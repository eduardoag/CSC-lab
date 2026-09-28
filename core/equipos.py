# ============================================================
# CSC LAB
# Gestión de equipos
# ============================================================

import sqlite3
from pathlib import Path


RUTA_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_DB = RUTA_PROYECTO / "data" / "csc_lab.db"


def obtener_conexion():
    return sqlite3.connect(RUTA_DB)


def inicializar_equipos():
    """
    Crea las tablas necesarias para gestionar
    equipos y membresías.
    """

    with obtener_conexion() as conexion:

        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS equipos (
                equipo_id TEXT PRIMARY KEY,
                curso TEXT NOT NULL,
                numero_equipo INTEGER NOT NULL,
                nombre_equipo TEXT NOT NULL,
                nombre_empresa TEXT,
                activo INTEGER NOT NULL DEFAULT 1,

                UNIQUE (curso, numero_equipo)
            )
            """
        )

        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS miembros_equipo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipo_id TEXT NOT NULL,
                alumno_id TEXT NOT NULL,
                fecha_desde TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                fecha_hasta TEXT,
                activo INTEGER NOT NULL DEFAULT 1,

                FOREIGN KEY (equipo_id)
                    REFERENCES equipos(equipo_id)
            )
            """
        )

        conexion.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_alumno_equipo_activo
            ON miembros_equipo(alumno_id)
            WHERE activo = 1
            """
        )

        conexion.commit()


def obtener_equipo_alumno(alumno_id):
    """
    Obtiene el equipo activo al que pertenece
    actualmente un alumno.
    """

    with obtener_conexion() as conexion:

        conexion.row_factory = sqlite3.Row

        resultado = conexion.execute(
            """
            SELECT
                e.equipo_id,
                e.curso,
                e.numero_equipo,
                e.nombre_equipo,
                e.nombre_empresa
            FROM miembros_equipo AS m
            JOIN equipos AS e
                ON e.equipo_id = m.equipo_id
            WHERE m.alumno_id = ?
              AND m.activo = 1
              AND e.activo = 1
            LIMIT 1
            """,
            (alumno_id,),
        ).fetchone()

    if resultado is None:
        return None

    return dict(resultado)


def obtener_integrantes_equipo(equipo_id):
    """
    Devuelve los alumno_id de todos los integrantes
    activos de un equipo.
    """

    with obtener_conexion() as conexion:

        conexion.row_factory = sqlite3.Row

        resultados = conexion.execute(
            """
            SELECT alumno_id
            FROM miembros_equipo
            WHERE equipo_id = ?
              AND activo = 1
            ORDER BY alumno_id
            """,
            (equipo_id,),
        ).fetchall()

    return [
        fila["alumno_id"]
        for fila in resultados
    ]
