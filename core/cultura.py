from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text

from config.horarios import ZONA_HORARIA
from core.base_datos import obtener_conexion


PROGRAMA_CONSTRUCTOR = "constructor"
VERSION_REGLAS = "v1"


def obtener_momento_actual():
    return datetime.now(
        ZoneInfo(ZONA_HORARIA)
    )


def inicializar_cultura():
    """
    El esquema se administra en PostgreSQL.
    """
    return


def alumno_acepto_reglas(alumno_id):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultado = sesion.execute(
            text(
                """
                SELECT 1
                FROM adhesiones_programa

                WHERE alumno_id = :alumno_id
                  AND programa = :programa
                  AND version = :version

                LIMIT 1
                """
            ),
            {
                "alumno_id": alumno_id,
                "programa": PROGRAMA_CONSTRUCTOR,
                "version": VERSION_REGLAS,
            },
        ).first()

    return resultado is not None


def aceptar_reglas(alumno_id):

    momento = obtener_momento_actual()

    conexion = obtener_conexion()

    with conexion.session as sesion:

        sesion.execute(
            text(
                """
                INSERT INTO adhesiones_programa (
                    alumno_id,
                    programa,
                    version,
                    fecha_aceptacion
                )
                VALUES (
                    :alumno_id,
                    :programa,
                    :version,
                    :fecha
                )

                ON CONFLICT (
                    alumno_id,
                    programa,
                    version
                )
                DO NOTHING
                """
            ),
            {
                "alumno_id": alumno_id,
                "programa": PROGRAMA_CONSTRUCTOR,
                "version": VERSION_REGLAS,
                "fecha": momento,
            },
        )

        sesion.commit()
