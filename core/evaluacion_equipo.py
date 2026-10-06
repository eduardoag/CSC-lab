from sqlalchemy import text

from core.base_datos import obtener_conexion


DECISIONES_REVISION_VALIDAS = {
    "REQUIERE_AJUSTES",
    "APROBADA",
}


class EvaluacionEquipoError(RuntimeError):
    """Error de dominio al revisar una entrega de equipo."""


def _normalizar_id(valor, nombre):
    valor = str(valor or "").strip()
    if not valor:
        raise ValueError(f"{nombre} no puede estar vacío.")
    return valor


def _normalizar_decision(decision):
    decision = str(decision or "").strip().upper()
    if decision not in DECISIONES_REVISION_VALIDAS:
        raise ValueError(f"Decisión de revisión no válida: {decision}")
    return decision


def _normalizar_devolucion(devolucion):
    devolucion = str(devolucion or "").strip()
    if not devolucion:
        raise ValueError("La devolución docente no puede estar vacía.")
    return devolucion


def revisar_entrega_equipo_en_sesion(
    sesion,
    equipo_id,
    mision_id,
    decision,
    devolucion,
):
    """
    Revisa la última entrega pendiente de un equipo SIN commit/rollback.

    La sesión exterior es propietaria de la transacción.
    Sólo permite:
      PENDIENTE_REVISION -> REQUIERE_AJUSTES
      PENDIENTE_REVISION -> APROBADA
    """
    equipo_id = _normalizar_id(equipo_id, "equipo_id")
    mision_id = _normalizar_id(mision_id, "mision_id")
    decision = _normalizar_decision(decision)
    devolucion = _normalizar_devolucion(devolucion)

    progreso = sesion.execute(
        text("""
            SELECT progreso_equipo_id, equipo_id, curso, mision_id,
                   estado, etapa_actual, ultima_version_entregada
            FROM progreso_equipo_misiones
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
            FOR UPDATE
        """),
        {
            "equipo_id": equipo_id,
            "mision_id": mision_id,
        },
    ).mappings().first()

    if progreso is None:
        raise EvaluacionEquipoError(
            "No existe progreso para esta misión del equipo."
        )

    if progreso["estado"] != "PENDIENTE_REVISION":
        raise EvaluacionEquipoError(
            "La misión ya no está pendiente de revisión."
        )

    version_entrega = int(progreso["ultima_version_entregada"] or 0)
    if version_entrega < 1:
        raise EvaluacionEquipoError(
            "La misión está pendiente de revisión pero no tiene una entrega válida."
        )

    ficha = sesion.execute(
        text("""
            SELECT ficha_equipo_id, equipo_id, curso, mision_id,
                   version_entrega, contenido, descripcion_cambios,
                   actor_alumno_id, fecha_envio
            FROM fichas_equipo_mision
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
              AND version_entrega = :version_entrega
            LIMIT 1
        """),
        {
            "equipo_id": equipo_id,
            "mision_id": mision_id,
            "version_entrega": version_entrega,
        },
    ).mappings().first()

    if ficha is None:
        raise EvaluacionEquipoError(
            "No se encontró la Ficha correspondiente a la última entrega."
        )

    revision_existente = sesion.execute(
        text("""
            SELECT revision_docente_id
            FROM revisiones_docente_equipo
            WHERE ficha_equipo_id = :ficha_equipo_id
            LIMIT 1
        """),
        {"ficha_equipo_id": ficha["ficha_equipo_id"]},
    ).first()

    if revision_existente is not None:
        raise EvaluacionEquipoError(
            "Esta entrega ya fue revisada por el docente."
        )

    revision = sesion.execute(
        text("""
            INSERT INTO revisiones_docente_equipo (
                ficha_equipo_id,
                decision,
                devolucion
            )
            VALUES (
                :ficha_equipo_id,
                :decision,
                :devolucion
            )
            RETURNING revision_docente_id, ficha_equipo_id,
                      decision, devolucion, fecha_revision
        """),
        {
            "ficha_equipo_id": ficha["ficha_equipo_id"],
            "decision": decision,
            "devolucion": devolucion,
        },
    ).mappings().one()

    progreso_actualizado = sesion.execute(
        text("""
            UPDATE progreso_equipo_misiones
            SET estado = :estado,
                fecha_revision = CURRENT_TIMESTAMP,
                fecha_ultima_actividad = CURRENT_TIMESTAMP
            WHERE progreso_equipo_id = :progreso_equipo_id
            RETURNING progreso_equipo_id, equipo_id, curso, mision_id,
                      estado, etapa_actual, fecha_inicio,
                      fecha_ultima_actividad, fecha_envio, fecha_revision,
                      ultima_version_entregada
        """),
        {
            "estado": decision,
            "progreso_equipo_id": progreso["progreso_equipo_id"],
        },
    ).mappings().one()

    return {
        "revision": dict(revision),
        "ficha": dict(ficha),
        "progreso": dict(progreso_actualizado),
    }


def revisar_entrega_equipo(
    equipo_id,
    mision_id,
    decision,
    devolucion,
):
    """Wrapper autónomo: abre transacción y hace commit/rollback."""
    conexion = obtener_conexion()

    with conexion.session as sesion:
        try:
            resultado = revisar_entrega_equipo_en_sesion(
                sesion,
                equipo_id,
                mision_id,
                decision,
                devolucion,
            )
            sesion.commit()
            return resultado
        except Exception:
            sesion.rollback()
            raise
