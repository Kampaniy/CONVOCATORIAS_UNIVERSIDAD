"""Scraper de la página "Concursos a plazas de PDI" de la UNED.

NOTA IMPORTANTE SOBRE VERIFICACIÓN:
La estructura general de esta página (encabezados <h2> del tipo
"Convocatoria N/AAAA. Profesorado contratado (...)" seguidos de una
lista de enlaces, y un párrafo con el texto "Plazo de presentación de
solicitudes: desde ... al ...") se comprobó en julio de 2026 a partir
del contenido renderizado de la página. No se inspeccionó el HTML en
bruto (etiquetas y clases CSS exactas), por lo que, si tras la primera
ejecución real el sistema no detecta convocatorias, es muy probable que
haya que ajustar los selectores de este archivo. Ejecuta
`python main.py --solo uned --debug` (ver README) para inspeccionar el
HTML descargado y adaptar el scraper si es necesario.
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

_BASE_URL = "https://www.uned.es"
_PATRON_TITULO_CONVOCATORIA = re.compile(r"Convocatoria\s+\d+", re.IGNORECASE)
_PATRON_PLAZO = re.compile(
    r"Plazo de presentaci[oó]n de solicitudes[:]?\s*desde.*?al\s+(.+?)(?:,\s*inclusive)?\.",
    re.IGNORECASE,
)


class ScraperUNED(ScraperUniversidad):
    id_universidad = "uned"
    nombre_universidad = "UNED"

    def obtener_convocatorias(self) -> List[Convocatoria]:
        html = self.descargar_html()
        soup = BeautifulSoup(html, "html.parser")

        encabezados = [
            h for h in soup.find_all(["h2", "h3"]) if _PATRON_TITULO_CONVOCATORIA.search(h.get_text())
        ]

        convocatorias: List[Convocatoria] = []
        for encabezado in encabezados:
            titulo = encabezado.get_text(strip=True)
            bloque_html = _texto_hasta_siguiente_encabezado(encabezado)
            enlace, fecha_publicacion = _primer_enlace_y_fecha(encabezado)
            fecha_limite = _extraer_fecha_limite(bloque_html)

            convocatorias.append(
                Convocatoria(
                    universidad_id=self.id_universidad,
                    universidad_nombre=self.nombre_universidad,
                    titulo=titulo,
                    area=None,
                    fecha_publicacion=fecha_publicacion,
                    fecha_limite=fecha_limite,
                    enlace=enlace or self.url,
                    cerrada=False,
                )
            )

        logger.info("[UNED] %d convocatorias encontradas.", len(convocatorias))
        return convocatorias


def _texto_hasta_siguiente_encabezado(encabezado) -> str:
    """Concatena el texto de los elementos hermanos siguientes hasta el
    próximo encabezado h2/h3, para poder buscar en él el plazo de
    solicitud sin invadir el bloque de la siguiente convocatoria."""
    trozos = []
    for hermano in encabezado.find_next_siblings():
        if hermano.name in ("h2", "h3"):
            break
        trozos.append(hermano.get_text(" ", strip=True))
    return " ".join(trozos)


def _primer_enlace_y_fecha(encabezado):
    """Busca el primer enlace <a> tras el encabezado (normalmente el PDF
    de la convocatoria oficial) y, si su texto empieza por una fecha
    dd/mm/aaaa, la extrae como fecha de publicación."""
    siguiente = encabezado.find_next("a")
    if siguiente is None:
        return None, None

    href = siguiente.get("href", "")
    enlace = urljoin(_BASE_URL, href) if href else None

    texto = siguiente.get_text(strip=True)
    coincidencia = re.match(r"(\d{2}/\d{2}/\d{4})", texto)
    fecha_publicacion = parsear_fecha(coincidencia.group(1)) if coincidencia else None

    return enlace, fecha_publicacion


def _extraer_fecha_limite(bloque_texto: str) -> Optional[str]:
    coincidencia = _PATRON_PLAZO.search(bloque_texto)
    if not coincidencia:
        return None
    return parsear_fecha(coincidencia.group(1).strip())
