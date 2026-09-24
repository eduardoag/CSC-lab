# ============================================================
# CSC LAB
# Cultura del programa
# ============================================================

import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config.horarios import ZONA_HORARIA


RUTA_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_DB = RUTA_PROYECTO / "data" / "csc_lab.db"

PROGRAMA_CONSTRUCTOR = "constructor"
VERSION_REGLAS = "v1"


def obtener_conexion():
    return sqlite3.connect(RUTA_DB)


def obtener_momento_actual():
    return datetime.now(
        ZoneInfo(ZONA_HORARIA)
    )


def inicializar_cultura():
    """
    Crea las tablas relacionadas con la cultura
    del programa si todavía no existen.
    """

    with obtener_conexion() as conexion:

        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS adhesiones_programa (
                alumno_id TEXT NOT NULL,
                programa TEXT NOT NULL,
                version TEXT NOT NULL,
                fecha_aceptacion TEXT NOT NULL,

                PRIMARY KEY (
                    alumno_id,
                    programa,
                    version
                )
            )
            """
        )

        conexion.commit()


def alumno_acepto_reglas(alumno_id):
    """
    Devuelve True si el alumno ya aceptó
    la versión vigente de las reglas.
    """

    with obtener_conexion() as conexion:

        resultado = conexion.execute(
            """
            SELECT 1
            FROM adhesiones_programa
            WHERE alumno_id = ?
              AND programa = ?
              AND version = ?
            """,
            (
                alumno_id,
                PROGRAMA_CONSTRUCTOR,
                VERSION_REGLAS,
            ),
        ).fetchone()

    return resultado is not None


def aceptar_reglas(alumno_id):
    """
    Registra la aceptación de las reglas
    del Constructor para la versión vigente.
    """

    momento = obtener_momento_actual()

    with obtener_conexion() as conexion:

        conexion.execute(
            """
            INSERT OR IGNORE INTO adhesiones_programa (
                alumno_id,
                programa,
                version,
                fecha_aceptacion
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                alumno_id,
                PROGRAMA_CONSTRUCTOR,
                VERSION_REGLAS,
                momento.isoformat(),
            ),
        )

        conexion.commit()
