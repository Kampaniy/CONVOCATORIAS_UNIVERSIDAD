"""Clase base común para todos los scrapers de universidades.

Cada universidad se implementa en su propio archivo dentro de este
paquete, heredando de `ScraperUniversidad` e implementando el método
`obtener_convocatorias`. Así se puede añadir o quitar una universidad
sin tocar el resto del sistema.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import requests

logger = logging.getLogger("monitor_convocatorias")


@dataclass
class Convocatoria:
    """Representa una única convocatoria detectada en la web de origen."""

    universidad_id: str
    universidad_nombre: str
    titulo: str
    area: Optional[str]
    fecha_publicacion: Optional[date]
    fecha_limite: Optional[date]
    enlace: str
    cerrada: bool = False


class ScraperUniversidad(ABC):
    """Interfaz común que debe implementar cada scraper de universidad."""

    #: Identificador corto de la universidad (debe coincidir con config.yaml)
    id_universidad: str = "base"
    #: Nombre legible de la universidad
    nombre_universidad: str = "Universidad"

    def __init__(self, url: str, timeout: int, user_agent: str) -> None:
        self.url = url
        self.timeout = timeout
        self.headers = {"User-Agent": user_agent}

    def descargar_html(self, url: Optional[str] = None) -> str:
        """Descarga el HTML de la URL configurada (o de la indicada).

        Lanza `requests.RequestException` si la petición falla; la
        gestión de reintentos y errores se hace en el nivel superior
        (main.py), tal y como se pidió en los requisitos ("si una
        universidad falla, registrar el error y continuar con el resto").
        """
        respuesta = requests.get(url or self.url, headers=self.headers, timeout=self.timeout)
        respuesta.raise_for_status()
        respuesta.encoding = respuesta.apparent_encoding or respuesta.encoding
        return respuesta.text

    @abstractmethod
    def obtener_convocatorias(self) -> List[Convocatoria]:
        """Descarga y parsea la página de la universidad.

        Returns:
            Lista de objetos `Convocatoria` encontrados en la página.
            Debe devolver una lista vacía (no None) si no hay resultados.
        """
        raise NotImplementedError

    def pausa_cortesia(self, segundos: float) -> None:
        """Pequeña pausa entre peticiones para no saturar el servidor."""
        if segundos > 0:
            time.sleep(segundos)
