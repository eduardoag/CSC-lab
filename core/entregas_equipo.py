import json
from sqlalchemy import text
from core.base_datos import obtener_conexion
from core.bitacora import registrar_evento_en_sesion
from core.equipos_misiones import validar_contexto_equipo_en_sesion
from core.progreso_equipo import verificar_mision_equipo_editable_en_sesion

class EntregaEquipoError(RuntimeError):
    pass

def _id(v, n):
    v = str(v or "").strip()
    if not v: raise ValueError(f"{n} no puede estar vacío.")
    return v

def _campos(campos):
    if isinstance(campos, (str, bytes)) or campos is None:
        raise ValueError("campos_requeridos debe ser una colección.")
    r, vistos = [], set()
    for c in campos:
        if not isinstance(c, dict):
            raise ValueError("Cada campo requerido debe ser un diccionario.")
        k = (_id(c.get("etapa_id"), "etapa_id"), _id(c.get("campo_id"), "campo_id"))
        if k in vistos: raise ValueError(f"Campo requerido duplicado: {k[0]}.{k[1]}")
        vistos.add(k); r.append(k)
    if not r: raise ValueError("campos_requeridos no puede estar vacío.")
    return tuple(r)

def _tiene_valor(v):
    if v is None: return False
    if isinstance(v, dict): return bool(v) and any(_tiene_valor(x) for x in v.values())
    if isinstance(v, (list, tuple)): return any(_tiene_valor(x) for x in v)
    if isinstance(v, str): return bool(v.strip())
    return True

def _snapshot(respuestas):
    etapas = {}
    for r in respuestas:
        etapas.setdefault(r["etapa_id"], {})[r["campo_id"]] = {
            "tipo_respuesta": r["tipo_respuesta"],
            "contenido": r["contenido_actual"],
        }
    return {"etapas": etapas}

def entregar_mision_equipo_en_sesion(
    sesion, alumno_id, equipo_id, mision_id, campos_requeridos,
    descripcion_cambios=None, validador_mision=None, sesion_id=None
):
    """Consolida una entrega completa sin commit ni rollback."""
    if sesion is None: raise ValueError("sesion es obligatoria.")
    ctx = validar_contexto_equipo_en_sesion(sesion, alumno_id, equipo_id)
    mision_id = _id(mision_id, "mision_id")
    requeridos = _campos(campos_requeridos)
    if validador_mision is not None and not callable(validador_mision):
        raise ValueError("validador_mision debe ser invocable o None.")

    progreso = verificar_mision_equipo_editable_en_sesion(
        sesion, ctx["alumno_id"], ctx["equipo_id"], mision_id, bloquear=True
    )
    respuestas = sesion.execute(text("""
        SELECT respuesta_equipo_id, etapa_id, campo_id, tipo_respuesta,
               contenido_actual, version_actual, revision_borrador
        FROM respuestas_equipo_mision
        WHERE equipo_id=:e AND mision_id=:m
        ORDER BY etapa_id, campo_id FOR UPDATE
    """), {"e": ctx["equipo_id"], "m": mision_id}).mappings().all()

    por_clave = {(r["etapa_id"], r["campo_id"]): r for r in respuestas}
    faltan, vacios = [], []
    for k in requeridos:
        r = por_clave.get(k); nombre = f"{k[0]}.{k[1]}"
        if r is None: faltan.append(nombre)
        elif not _tiene_valor(r["contenido_actual"]): vacios.append(nombre)
    if faltan or vacios:
        p = []
        if faltan: p.append("faltan: " + ", ".join(faltan))
        if vacios: p.append("sin contenido: " + ", ".join(vacios))
        raise EntregaEquipoError("La misión todavía no puede enviarse; " + "; ".join(p) + ".")

    vn = progreso["ultima_version_entregada"] + 1
    descripcion = str(descripcion_cambios).strip() if descripcion_cambios is not None else ""
    descripcion = descripcion or None
    if vn >= 2 and not descripcion:
        raise EntregaEquipoError("Las reentregas V2 o superiores requieren descripción de cambios.")

    snapshot = _snapshot(respuestas)
    if validador_mision is not None: validador_mision(snapshot)

    for r in respuestas:
        sesion.execute(text("""
            INSERT INTO versiones_respuesta_equipo_mision
            (respuesta_equipo_id, version, contenido, origen, actor_alumno_id, motivo)
            VALUES (:rid,:v,CAST(:c AS JSONB),'ALUMNO',:actor,:motivo)
        """), {"rid": r["respuesta_equipo_id"], "v": vn,
               "c": json.dumps(r["contenido_actual"], ensure_ascii=False),
               "actor": ctx["alumno_id"], "motivo": descripcion})
        sesion.execute(text("""
            UPDATE respuestas_equipo_mision SET version_actual=:v
            WHERE respuesta_equipo_id=:rid
        """), {"v": vn, "rid": r["respuesta_equipo_id"]})

    ficha = sesion.execute(text("""
        INSERT INTO fichas_equipo_mision
        (equipo_id,curso,mision_id,version_entrega,contenido,descripcion_cambios,actor_alumno_id)
        VALUES (:e,:curso,:m,:v,CAST(:c AS JSONB),:d,:actor)
        RETURNING ficha_equipo_id,equipo_id,curso,mision_id,version_entrega,
                  contenido,descripcion_cambios,actor_alumno_id,fecha_envio
    """), {"e": ctx["equipo_id"], "curso": ctx["curso"], "m": mision_id, "v": vn,
           "c": json.dumps(snapshot, ensure_ascii=False), "d": descripcion,
           "actor": ctx["alumno_id"]}).mappings().one()

    prog = sesion.execute(text("""
        UPDATE progreso_equipo_misiones
        SET estado='PENDIENTE_REVISION', ultima_version_entregada=:v,
            fecha_envio=CURRENT_TIMESTAMP, fecha_ultima_actividad=CURRENT_TIMESTAMP
        WHERE progreso_equipo_id=:pid
        RETURNING progreso_equipo_id,equipo_id,curso,mision_id,estado,etapa_actual,
                  iniciada_por_alumno_id,fecha_inicio,fecha_ultima_actividad,
                  fecha_envio,fecha_revision,ultima_version_entregada
    """), {"v": vn, "pid": progreso["progreso_equipo_id"]}).mappings().one()

    registrar_evento_en_sesion(
        sesion=sesion, alumno={"alumno_id": ctx["alumno_id"], "curso": ctx["curso"]},
        mision_id=mision_id, tipo_evento="ENVIO_REVISION", sesion_id=sesion_id,
        etapa_id="FICHA", detalle={"version_entrega": vn}, equipo_id=ctx["equipo_id"]
    )
    return {"version_entrega": vn, "ficha": dict(ficha), "progreso": dict(prog)}

def entregar_mision_equipo(
    alumno_id, equipo_id, mision_id, campos_requeridos,
    descripcion_cambios=None, validador_mision=None, sesion_id=None
):
    conexion = obtener_conexion()
    with conexion.session as sesion:
        try:
            r = entregar_mision_equipo_en_sesion(
                sesion, alumno_id, equipo_id, mision_id, campos_requeridos,
                descripcion_cambios, validador_mision, sesion_id
            )
            sesion.commit()
            return r
        except Exception:
            sesion.rollback()
            raise
