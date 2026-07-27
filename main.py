#!/usr/bin/env python3
"""Sistema de monitorización de convocatorias de plazas universitarias.

Flujo general (ver README.md para más detalle):
  1. Carga la configuración (config/config.yaml) y las palabras clave
     (config/keywords.yaml).
  2. Para cada universidad activa, descarga y parsea sus convocatorias
     mediante el scraper correspondiente en universidades/.
  3. Filtra las convocatorias cuyo título o área contengan alguna
     palabra clave.
  4. Descarta las que ya están cerradas (fecha límite pasada) o que ya
     se notificaron anteriormente (registradas en SQLite).
  5. Envía un correo electrónico por cada convocatoria nueva y la
     marca como notificada.

Si una universidad falla (error de red, cambio de estructura HTML,
etc.), se registra el error y se continúa con el resto: un fallo
puntual nunca debe detener la ejecución completa.
"""

from __future__ import annotations

import argparse
import importlib
import logging
import os
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Permite ejecutar "python main.py" desde cualquier directorio.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from database.db import BaseDatos  # noqa: E402
from universidades.base import Convocatoria, ScraperUniversidad  # noqa: E402
from utils.date_utils import convocatoria_cerrada, dias_restantes  # noqa: E402
from utils.email_sender import (  # noqa: E402
    CredencialesSMTP,
    ErrorEnvioCorreo,
    construir_cuerpo_html,
    enviar_correo,
)
from utils.logger import configurar_logger  # noqa: E402

RUTA_BASE = Path(__file__).resolve().parent


def cargar_yaml(ruta: Path) -> Dict[str, Any]:
    with open(ruta, "r", encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


def normalizar_texto(texto: Optional[str]) -> str:
    """Pasa a minúsculas y elimina acentos, para comparar sin distinguir
    mayúsculas/minúsculas ni tildes."""
    if not texto:
        return ""
    texto_sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return texto_sin_acentos.lower()


def coincide_con_palabras_clave(convocatoria: Convocatoria, palabras_clave: List[str]) -> bool:
    texto_completo = normalizar_texto(convocatoria.titulo) + " " + normalizar_texto(convocatoria.area)
    return any(normalizar_texto(palabra) in texto_completo for palabra in palabras_clave)


def instanciar_scraper(config_universidad: Dict[str, Any], comportamiento: Dict[str, Any]) -> ScraperUniversidad:
    """Importa dinámicamente el módulo/clase indicados en config.yaml y
    devuelve una instancia lista para usar."""
    modulo = importlib.import_module(f"universidades.{config_universidad['modulo']}")
    clase = getattr(modulo, config_universidad["clase"])
    return clase(
        url=config_universidad["url"],
        timeout=comportamiento["timeout_segundos"],
        user_agent=comportamiento["user_agent"],
    )


def obtener_convocatorias_con_reintentos(
    scraper: ScraperUniversidad,
    reintentos: int,
    espera_segundos: float,
    logger: logging.Logger,
) -> List[Convocatoria]:
    ultimo_error: Optional[Exception] = None
    for intento in range(1, reintentos + 1):
        try:
            return scraper.obtener_convocatorias()
        except Exception as error:  # noqa: BLE001 - un fallo aquí nunca debe tumbar el sistema
            ultimo_error = error
            logger.warning(
                "[%s] Intento %d/%d fallido: %s",
                scraper.id_universidad,
                intento,
                reintentos,
                error,
            )
            if intento < reintentos:
                time.sleep(espera_segundos)

    logger.error("[%s] No se pudo obtener información tras %d intentos: %s", scraper.id_universidad, reintentos, ultimo_error)
    return []


def obtener_credenciales_smtp(config: Dict[str, Any]) -> CredencialesSMTP:
    """Lee las credenciales SMTP desde variables de entorno (secretos de
    GitHub Actions). Lanza un error claro si falta alguna."""
    variables_requeridas = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_DESTINO"]
    faltantes = [variable for variable in variables_requeridas if not os.environ.get(variable)]
    if faltantes:
        raise RuntimeError(
            "Faltan variables de entorno necesarias para el envío de correo: "
            + ", ".join(faltantes)
            + ". Configúralas como 'secrets' en GitHub Actions (ver README.md)."
        )

    return CredencialesSMTP(
        host=os.environ["SMTP_HOST"],
        puerto=int(os.environ["SMTP_PORT"]),
        usuario=os.environ["SMTP_USER"],
        contrasena=os.environ["SMTP_PASSWORD"],
        destino=os.environ["EMAIL_DESTINO"],
        usar_tls=config["correo"].get("usar_tls", True),
    )


def procesar_universidad(
    config_universidad: Dict[str, Any],
    comportamiento: Dict[str, Any],
    palabras_clave: List[str],
    base_datos: BaseDatos,
    credenciales_smtp: Optional[CredencialesSMTP],
    asunto_correo: str,
    logger: logging.Logger,
    modo_prueba: bool,
) -> Dict[str, int]:
    """Procesa una única universidad de principio a fin y devuelve un
    resumen de estadísticas para el log."""
    resumen = {"encontradas": 0, "nuevas": 0, "errores": 0}
    universidad_id = config_universidad["id"]

    try:
        scraper = instanciar_scraper(config_universidad, comportamiento)
    except Exception as error:  # noqa: BLE001
        logger.error("[%s] Error instanciando el scraper: %s", universidad_id, error)
        resumen["errores"] += 1
        return resumen

    convocatorias = obtener_convocatorias_con_reintentos(
        scraper,
        reintentos=comportamiento["reintentos_por_universidad"],
        espera_segundos=comportamiento["espera_entre_reintentos_segundos"],
        logger=logger,
    )
    resumen["encontradas"] = len(convocatorias)

    for convocatoria in convocatorias:
        try:
            if not coincide_con_palabras_clave(convocatoria, palabras_clave):
                continue

            if convocatoria.cerrada or convocatoria_cerrada(convocatoria.fecha_limite):
                logger.debug(
                    "[%s] Convocatoria descartada por estar cerrada: %s",
                    universidad_id,
                    convocatoria.titulo,
                )
                continue

            convocatoria_id = BaseDatos.generar_id(
                universidad_id, convocatoria.enlace, convocatoria.titulo
            )
            if base_datos.ya_notificada(convocatoria_id):
                continue

            resumen["nuevas"] += 1
            logger.info("[%s] Nueva convocatoria detectada: %s", universidad_id, convocatoria.titulo)

            if modo_prueba:
                logger.info("[%s] MODO PRUEBA: no se envía correo ni se marca como notificada.", universidad_id)
                continue

            cuerpo_html = construir_cuerpo_html(
                universidad=convocatoria.universidad_nombre,
                titulo=convocatoria.titulo,
                area=convocatoria.area,
                fecha_publicacion=(
                    convocatoria.fecha_publicacion.strftime("%d/%m/%Y")
                    if convocatoria.fecha_publicacion
                    else None
                ),
                fecha_limite=(
                    convocatoria.fecha_limite.strftime("%d/%m/%Y") if convocatoria.fecha_limite else None
                ),
                dias_restantes=dias_restantes(convocatoria.fecha_limite),
                enlace=convocatoria.enlace,
            )

            assert credenciales_smtp is not None  # ya se validó antes de llamar a esta función
            enviar_correo(credenciales_smtp, asunto_correo, cuerpo_html)
            base_datos.marcar_notificada(convocatoria_id, universidad_id, convocatoria.titulo)

        except ErrorEnvioCorreo as error:
            logger.error("[%s] Error enviando correo: %s", universidad_id, error)
            resumen["errores"] += 1
        except Exception as error:  # noqa: BLE001 - una convocatoria problemática no debe tumbar el resto
            logger.error("[%s] Error procesando una convocatoria: %s", universidad_id, error)
            resumen["errores"] += 1

    return resumen


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor de convocatorias de plazas universitarias")
    parser.add_argument(
        "--solo",
        help="Ejecuta el sistema solo para el id de una universidad concreta (ej: --solo uva)",
        default=None,
    )
    parser.add_argument(
        "--prueba",
        action="store_true",
        help="Ejecuta el scraping y el filtrado pero NO envía correos ni marca nada como notificado.",
    )
    args = parser.parse_args()

    config = cargar_yaml(RUTA_BASE / "config" / "config.yaml")
    keywords_config = cargar_yaml(RUTA_BASE / config["rutas"]["palabras_clave"])
    palabras_clave = keywords_config["palabras_clave"]

    logger = configurar_logger(str(RUTA_BASE / config["rutas"]["log"]))
    logger.info("=== Inicio de ejecución del monitor de convocatorias ===")

    base_datos = BaseDatos(str(RUTA_BASE / config["rutas"]["base_datos"]))

    credenciales_smtp: Optional[CredencialesSMTP] = None
    if not args.prueba:
        try:
            credenciales_smtp = obtener_credenciales_smtp(config)
        except RuntimeError as error:
            logger.error(str(error))
            return 1

    universidades = config["universidades"]
    if args.solo:
        universidades = [u for u in universidades if u["id"] == args.solo]
        if not universidades:
            logger.error("No existe ninguna universidad con id '%s' en config.yaml", args.solo)
            return 1

    resumen_total = {"encontradas": 0, "nuevas": 0, "errores": 0}

    for config_universidad in universidades:
        if not config_universidad.get("activa", True):
            logger.info("[%s] Universidad desactivada en config.yaml, se omite.", config_universidad["id"])
            continue

        logger.info("--- Procesando %s ---", config_universidad["nombre"])
        resumen = procesar_universidad(
            config_universidad=config_universidad,
            comportamiento=config["comportamiento"],
            palabras_clave=palabras_clave,
            base_datos=base_datos,
            credenciales_smtp=credenciales_smtp,
            asunto_correo=config["correo"]["asunto"],
            logger=logger,
            modo_prueba=args.prueba,
        )
        logger.info(
            "[%s] Resumen: %d encontradas, %d nuevas, %d errores.",
            config_universidad["id"],
            resumen["encontradas"],
            resumen["nuevas"],
            resumen["errores"],
        )
        for clave in resumen_total:
            resumen_total[clave] += resumen[clave]

        scraper_pausa = config["comportamiento"]["espera_entre_universidades_segundos"]
        time.sleep(scraper_pausa)

    logger.info(
        "=== Fin de la ejecución. Total: %d encontradas, %d nuevas, %d errores. ===",
        resumen_total["encontradas"],
        resumen_total["nuevas"],
        resumen_total["errores"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
