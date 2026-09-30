import json

from sqlalchemy import text

from core.base_datos import obtener_conexion


def reenviar_mision(
    alumno_id,
    mision_id,
    descripcion_cambios,
):
    """
    Registra una reentrega después de una devolución.

    Actualiza el progreso y agrega un evento
    a la bitácora dentro de una única transacción.
    """

    descripcion_cambios = descripcion_cambios.strip()

    if not descripcion_cambios:
        raise ValueError(
            "El alumno debe describir los cambios realizados."
        )

    conexion = obtener_conexion()

    with conexion.session as sesion:

        progreso = sesion.execute(
            text("""
                SELECT estado, curso
                FROM progreso_misiones
                WHERE alumno_id = :alumno_id
                  AND mision_id = :mision_id
                FOR UPDATE
            """),
            {
                "alumno_id": alumno_id,
                "mision_id": mision_id,
            },
        ).mappings().first()

        if progreso is None:
            raise ValueError(
                "No existe progreso para esta misión."
            )

        if progreso["estado"] != "REQUIERE_AJUSTES":
            raise ValueError(
                "La misión no está habilitada para reentrega."
            )

        sesion.execute(
            text("""
                UPDATE progreso_misiones
                SET estado = 'PENDIENTE_REVISION',
                    fecha_envio = CURRENT_TIMESTAMP,
                    fecha_ultima_actividad = CURRENT_TIMESTAMP
                WHERE alumno_id = :alumno_id
                  AND mision_id = :mision_id
            """),
            {
                "alumno_id": alumno_id,
                "mision_id": mision_id,
            },
        )

        detalle = {
            "estado_anterior": "REQUIERE_AJUSTES",
            "estado_nuevo": "PENDIENTE_REVISION",
            "descripcion_cambios": descripcion_cambios,
        }

        sesion.execute(
            text("""
                INSERT INTO eventos_aprendizaje (
                    alumno_id,
                    curso,
                    mision_id,
                    tipo_evento,
                    detalle
                )
                VALUES (
                    :alumno_id,
                    :curso,
                    :mision_id,
                    'REENTREGA_MISION',
                    CAST(:detalle AS JSONB)
                )
            """),
            {
                "alumno_id": alumno_id,
                "curso": progreso["curso"],
                "mision_id": mision_id,
                "detalle": json.dumps(
                    detalle,
                    ensure_ascii=False,
                ),
            },
        )

        sesion.commit()
