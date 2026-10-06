import json

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from core.base_datos import obtener_conexion
from core.equipos_misiones import validar_contexto_equipo_en_sesion
from core.progreso_equipo import verificar_mision_equipo_editable_en_sesion


TIPOS_RESPUESTA_VALIDOS = {
    "TEXTO",
    "TEXTO_LARGO",
    "OPCION",
    "MULTIOPCION",
    "NUMERO",
    "ESCALA",
    "BOOLEANO",
    "JSON",
}


class ConflictoBorradorEquipoError(RuntimeError):
    """Otro integrante modificó el borrador desde que fue cargado."""


def _normalizar_id(valor, nombre):
    valor = str(valor or "").strip()
    if not valor:
        raise ValueError(f"{nombre} no puede estar vacío.")
    return valor


def _normalizar_tipo(tipo_respuesta):
    tipo = str(tipo_respuesta or "").strip().upper()
    if tipo not in TIPOS_RESPUESTA_VALIDOS:
        raise ValueError(f"Tipo de respuesta no válido: {tipo_respuesta}")
    return tipo


def _contenido_json(contenido):
    if isinstance(contenido, dict):
        normalizado = contenido
    elif isinstance(contenido, (list, tuple)):
        normalizado = {"valores": list(contenido)}
    else:
        normalizado = {"valor": contenido}

    json.dumps(normalizado, ensure_ascii=False)
    return normalizado


def obtener_respuesta_equipo_en_sesion(
    sesion, alumno_id, equipo_id, mision_id, etapa_id, campo_id
):
    contexto = validar_contexto_equipo_en_sesion(sesion, alumno_id, equipo_id)
    mision_id = _normalizar_id(mision_id, "mision_id")
    etapa_id = _normalizar_id(etapa_id, "etapa_id")
    campo_id = _normalizar_id(campo_id, "campo_id")

    fila = sesion.execute(
        text("""
            SELECT respuesta_equipo_id, equipo_id, curso, mision_id,
                   etapa_id, campo_id, tipo_respuesta, contenido_actual,
                   version_actual, revision_borrador,
                   actualizado_por_alumno_id,
                   fecha_creacion, fecha_actualizacion
            FROM respuestas_equipo_mision
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
              AND etapa_id = :etapa_id
              AND campo_id = :campo_id
            LIMIT 1
        """),
        {
            "equipo_id": contexto["equipo_id"],
            "mision_id": mision_id,
            "etapa_id": etapa_id,
            "campo_id": campo_id,
        },
    ).mappings().first()

    return dict(fila) if fila else None


def listar_respuestas_etapa_equipo_en_sesion(
    sesion, alumno_id, equipo_id, mision_id, etapa_id
):
    contexto = validar_contexto_equipo_en_sesion(sesion, alumno_id, equipo_id)
    mision_id = _normalizar_id(mision_id, "mision_id")
    etapa_id = _normalizar_id(etapa_id, "etapa_id")

    filas = sesion.execute(
        text("""
            SELECT respuesta_equipo_id, equipo_id, curso, mision_id,
                   etapa_id, campo_id, tipo_respuesta, contenido_actual,
                   version_actual, revision_borrador,
                   actualizado_por_alumno_id,
                   fecha_creacion, fecha_actualizacion
            FROM respuestas_equipo_mision
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
              AND etapa_id = :etapa_id
            ORDER BY campo_id
        """),
        {
            "equipo_id": contexto["equipo_id"],
            "mision_id": mision_id,
            "etapa_id": etapa_id,
        },
    ).mappings().all()

    return [dict(fila) for fila in filas]


def guardar_borrador_equipo_en_sesion(
    sesion,
    alumno_id,
    equipo_id,
    mision_id,
    etapa_id,
    campo_id,
    tipo_respuesta,
    contenido,
    revision_esperada=None,
):
    """
    Crea o actualiza un borrador grupal SIN hacer commit.

    Creación:
      revision_esperada debe ser None y la fila nace en revisión 0.

    Actualización:
      revision_esperada debe coincidir con revision_borrador.
      Si otro integrante guardó antes, se rechaza la escritura.
    """
    contexto = validar_contexto_equipo_en_sesion(sesion, alumno_id, equipo_id)
    mision_id = _normalizar_id(mision_id, "mision_id")
    etapa_id = _normalizar_id(etapa_id, "etapa_id")
    campo_id = _normalizar_id(campo_id, "campo_id")
    tipo = _normalizar_tipo(tipo_respuesta)
    contenido_normalizado = _contenido_json(contenido)
    contenido_serializado = json.dumps(contenido_normalizado, ensure_ascii=False)

    # Seguridad pedagógica: sólo se puede escribir si la misión del equipo
    # existe y su estado actual admite edición.
    verificar_mision_equipo_editable_en_sesion(
        sesion,
        contexto["alumno_id"],
        contexto["equipo_id"],
        mision_id,
    )

    existente = sesion.execute(
        text("""
            SELECT respuesta_equipo_id, revision_borrador
            FROM respuestas_equipo_mision
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
              AND etapa_id = :etapa_id
              AND campo_id = :campo_id
        """),
        {
            "equipo_id": contexto["equipo_id"],
            "mision_id": mision_id,
            "etapa_id": etapa_id,
            "campo_id": campo_id,
        },
    ).mappings().first()

    if existente is None:
        if revision_esperada is not None:
            raise ConflictoBorradorEquipoError(
                "El borrador ya no coincide con el estado esperado. "
                "Actualizá la información antes de volver a guardar."
            )

        # SAVEPOINT: si dos integrantes intentan crear el mismo campo a la vez,
        # una violación UNIQUE no invalida la transacción exterior.
        try:
            with sesion.begin_nested():
                creada = sesion.execute(
                    text("""
                        INSERT INTO respuestas_equipo_mision (
                            equipo_id, curso, mision_id, etapa_id, campo_id,
                            tipo_respuesta, contenido_actual,
                            actualizado_por_alumno_id
                        )
                        VALUES (
                            :equipo_id, :curso, :mision_id, :etapa_id, :campo_id,
                            :tipo_respuesta, CAST(:contenido AS JSONB),
                            :actor
                        )
                        RETURNING respuesta_equipo_id, equipo_id, curso,
                                  mision_id, etapa_id, campo_id, tipo_respuesta,
                                  contenido_actual, version_actual,
                                  revision_borrador,
                                  actualizado_por_alumno_id,
                                  fecha_creacion, fecha_actualizacion
                    """),
                    {
                        "equipo_id": contexto["equipo_id"],
                        "curso": contexto["curso"],
                        "mision_id": mision_id,
                        "etapa_id": etapa_id,
                        "campo_id": campo_id,
                        "tipo_respuesta": tipo,
                        "contenido": contenido_serializado,
                        "actor": contexto["alumno_id"],
                    },
                ).mappings().one()
        except IntegrityError as exc:
            raise ConflictoBorradorEquipoError(
                "Otro integrante creó este borrador al mismo tiempo. "
                "Actualizá la información antes de volver a guardar."
            ) from exc

        return dict(creada)

    if revision_esperada is None:
        raise ConflictoBorradorEquipoError(
            "El borrador ya existe. Actualizá la información antes de guardar."
        )

    try:
        revision_esperada = int(revision_esperada)
    except (TypeError, ValueError) as exc:
        raise ValueError("revision_esperada debe ser un entero.") from exc

    actualizada = sesion.execute(
        text("""
            UPDATE respuestas_equipo_mision
            SET curso = :curso,
                tipo_respuesta = :tipo_respuesta,
                contenido_actual = CAST(:contenido AS JSONB),
                revision_borrador = revision_borrador + 1,
                actualizado_por_alumno_id = :actor,
                fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE respuesta_equipo_id = :respuesta_equipo_id
              AND revision_borrador = :revision_esperada
            RETURNING respuesta_equipo_id, equipo_id, curso,
                      mision_id, etapa_id, campo_id, tipo_respuesta,
                      contenido_actual, version_actual, revision_borrador,
                      actualizado_por_alumno_id,
                      fecha_creacion, fecha_actualizacion
        """),
        {
            "curso": contexto["curso"],
            "tipo_respuesta": tipo,
            "contenido": contenido_serializado,
            "actor": contexto["alumno_id"],
            "respuesta_equipo_id": existente["respuesta_equipo_id"],
            "revision_esperada": revision_esperada,
        },
    ).mappings().first()

    if actualizada is None:
        raise ConflictoBorradorEquipoError(
            "La respuesta fue modificada por otro integrante del equipo. "
            "Actualizá la información antes de volver a guardar."
        )

    return dict(actualizada)


def obtener_respuesta_equipo(alumno_id, equipo_id, mision_id, etapa_id, campo_id):
    conexion = obtener_conexion()
    with conexion.session as sesion:
        return obtener_respuesta_equipo_en_sesion(
            sesion, alumno_id, equipo_id, mision_id, etapa_id, campo_id
        )


def listar_respuestas_etapa_equipo(
    alumno_id, equipo_id, mision_id, etapa_id
):
    conexion = obtener_conexion()
    with conexion.session as sesion:
        return listar_respuestas_etapa_equipo_en_sesion(
            sesion, alumno_id, equipo_id, mision_id, etapa_id
        )


def guardar_borrador_equipo(
    alumno_id,
    equipo_id,
    mision_id,
    etapa_id,
    campo_id,
    tipo_respuesta,
    contenido,
    revision_esperada=None,
):
    """Wrapper autónomo: abre transacción y hace commit/rollback."""
    conexion = obtener_conexion()
    with conexion.session as sesion:
        try:
            resultado = guardar_borrador_equipo_en_sesion(
                sesion,
                alumno_id,
                equipo_id,
                mision_id,
                etapa_id,
                campo_id,
                tipo_respuesta,
                contenido,
                revision_esperada,
            )
            sesion.commit()
            return resultado
        except Exception:
            sesion.rollback()
            raise
