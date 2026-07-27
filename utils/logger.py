"""Configuración de logging para el sistema de monitorización.

Escribe simultáneamente en consola (stdout, visible en los logs de
GitHub Actions) y en un archivo de log local sencillo.
"""

from __future__ import annotations

import logging
from pathlib import Path


def configurar_logger(ruta_log: str, nivel: int = logging.INFO) -> logging.Logger:
    """Configura y devuelve el logger raíz de la aplicación.

    Args:
        ruta_log: Ruta del archivo donde se escribirá el log.
        nivel: Nivel mínimo de logging (por defecto INFO).

    Returns:
        Logger ya configurado, listo para usar en el resto del programa.
    """
    Path(ruta_log).parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("monitor_convocatorias")
    logger.setLevel(nivel)

    # Evita añadir handlers duplicados si la función se llama más de una vez.
    if logger.handlers:
        return logger

    formato = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler_archivo = logging.FileHandler(ruta_log, encoding="utf-8")
    handler_archivo.setFormatter(formato)
    logger.addHandler(handler_archivo)

    handler_consola = logging.StreamHandler()
    handler_consola.setFormatter(formato)
    logger.addHandler(handler_consola)

    return logger
