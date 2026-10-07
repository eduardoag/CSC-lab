from sqlalchemy import text


class PrerrequisitoMisionError(RuntimeError):
    """La misión no puede iniciarse porque faltan prerrequisitos aprobados."""


def _normalizar_id(valor, nombre):
    valor = str(valor or "").strip()
    if not valor:
        raise ValueError(f"{nombre} no puede estar vacío.")
    return valor


def _normalizar_prerrequisitos(prerrequisitos):
    if prerrequisitos is None:
        return ()
    if isinstance(prerrequisitos, (str, bytes)):
        raise ValueError("prerrequisitos debe ser una colección de mision_id.")

    normalizados = tuple(
        _normalizar_id(mision_id, "prerrequisito")
        for mision_id in prerrequisitos
    )
    if len(set(normalizados)) != len(normalizados):
        raise ValueError("prerrequisitos no puede contener misiones duplicadas.")
    return normalizados


def validar_prerrequisitos_equipo_en_sesion(
    sesion, equipo_id, mision_id, prerrequisitos=()
):
    """Valida SIN commit/rollback que todos los prerrequisitos estén APROBADOS."""
    if sesion is None:
        raise ValueError("sesion es obligatoria.")

    equipo_id = _normalizar_id(equipo_id, "equipo_id")
    mision_id = _normalizar_id(mision_id, "mision_id")
    requeridos = _normalizar_prerrequisitos(prerrequisitos)

    if mision_id in requeridos:
        raise ValueError("Una misión no puede ser prerrequisito de sí misma.")

    if not requeridos:
        return {
            "habilitada": True,
            "mision_id": mision_id,
            "prerrequisitos": (),
        }

    filas = sesion.execute(
        text("""
            SELECT mision_id, estado
            FROM progreso_equipo_misiones
            WHERE equipo_id = :equipo_id
              AND mision_id = ANY(:prerrequisitos)
        """),
        {"equipo_id": equipo_id, "prerrequisitos": list(requeridos)},
    ).mappings().all()

    estados = {fila["mision_id"]: fila["estado"] for fila in filas}
    pendientes = [
        requerida for requerida in requeridos
        if estados.get(requerida) != "APROBADA"
    ]

    if pendientes:
        detalle = ", ".join(
            f"{requerida}={estados.get(requerida, 'NO_INICIADA')}"
            for requerida in pendientes
        )
        raise PrerrequisitoMisionError(
            f"La misión {mision_id} todavía está bloqueada. "
            f"Prerrequisitos pendientes: {detalle}."
        )

    return {
        "habilitada": True,
        "mision_id": mision_id,
        "prerrequisitos": requeridos,
    }
