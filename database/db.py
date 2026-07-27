"""Persistencia mínima en SQLite para no notificar dos veces la misma
convocatoria.

Solo se guarda un identificador único por convocatoria (hash del enlace
o del título+universidad) y la fecha en que se detectó. No se almacena
ninguna información adicional, tal y como se pidió.
"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator


class BaseDatos:
    """Envoltorio muy simple sobre SQLite para registrar convocatorias ya
    notificadas y comprobar duplicados."""

    def __init__(self, ruta_bd: str) -> None:
        self.ruta_bd = ruta_bd
        Path(ruta_bd).parent.mkdir(parents=True, exist_ok=True)
        self._inicializar_esquema()

    @staticmethod
    def generar_id(universidad_id: str, enlace: str, titulo: str) -> str:
        """Genera un identificador estable y único para una convocatoria.

        Se basa en el enlace (más fiable) combinado con el id de la
        universidad; si el enlace estuviera vacío, se usa el título como
        respaldo para evitar colisiones accidentales.
        """
        base = f"{universidad_id}|{enlace or titulo}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @contextmanager
    def _conexion(self) -> Iterator[sqlite3.Connection]:
        conexion = sqlite3.connect(self.ruta_bd)
        try:
            yield conexion
            conexion.commit()
        finally:
            conexion.close()

    def _inicializar_esquema(self) -> None:
        with self._conexion() as conexion:
            conexion.execute(
                """
                CREATE TABLE IF NOT EXISTS convocatorias_notificadas (
                    id TEXT PRIMARY KEY,
                    universidad_id TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    fecha_deteccion TEXT NOT NULL
                )
                """
            )

    def ya_notificada(self, convocatoria_id: str) -> bool:
        """Comprueba si una convocatoria ya fue notificada anteriormente."""
        with self._conexion() as conexion:
            cursor = conexion.execute(
                "SELECT 1 FROM convocatorias_notificadas WHERE id = ? LIMIT 1",
                (convocatoria_id,),
            )
            return cursor.fetchone() is not None

    def marcar_notificada(self, convocatoria_id: str, universidad_id: str, titulo: str) -> None:
        """Registra una convocatoria como ya notificada."""
        with self._conexion() as conexion:
            conexion.execute(
                """
                INSERT OR IGNORE INTO convocatorias_notificadas
                    (id, universidad_id, titulo, fecha_deteccion)
                VALUES (?, ?, ?, ?)
                """,
                (convocatoria_id, universidad_id, titulo, datetime.utcnow().isoformat()),
            )
