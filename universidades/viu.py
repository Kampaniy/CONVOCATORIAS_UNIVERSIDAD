"""Scraper de la VIU (Universidad Internacional de Valencia).

Hereda del scraper genérico heurístico (ver `generico.py` para el aviso
importante sobre las limitaciones frente a páginas con carga por
JavaScript). Ajusta `obtener_convocatorias` aquí si esta universidad en
concreto necesita una lógica distinta a la genérica.
"""

from __future__ import annotations

from universidades.generico import ScraperGenerico


class ScraperVIU(ScraperGenerico):
    id_universidad = "viu"
    nombre_universidad = "Universidad Internacional de Valencia (VIU)"
