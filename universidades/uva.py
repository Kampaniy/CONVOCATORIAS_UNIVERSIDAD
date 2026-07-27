"""Scraper del tablón electrónico de anuncios "PDI" de la Universidad de
Valladolid (UVa).

Estructura verificada manualmente en julio de 2026 en:
https://portal.sede.uva.es/tablon/pdi/1/0/907

La página muestra una tabla HTML estándar (sin JavaScript) con tres
columnas: título del anuncio + enlace a la ficha, fecha de publicación,
y enlace(s) al PDF de detalle. La tabla se pagina (91 páginas en el
momento de la verificación); este scraper solo consulta la primera
página, que es donde aparecen siempre los anuncios más recientes, ya
que la tabla está ordenada por fecha de publicación descendente.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from universidades.base import Convocatoria, ScraperUniversidad
from utils.date_utils import parsear_fecha

logger = logging.getLogger("monitor_convocatorias")

_BASE_URL = "https://portal.sede.uva.es"


class ScraperUVa(ScraperUniversidad):
    id_universidad = "uva"
    nombre_universidad = "Universidad de Valladolid (UVa)"

    def obtener_convocatorias(self) -> List[Convocatoria]:
        html = self.descargar_html()
        soup = BeautifulSoup(html, "html.parser")

        tabla = soup.find("table")
        if tabla is None:
            logger.warning("[UVa] No se encontró ninguna tabla en la página del tablón.")
            return []

        convocatorias: List[Convocatoria] = []
        filas = tabla.find_all("tr")

        for fila in filas:
            celdas = fila.find_all("td")
            if len(celdas) < 2:
                # Es la fila de cabecera (th) o una fila sin datos: se ignora.
                continue

            celda_anuncio = celdas[0]
            enlace_tag = celda_anuncio.find("a")
            if enlace_tag is None:
                continue

            titulo = enlace_tag.get_text(strip=True)
            href = enlace_tag.get("href", "")
            enlace = urljoin(_BASE_URL, href) if href else self.url

            fecha_pub_texto = celdas[1].get_text(strip=True) if len(celdas) > 1 else None
            fecha_publicacion = parsear_fecha(fecha_pub_texto)

            if not titulo:
                continue

            convocatorias.append(
                Convocatoria(
                    universidad_id=self.id_universidad,
                    universidad_nombre=self.nombre_universidad,
                    titulo=titulo,
                    area=_extraer_area(titulo),
                    fecha_publicacion=fecha_publicacion,
                    # El tablón no publica una fecha límite de solicitud
                    # explícita en el listado; habría que abrir cada PDF
                    # individualmente para extraerla, lo que excede el
                    # alcance "sencillo" pedido. Se deja en None.
                    fecha_limite=None,
                    enlace=enlace,
                    cerrada=False,
                )
            )

        logger.info("[UVa] %d anuncios encontrados en la primera página del tablón.", len(convocatorias))
        return convocatorias


def _extraer_area(titulo: str) -> Optional[str]:
    """Intenta extraer el área de conocimiento a partir del texto del
    título del anuncio, cuando sigue el patrón "..., Área <nombre>."
    típico de los anuncios de la UVa. Si no se encuentra el patrón,
    devuelve None (el filtrado por palabras clave seguirá funcionando
    igualmente sobre el título completo).
    """
    coincidencia = re.search(r"[ÁA]rea\s*[:\-]?\s*([^.,]+)", titulo, flags=re.IGNORECASE)
    if coincidencia:
        return coincidencia.group(1).strip()
    return None
