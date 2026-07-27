"""Utilidades para parsear fechas en formato español y calcular plazos."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

# Formatos de fecha habituales en los tablones universitarios españoles.
_FORMATOS_FECHA = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d de %B de %Y",  # ej: "27 de julio de 2026" (requiere meses en español, ver abajo)
)

_MESES_ES = {
    "enero": "January",
    "febrero": "February",
    "marzo": "March",
    "abril": "April",
    "mayo": "May",
    "junio": "June",
    "julio": "July",
    "agosto": "August",
    "septiembre": "September",
    "setiembre": "September",
    "octubre": "October",
    "noviembre": "November",
    "diciembre": "December",
}


def _traducir_mes_es_a_en(texto: str) -> str:
    """Traduce el nombre de un mes en español a su equivalente en inglés.

    Esto permite reutilizar el parseo estándar de datetime.strptime con
    el especificador %B (nombre completo del mes) sin depender del
    locale del sistema operativo, que no es fiable en GitHub Actions.
    """
    texto_lower = texto.lower()
    for mes_es, mes_en in _MESES_ES.items():
        if mes_es in texto_lower:
            texto_lower = texto_lower.replace(mes_es, mes_en)
    return texto_lower


def parsear_fecha(texto: Optional[str]) -> Optional[date]:
    """Intenta convertir un texto de fecha en un objeto `date`.

    Soporta los formatos dd/mm/aaaa, dd-mm-aaaa, dd.mm.aaaa y
    "dd de <mes> de aaaa". Si no puede parsear el texto, devuelve None
    en lugar de lanzar una excepción, para no interrumpir el scraping.

    Args:
        texto: Cadena de texto que representa una fecha, o None.

    Returns:
        Objeto `date` si el parseo tuvo éxito, o None en caso contrario.
    """
    if not texto:
        return None

    texto = texto.strip()
    if not texto:
        return None

    # Normaliza espacios múltiples.
    texto = re.sub(r"\s+", " ", texto)

    for formato in _FORMATOS_FECHA:
        candidato = texto
        if "%B" in formato:
            candidato = _traducir_mes_es_a_en(texto)
        try:
            return datetime.strptime(candidato, formato).date()
        except ValueError:
            continue

    return None


def dias_restantes(fecha_limite: Optional[date], hoy: Optional[date] = None) -> Optional[int]:
    """Calcula los días naturales restantes hasta una fecha límite.

    Args:
        fecha_limite: Fecha límite de la convocatoria, o None si se desconoce.
        hoy: Fecha de referencia (por defecto, la fecha actual). Se permite
            inyectarla para facilitar las pruebas unitarias.

    Returns:
        Número de días restantes (puede ser negativo si ya venció), o None
        si no se pudo determinar la fecha límite.
    """
    if fecha_limite is None:
        return None
    if hoy is None:
        hoy = date.today()
    return (fecha_limite - hoy).days


def convocatoria_cerrada(fecha_limite: Optional[date], hoy: Optional[date] = None) -> bool:
    """Indica si una convocatoria debe considerarse cerrada.

    Una convocatoria sin fecha límite conocida NUNCA se considera cerrada
    automáticamente (no hay datos suficientes para descartarla); es
    responsabilidad del scraper de cada universidad marcarla como cerrada
    si detecta explícitamente esa palabra en la página de origen.

    Args:
        fecha_limite: Fecha límite de solicitud, si se conoce.
        hoy: Fecha de referencia (por defecto, hoy).

    Returns:
        True si la fecha límite ya pasó, False en caso contrario.
    """
    restantes = dias_restantes(fecha_limite, hoy)
    if restantes is None:
        return False
    return restantes < 0
