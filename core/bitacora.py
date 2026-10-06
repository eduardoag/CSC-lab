import json

from sqlalchemy import text

from core.base_datos import obtener_conexion


def _normalizar_id_opcional(valor):
    if valor is None:
        return None
    valor = str(valor).strip()
    return valor or None


def registrar_evento_en_sesion(
    sesion,
    alumno,
    mision_id,
    tipo_evento,
    sesion_id=None,
    etapa_id=None,
    detalle=None,
    equipo_id=None,
):
    """
    Registra un evento dentro de una sesión SQLAlchemy existente.

    No abre conexión, no hace commit y no hace rollback.
    La transacción pertenece exclusivamente al llamador.
    """
    if sesion is None:
        raise ValueError("sesion es obligatoria.")
    if not isinstance(alumno, dict):
        raise ValueError("alumno debe ser un diccionario.")

    alumno_id = str(alumno.get("alumno_id") or "").strip()
    curso = str(alumno.get("curso") or "").strip()
    mision_id = str(mision_id or "").strip()
    tipo_evento = str(tipo_evento or "").strip()

    if not alumno_id:
        raise ValueError("alumno['alumno_id'] es obligatorio.")
    if not curso:
        raise ValueError("alumno['curso'] es obligatorio.")
    if not mision_id:
        raise ValueError("mision_id es obligatorio.")
    if not tipo_evento:
        raise ValueError("tipo_evento es obligatorio.")

    detalle_serializado = json.dumps(detalle or {}, ensure_ascii=False)

    sesion.execute(
        text("""
            INSERT INTO eventos_aprendizaje (
                alumno_id, sesion_id, curso, mision_id,
                etapa_id, tipo_evento, detalle, equipo_id
            )
            VALUES (
                :alumno_id, :sesion_id, :curso, :mision_id,
                :etapa_id, :tipo_evento, CAST(:detalle AS JSONB), :equipo_id
            )
        """),
        {
            "alumno_id": alumno_id,
            "sesion_id": _normalizar_id_opcional(sesion_id),
            "curso": curso,
            "mision_id": mision_id,
            "etapa_id": _normalizar_id_opcional(etapa_id),
            "tipo_evento": tipo_evento,
            "detalle": detalle_serializado,
            "equipo_id": _normalizar_id_opcional(equipo_id),
        },
    )


def registrar_evento(
    alumno,
    mision_id,
    tipo_evento,
    sesion_id=None,
    etapa_id=None,
    detalle=None,
    equipo_id=None,
):
    """
    Wrapper autónomo compatible con la API histórica.

    Los parámetros originales conservan su posición; equipo_id se agrega
    al final para no romper llamadas existentes.
    """
    conexion = obtener_conexion()

    with conexion.session as sesion:
        try:
            registrar_evento_en_sesion(
                sesion=sesion,
                alumno=alumno,
                mision_id=mision_id,
                tipo_evento=tipo_evento,
                sesion_id=sesion_id,
                etapa_id=etapa_id,
                detalle=detalle,
                equipo_id=equipo_id,
            )
            sesion.commit()
        except Exception:
            sesion.rollback()
            raise
