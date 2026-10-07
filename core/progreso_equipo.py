from sqlalchemy import text

from core.base_datos import obtener_conexion
from core.equipos_misiones import validar_contexto_equipo_en_sesion
from core.prerrequisitos_misiones import validar_prerrequisitos_equipo_en_sesion


ESTADOS_PERSISTIDOS = {
    "EN_PROGRESO",
    "PENDIENTE_REVISION",
    "REQUIERE_AJUSTES",
    "APROBADA",
}

ESTADOS_EDITABLES = {
    "EN_PROGRESO",
    "REQUIERE_AJUSTES",
}


class EstadoProgresoEquipoError(RuntimeError):
    """El estado actual de la misión no permite la operación solicitada."""


def _normalizar_id(valor, nombre):
    valor = str(valor or "").strip()
    if not valor:
        raise ValueError(f"{nombre} no puede estar vacío.")
    return valor


def _normalizar_orden_etapas(orden_etapas):
    if isinstance(orden_etapas, (str, bytes)) or orden_etapas is None:
        raise ValueError("orden_etapas debe ser una secuencia de etapas.")

    etapas = tuple(_normalizar_id(etapa, "etapa") for etapa in orden_etapas)

    if not etapas:
        raise ValueError("orden_etapas no puede estar vacío.")

    if len(set(etapas)) != len(etapas):
        raise ValueError("orden_etapas no puede contener etapas duplicadas.")

    return etapas


def obtener_progreso_equipo_en_sesion(sesion, alumno_id, equipo_id, mision_id):
    """
    Devuelve el progreso persistido del equipo.

    None significa NO_INICIADA. NO_INICIADA nunca se persiste.
    """
    contexto = validar_contexto_equipo_en_sesion(sesion, alumno_id, equipo_id)
    mision_id = _normalizar_id(mision_id, "mision_id")

    fila = sesion.execute(
        text("""
            SELECT progreso_equipo_id, equipo_id, curso, mision_id,
                   estado, etapa_actual, iniciada_por_alumno_id,
                   fecha_inicio, fecha_ultima_actividad,
                   fecha_envio, fecha_revision,
                   ultima_version_entregada
            FROM progreso_equipo_misiones
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
            LIMIT 1
        """),
        {
            "equipo_id": contexto["equipo_id"],
            "mision_id": mision_id,
        },
    ).mappings().first()

    return dict(fila) if fila else None


def iniciar_mision_equipo_en_sesion(
    sesion,
    alumno_id,
    equipo_id,
    mision_id,
    etapa_inicial,
    prerrequisitos=(),
):
    """
    Inicia una misión grupal SIN hacer commit.

    Sólo crea EN_PROGRESO. Si ya existe progreso, no lo reinicia ni lo pisa.
    """
    contexto = validar_contexto_equipo_en_sesion(sesion, alumno_id, equipo_id)
    mision_id = _normalizar_id(mision_id, "mision_id")
    etapa_inicial = _normalizar_id(etapa_inicial, "etapa_inicial")

    validar_prerrequisitos_equipo_en_sesion(
        sesion,
        contexto["equipo_id"],
        mision_id,
        prerrequisitos,
    )

    creada = sesion.execute(
        text("""
            INSERT INTO progreso_equipo_misiones (
                equipo_id, curso, mision_id, estado, etapa_actual,
                iniciada_por_alumno_id, fecha_ultima_actividad
            )
            VALUES (
                :equipo_id, :curso, :mision_id, 'EN_PROGRESO',
                :etapa_actual, :actor, CURRENT_TIMESTAMP
            )
            ON CONFLICT (equipo_id, mision_id) DO NOTHING
            RETURNING progreso_equipo_id, equipo_id, curso, mision_id,
                      estado, etapa_actual, iniciada_por_alumno_id,
                      fecha_inicio, fecha_ultima_actividad,
                      fecha_envio, fecha_revision,
                      ultima_version_entregada
        """),
        {
            "equipo_id": contexto["equipo_id"],
            "curso": contexto["curso"],
            "mision_id": mision_id,
            "etapa_actual": etapa_inicial,
            "actor": contexto["alumno_id"],
        },
    ).mappings().first()

    if creada is not None:
        return dict(creada)

    existente = sesion.execute(
        text("""
            SELECT progreso_equipo_id, equipo_id, curso, mision_id,
                   estado, etapa_actual, iniciada_por_alumno_id,
                   fecha_inicio, fecha_ultima_actividad,
                   fecha_envio, fecha_revision,
                   ultima_version_entregada
            FROM progreso_equipo_misiones
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
        """),
        {
            "equipo_id": contexto["equipo_id"],
            "mision_id": mision_id,
        },
    ).mappings().one()

    return dict(existente)


def verificar_mision_equipo_editable_en_sesion(
    sesion, alumno_id, equipo_id, mision_id, bloquear=False
):
    """
    Exige progreso existente y un estado editable.

    bloquear=True aplica FOR UPDATE para futuras transacciones críticas.
    """
    contexto = validar_contexto_equipo_en_sesion(sesion, alumno_id, equipo_id)
    mision_id = _normalizar_id(mision_id, "mision_id")
    bloqueo = " FOR UPDATE" if bloquear else ""

    fila = sesion.execute(
        text("""
            SELECT progreso_equipo_id, equipo_id, curso, mision_id,
                   estado, etapa_actual, iniciada_por_alumno_id,
                   fecha_inicio, fecha_ultima_actividad,
                   fecha_envio, fecha_revision,
                   ultima_version_entregada
            FROM progreso_equipo_misiones
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
        """ + bloqueo),
        {
            "equipo_id": contexto["equipo_id"],
            "mision_id": mision_id,
        },
    ).mappings().first()

    if fila is None:
        raise EstadoProgresoEquipoError(
            "La misión todavía no fue iniciada por el equipo."
        )

    if fila["estado"] not in ESTADOS_EDITABLES:
        raise EstadoProgresoEquipoError(
            f"La misión no admite edición mientras está en estado "
            f"{fila['estado']}."
        )

    return dict(fila)


def actualizar_etapa_equipo_en_sesion(
    sesion,
    alumno_id,
    equipo_id,
    mision_id,
    etapa_visitada,
    orden_etapas,
):
    """
    Registra la etapa más avanzada alcanzada SIN hacer commit.

    La navegación puede volver a etapas anteriores, pero etapa_actual nunca
    retrocede. El orden de etapas pertenece a cada misión y se recibe como
    argumento para mantener este motor universal.
    """
    contexto = validar_contexto_equipo_en_sesion(sesion, alumno_id, equipo_id)
    mision_id = _normalizar_id(mision_id, "mision_id")
    etapa_visitada = _normalizar_id(etapa_visitada, "etapa_visitada")
    etapas = _normalizar_orden_etapas(orden_etapas)

    if etapa_visitada not in etapas:
        raise ValueError(
            f"La etapa {etapa_visitada!r} no pertenece al orden de etapas "
            f"de la misión."
        )

    progreso = verificar_mision_equipo_editable_en_sesion(
        sesion,
        contexto["alumno_id"],
        contexto["equipo_id"],
        mision_id,
        bloquear=True,
    )

    etapa_guardada = progreso["etapa_actual"]
    if etapa_guardada not in etapas:
        raise EstadoProgresoEquipoError(
            "La etapa actual persistida no pertenece al orden de etapas "
            "de la misión."
        )

    indice_guardado = etapas.index(etapa_guardada)
    indice_visitado = etapas.index(etapa_visitada)

    # Volver a una etapa anterior es navegación válida, pero no debe
    # hacer retroceder el indicador de progreso.
    if indice_visitado <= indice_guardado:
        return progreso

    actualizada = sesion.execute(
        text("""
            UPDATE progreso_equipo_misiones
            SET curso = :curso,
                etapa_actual = :etapa_actual,
                fecha_ultima_actividad = CURRENT_TIMESTAMP
            WHERE progreso_equipo_id = :progreso_id
            RETURNING progreso_equipo_id, equipo_id, curso, mision_id,
                      estado, etapa_actual, iniciada_por_alumno_id,
                      fecha_inicio, fecha_ultima_actividad,
                      fecha_envio, fecha_revision,
                      ultima_version_entregada
        """),
        {
            "curso": contexto["curso"],
            "etapa_actual": etapa_visitada,
            "progreso_id": progreso["progreso_equipo_id"],
        },
    ).mappings().one()

    return dict(actualizada)


def obtener_progreso_equipo(alumno_id, equipo_id, mision_id):
    conexion = obtener_conexion()
    with conexion.session as sesion:
        return obtener_progreso_equipo_en_sesion(
            sesion, alumno_id, equipo_id, mision_id
        )


def iniciar_mision_equipo(
    alumno_id,
    equipo_id,
    mision_id,
    etapa_inicial,
    prerrequisitos=(),
):
    conexion = obtener_conexion()
    with conexion.session as sesion:
        try:
            resultado = iniciar_mision_equipo_en_sesion(
                sesion,
                alumno_id,
                equipo_id,
                mision_id,
                etapa_inicial,
                prerrequisitos,
            )
            sesion.commit()
            return resultado
        except Exception:
            sesion.rollback()
            raise


def actualizar_etapa_equipo(
    alumno_id,
    equipo_id,
    mision_id,
    etapa_visitada,
    orden_etapas,
):
    conexion = obtener_conexion()
    with conexion.session as sesion:
        try:
            resultado = actualizar_etapa_equipo_en_sesion(
                sesion,
                alumno_id,
                equipo_id,
                mision_id,
                etapa_visitada,
                orden_etapas,
            )
            sesion.commit()
            return resultado
        except Exception:
            sesion.rollback()
            raise
