"""Scraper genérico y heurístico, pensado como PUNTO DE PARTIDA para las
universidades privadas online (UNIR, UOC, Universidad Isabel I, VIU).

⚠️ AVISO IMPORTANTE DE FIABILIDAD (léase antes de confiar en este scraper)
---------------------------------------------------------------------------
A diferencia de los scrapers de UVa y UNED (cuya estructura HTML se
verificó directamente sobre la página real), las páginas de "trabaja con
nosotros" / "empleo" de las universidades privadas online:

  1. Cambian de estructura con frecuencia y no siguen un patrón único.
  2. Muchas están construidas con paneles de ofertas dinámicos (React,
     Vue, portales de terceros tipo Personio, Workday, Factorial,
     Softgarden...) que cargan las vacantes mediante JavaScript DESPUÉS
     de la carga inicial de la página. La librería `requests` utilizada
     aquí (deliberadamente, para mantener el sistema simple y sin
     dependencias pesadas como Selenium/Playwright) NO ejecuta
     JavaScript, por lo que en esos casos este scraper devolverá una
     lista vacía aunque existan vacantes publicadas.

Este archivo implementa una estrategia razonable (buscar enlaces cuyo
texto contenga términos relacionados con plazas docentes) que funcionará
si la página es HTML estático, pero se recomienda ENCARECIDAMENTE
verificar manualmente, tras la primera ejecución en GitHub Actions, si
cada universidad online está devolviendo resultados. Si una universidad
concreta usa un portal de ofertas dinámico, la solución robusta pasa por
localizar el endpoint JSON que ese portal consulta internamente (visible
en la pestaña "Red/Network" del navegador) y adaptar el scraper
correspondiente para leer ese JSON directamente con `requests`, lo cual
sigue sin requerir un navegador completo.
"""

from __future__ import annotations

import logging
import re
from typing import List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from universidades.base import Convocatoria, ScraperUniversidad

logger = logging.getLogger("monitor_convocatorias")

# Términos que sugieren que un enlace corresponde a una vacante docente
# (y no a un enlace de menú, redes sociales, legal, etc.).
_TERMINOS_RELEVANTES = (
    "profesor",
    "docente",
    "pdi",
    "plaza",
    "vacante",
    "oferta",
    "convocatoria",
    "empleo",
)


class ScraperGenerico(ScraperUniversidad):
    """Scraper heurístico reutilizable por varias universidades online.

    Cada subclase solo necesita definir `id_universidad` y
    `nombre_universidad`; si en el futuro una universidad concreta
    necesita una lógica distinta, basta con sobrescribir
    `obtener_convocatorias` en su propio archivo sin afectar a las demás.
    """

    def obtener_convocatorias(self) -> List[Convocatoria]:
        html = self.descargar_html()
        soup = BeautifulSoup(html, "html.parser")

        dominio = urlparse(self.url).scheme + "://" + urlparse(self.url).netloc
        convocatorias: List[Convocatoria] = []
        vistos = set()

        for enlace_tag in soup.find_all("a", href=True):
            texto = enlace_tag.get_text(" ", strip=True)
            if not texto or len(texto) < 8:
                continue

            texto_normalizado = _sin_acentos(texto.lower())
            if not any(termino in texto_normalizado for termino in _TERMINOS_RELEVANTES):
                continue

            href = enlace_tag["href"]
            enlace_absoluto = urljoin(dominio, href)

            if enlace_absoluto in vistos:
                continue
            vistos.add(enlace_absoluto)

            convocatorias.append(
                Convocatoria(
                    universidad_id=self.id_universidad,
                    universidad_nombre=self.nombre_universidad,
                    titulo=texto,
                    area=None,
                    fecha_publicacion=None,
                    fecha_limite=None,
                    enlace=enlace_absoluto,
                    cerrada=False,
                )
            )

        logger.info(
            "[%s] %d posibles vacantes encontradas (scraper genérico heurístico).",
            self.id_universidad,
            len(convocatorias),
        )
        return convocatorias


def _sin_acentos(texto: str) -> str:
    """Sustituye vocales acentuadas para que la búsqueda de términos no
    dependa de que el texto use o no tildes."""
    tabla = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")
    return texto.translate(tabla)
