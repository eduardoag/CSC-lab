# ============================================================
# CSC LAB
# Gestión de sesiones académicas persistentes
# ============================================================

import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from config.horarios import ZONA_HORARIA


RUTA_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_DB = RUTA_PROYECTO / "data" / "csc_lab.db"

# Si entre dos interacciones pasan hasta 5 minutos,
# consideramos ese intervalo como trabajo continuo.
UMBRAL_ACTIVIDAD_SEGUNDOS = 300

# Una sesión sin actividad durante 15 minutos puede
# considerarse abandonada y cerrarse automáticamente.
EXPIRACION_SESION_MINUTOS = 15


def obtener_conexion():
    return sqlite3.connect(RUTA_DB)


def obtener_momento_actual():
    return datetime.now(ZoneInfo(ZONA_HORARIA))


def inicializar_base_datos():
    """
    Crea la tabla de sesiones y aplica pequeñas migraciones
    necesarias sin borrar el historial existente.
    """
    with obtener_conexion() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS sesiones (
                sesion_id TEXT PRIMARY KEY,
                alumno_id TEXT NOT NULL,
                curso TEXT NOT NULL,
                fecha TEXT NOT NULL,
                hora_inicio TEXT NOT NULL,
                ultima_actividad TEXT NOT NULL,
                hora_fin TEXT,
                segundos_activos INTEGER NOT NULL DEFAULT 0,
                estado TEXT NOT NULL DEFAULT 'ACTIVA',
                cierre_motivo TEXT
            )
            """
        )

        columnas = {
            fila[1]
            for fila in conexion.execute(
                "PRAGMA table_info(sesiones)"
            ).fetchall()
        }

        if "cierre_motivo" not in columnas:
            conexion.execute(
                "ALTER TABLE sesiones "
                "ADD COLUMN cierre_motivo TEXT"
            )

        conexion.commit()


def crear_sesion(alumno):
    momento = obtener_momento_actual()

    sesion_id = (
        f"{momento.strftime('%Y%m%d')}-"
        f"{alumno['alumno_id']}-"
        f"{uuid.uuid4().hex[:8]}"
    )

    with obtener_conexion() as conexion:
        conexion.execute(
            """
            INSERT INTO sesiones (
                sesion_id,
                alumno_id,
                curso,
                fecha,
                hora_inicio,
                ultima_actividad,
                segundos_activos,
                estado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sesion_id,
                alumno["alumno_id"],
                alumno["curso"],
                momento.date().isoformat(),
                momento.isoformat(),
                momento.isoformat(),
                0,
                "ACTIVA",
            ),
        )
        conexion.commit()

    return sesion_id


def obtener_sesion(sesion_id):
    with obtener_conexion() as conexion:
        conexion.row_factory = sqlite3.Row

        resultado = conexion.execute(
            """
            SELECT *
            FROM sesiones
            WHERE sesion_id = ?
            """,
            (sesion_id,),
        ).fetchone()

    if resultado is None:
        return None

    return dict(resultado)


def registrar_actividad(sesion_id):
    """
    Registra una nueva interacción.

    Si el intervalo desde la actividad anterior es <= 5 minutos,
    lo suma a segundos_activos. Si fue mayor, lo considera
    inactividad y no suma ese intervalo.
    """
    momento = obtener_momento_actual()

    with obtener_conexion() as conexion:
        conexion.row_factory = sqlite3.Row

        sesion = conexion.execute(
            """
            SELECT *
            FROM sesiones
            WHERE sesion_id = ?
              AND estado = 'ACTIVA'
            """,
            (sesion_id,),
        ).fetchone()

        if sesion is None:
            return False

        ultima = datetime.fromisoformat(
            sesion["ultima_actividad"]
        )

        diferencia = max(
            0,
            int((momento - ultima).total_seconds()),
        )

        segundos_a_sumar = 0

        if diferencia <= UMBRAL_ACTIVIDAD_SEGUNDOS:
            segundos_a_sumar = diferencia

        conexion.execute(
            """
            UPDATE sesiones
            SET ultima_actividad = ?,
                segundos_activos = segundos_activos + ?
            WHERE sesion_id = ?
              AND estado = 'ACTIVA'
            """,
            (
                momento.isoformat(),
                segundos_a_sumar,
                sesion_id,
            ),
        )

        conexion.commit()

    return True


def cerrar_sesion(sesion_id, motivo="CIERRE_ALUMNO"):
    """
    Cierra una sesión activa.

    motivo puede ser, por ejemplo:
    CIERRE_ALUMNO, FIN_HORARIO, CAMBIO_CURSO.
    """
    momento = obtener_momento_actual()

    with obtener_conexion() as conexion:
        conexion.execute(
            """
            UPDATE sesiones
            SET hora_fin = ?,
                ultima_actividad = ?,
                estado = 'CERRADA',
                cierre_motivo = ?
            WHERE sesion_id = ?
              AND estado = 'ACTIVA'
            """,
            (
                momento.isoformat(),
                momento.isoformat(),
                motivo,
                sesion_id,
            ),
        )
        conexion.commit()


def expirar_sesiones_abandonadas():
    """
    Cierra sesiones que quedaron ACTIVA por cierre del navegador,
    pérdida de conexión u otra interrupción.

    La hora_fin se fija en la última actividad conocida, no en
    el momento posterior en que detectamos la expiración.
    """
    momento = obtener_momento_actual()
    limite = momento - timedelta(
        minutes=EXPIRACION_SESION_MINUTOS
    )

    with obtener_conexion() as conexion:
        conexion.row_factory = sqlite3.Row

        sesiones = conexion.execute(
            """
            SELECT sesion_id, ultima_actividad
            FROM sesiones
            WHERE estado = 'ACTIVA'
            """
        ).fetchall()

        expiradas = 0

        for sesion in sesiones:
            ultima = datetime.fromisoformat(
                sesion["ultima_actividad"]
            )

            if ultima < limite:
                conexion.execute(
                    """
                    UPDATE sesiones
                    SET hora_fin = ultima_actividad,
                        estado = 'EXPIRADA',
                        cierre_motivo = 'INACTIVIDAD'
                    WHERE sesion_id = ?
                      AND estado = 'ACTIVA'
                    """,
                    (sesion["sesion_id"],),
                )
                expiradas += 1

        conexion.commit()

    return expiradas
