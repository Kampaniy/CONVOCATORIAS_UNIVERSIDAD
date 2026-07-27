"""Scraper de UNIR (Universidad Internacional de La Rioja).

Hereda del scraper genérico heurístico (ver `generico.py` para el aviso
importante sobre las limitaciones frente a páginas con carga por
JavaScript). Ajusta `obtener_convocatorias` aquí si esta universidad en
concreto necesita una lógica distinta a la genérica.
"""

from __future__ import annotations

from universidades.generico import ScraperGenerico


class ScraperUNIR(ScraperGenerico):
    id_universidad = "unir"
    nombre_universidad = "UNIR"
