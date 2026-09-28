import uuid

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from config.horarios import ZONA_HORARIA
from core.base_datos import obtener_conexion


UMBRAL_ACTIVIDAD_SEGUNDOS = 300
EXPIRACION_SESION_MINUTOS = 15


def obtener_momento_actual():
    return datetime.now(
        ZoneInfo(ZONA_HORARIA)
    )


def inicializar_base_datos():
    """
    PostgreSQL ya posee el esquema.
    """
    return


def crear_sesion(alumno):

    momento = obtener_momento_actual()

    sesion_id = (
        f"{momento.strftime('%Y%m%d')}-"
        f"{alumno['alumno_id']}-"
        f"{uuid.uuid4().hex[:8]}"
    )

    conexion = obtener_conexion()

    with conexion.session as sesion:

        sesion.execute(
            text(
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
                VALUES (
                    :sesion_id,
                    :alumno_id,
                    :curso,
                    :fecha,
                    :hora_inicio,
                    :ultima_actividad,
                    0,
                    'ACTIVA'
                )
                """
            ),
            {
                "sesion_id": sesion_id,
                "alumno_id": alumno["alumno_id"],
                "curso": alumno["curso"],
                "fecha": momento.date(),
                "hora_inicio": momento,
                "ultima_actividad": momento,
            },
        )

        sesion.commit()

    return sesion_id


def obtener_sesion(sesion_id):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultado = sesion.execute(
            text(
                """
                SELECT *
                FROM sesiones
                WHERE sesion_id = :sesion_id
                """
            ),
            {
                "sesion_id": sesion_id,
            },
        ).mappings().first()

    if resultado is None:
        return None

    return dict(resultado)


def registrar_actividad(sesion_id):

    momento = obtener_momento_actual()

    conexion = obtener_conexion()

    with conexion.session as sesion:

        registro = sesion.execute(
            text(
                """
                SELECT *
                FROM sesiones
                WHERE sesion_id = :sesion_id
                  AND estado = 'ACTIVA'
                """
            ),
            {
                "sesion_id": sesion_id,
            },
        ).mappings().first()

        if registro is None:
            return False

        ultima = registro["ultima_actividad"]

        diferencia = max(
            0,
            int(
                (
                    momento - ultima
                ).total_seconds()
            ),
        )

        segundos_a_sumar = (
            diferencia
            if diferencia <= UMBRAL_ACTIVIDAD_SEGUNDOS
            else 0
        )

        sesion.execute(
            text(
                """
                UPDATE sesiones
                SET ultima_actividad = :momento,
                    segundos_activos =
                        segundos_activos + :segundos
                WHERE sesion_id = :sesion_id
                  AND estado = 'ACTIVA'
                """
            ),
            {
                "momento": momento,
                "segundos": segundos_a_sumar,
                "sesion_id": sesion_id,
            },
        )

        sesion.commit()

    return True


def cerrar_sesion(
    sesion_id,
    motivo="CIERRE_ALUMNO",
):

    momento = obtener_momento_actual()

    conexion = obtener_conexion()

    with conexion.session as sesion:

        sesion.execute(
            text(
                """
                UPDATE sesiones

                SET hora_fin = :momento,
                    ultima_actividad = :momento,
                    estado = 'CERRADA',
                    cierre_motivo = :motivo

                WHERE sesion_id = :sesion_id
                  AND estado = 'ACTIVA'
                """
            ),
            {
                "momento": momento,
                "motivo": motivo,
                "sesion_id": sesion_id,
            },
        )

        sesion.commit()


def expirar_sesiones_abandonadas():

    momento = obtener_momento_actual()

    limite = momento - timedelta(
        minutes=EXPIRACION_SESION_MINUTOS
    )

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultado = sesion.execute(
            text(
                """
                UPDATE sesiones

                SET hora_fin = ultima_actividad,
                    estado = 'EXPIRADA',
                    cierre_motivo = 'INACTIVIDAD'

                WHERE estado = 'ACTIVA'
                  AND ultima_actividad < :limite
                """
            ),
            {
                "limite": limite,
            },
        )

        sesion.commit()

        return resultado.rowcount
