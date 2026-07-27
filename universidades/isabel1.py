"""Scraper de la Universidad Isabel I.

Hereda del scraper genérico heurístico (ver `generico.py` para el aviso
importante sobre las limitaciones frente a páginas con carga por
JavaScript). Ajusta `obtener_convocatorias` aquí si esta universidad en
concreto necesita una lógica distinta a la genérica.
"""

from __future__ import annotations

from universidades.generico import ScraperGenerico


class ScraperIsabel1(ScraperGenerico):
    id_universidad = "isabel1"
    nombre_universidad = "Universidad Isabel I"
