import json

from sqlalchemy import text

from core.base_datos import obtener_conexion


def registrar_evento(
    alumno,
    mision_id,
    tipo_evento,
    sesion_id=None,
    etapa_id=None,
    detalle=None,
):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        sesion.execute(
            text(
                """
                INSERT INTO eventos_aprendizaje (
                    alumno_id,
                    sesion_id,
                    curso,
                    mision_id,
                    etapa_id,
                    tipo_evento,
                    detalle
                )
                VALUES (
                    :alumno_id,
                    :sesion_id,
                    :curso,
                    :mision_id,
                    :etapa_id,
                    :tipo_evento,
                    CAST(:detalle AS JSONB)
                )
                """
            ),
            {
                "alumno_id": alumno["alumno_id"],
                "sesion_id": sesion_id,
                "curso": alumno["curso"],
                "mision_id": mision_id,
                "etapa_id": etapa_id,
                "tipo_evento": tipo_evento,
                "detalle": json.dumps(
                    detalle or {},
                    ensure_ascii=False,
                ),
            },
        )

        sesion.commit()
