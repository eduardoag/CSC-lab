from sqlalchemy import text

from core.base_datos import obtener_conexion


ESTADOS_VALIDOS = {
    "NO_INICIADA",
    "EN_PROGRESO",
    "PENDIENTE_REVISION",
    "REQUIERE_AJUSTES",
    "APROBADA",
}


def obtener_progreso(alumno_id, mision_id):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultado = sesion.execute(
            text(
                """
                SELECT *
                FROM progreso_misiones
                WHERE alumno_id = :alumno_id
                  AND mision_id = :mision_id
                LIMIT 1
                """
            ),
            {
                "alumno_id": alumno_id,
                "mision_id": mision_id,
            },
        ).mappings().first()

    if resultado is None:
        return None

    return dict(resultado)


def iniciar_mision(alumno, mision_id):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        sesion.execute(
            text(
                """
                INSERT INTO progreso_misiones (
                    alumno_id,
                    curso,
                    mision_id,
                    estado,
                    fecha_inicio,
                    fecha_ultima_actividad
                )
                VALUES (
                    :alumno_id,
                    :curso,
                    :mision_id,
                    'EN_PROGRESO',
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (alumno_id, mision_id)
                DO NOTHING
                """
            ),
            {
                "alumno_id": alumno["alumno_id"],
                "curso": alumno["curso"],
                "mision_id": mision_id,
            },
        )

        sesion.commit()


def actualizar_etapa(
    alumno_id,
    mision_id,
    etapa_actual,
):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        sesion.execute(
            text(
                """
                UPDATE progreso_misiones
                SET etapa_actual = :etapa_actual,
                    fecha_ultima_actividad =
                        CURRENT_TIMESTAMP
                WHERE alumno_id = :alumno_id
                  AND mision_id = :mision_id
                """
            ),
            {
                "alumno_id": alumno_id,
                "mision_id": mision_id,
                "etapa_actual": etapa_actual,
            },
        )

        sesion.commit()


def cambiar_estado(
    alumno_id,
    mision_id,
    nuevo_estado,
):

    if nuevo_estado not in ESTADOS_VALIDOS:
        raise ValueError(
            f"Estado de misión no válido: {nuevo_estado}"
        )

    conexion = obtener_conexion()

    with conexion.session as sesion:

        campos_extra = ""

        if nuevo_estado == "PENDIENTE_REVISION":
            campos_extra = """
                , fecha_envio = CURRENT_TIMESTAMP
            """

        elif nuevo_estado in {
            "REQUIERE_AJUSTES",
            "APROBADA",
        }:
            campos_extra = """
                , fecha_revision = CURRENT_TIMESTAMP
            """

        consulta = f"""
            UPDATE progreso_misiones
            SET estado = :estado,
                fecha_ultima_actividad =
                    CURRENT_TIMESTAMP
                {campos_extra}
            WHERE alumno_id = :alumno_id
              AND mision_id = :mision_id
        """

        sesion.execute(
            text(consulta),
            {
                "estado": nuevo_estado,
                "alumno_id": alumno_id,
                "mision_id": mision_id,
            },
        )

        sesion.commit()
