from sqlalchemy import text
from core.base_datos import obtener_conexion

def _normalizar_id(valor, nombre):
    valor = str(valor or "").strip()
    if not valor:
        raise ValueError(f"{nombre} no puede estar vacío.")
    return valor

def obtener_contexto_equipo_en_sesion(sesion, alumno_id):
    """Resuelve y valida el equipo activo dentro de una sesión existente."""
    alumno_id = _normalizar_id(alumno_id, "alumno_id")
    filas = sesion.execute(text("""
        SELECT a.alumno_id, a.curso AS curso_alumno,
               e.equipo_id, e.curso AS curso_equipo,
               e.numero_equipo, e.nombre_equipo, e.nombre_empresa
        FROM alumnos a
        JOIN miembros_equipo m
          ON m.alumno_id = a.alumno_id AND m.activo = TRUE
        JOIN equipos e
          ON e.equipo_id = m.equipo_id AND e.activo = TRUE
        WHERE a.alumno_id = :alumno_id AND a.activo = TRUE
    """), {"alumno_id": alumno_id}).mappings().all()

    if not filas:
        raise PermissionError("El alumno no posee un contexto de equipo activo autorizado.")
    if len(filas) != 1:
        raise RuntimeError("Integridad inesperada: el alumno posee más de un equipo activo.")

    c = dict(filas[0])
    if c["curso_alumno"] != c["curso_equipo"]:
        raise RuntimeError("Integridad inesperada: el curso del alumno no coincide con el curso del equipo.")

    return {
        "alumno_id": c["alumno_id"],
        "equipo_id": c["equipo_id"],
        "curso": c["curso_equipo"],
        "numero_equipo": c["numero_equipo"],
        "nombre_equipo": c["nombre_equipo"],
        "nombre_empresa": c["nombre_empresa"],
    }

def validar_contexto_equipo_en_sesion(sesion, alumno_id, equipo_id):
    """Autoriza al alumno para un equipo concreto sin confiar en el equipo_id de la UI."""
    equipo_id = _normalizar_id(equipo_id, "equipo_id")
    contexto = obtener_contexto_equipo_en_sesion(sesion, alumno_id)
    if contexto["equipo_id"] != equipo_id:
        raise PermissionError("El alumno no está autorizado para operar sobre ese equipo.")
    return contexto

def obtener_contexto_equipo(alumno_id):
    conexion = obtener_conexion()
    with conexion.session as sesion:
        return obtener_contexto_equipo_en_sesion(sesion, alumno_id)

def validar_contexto_equipo(alumno_id, equipo_id):
    conexion = obtener_conexion()
    with conexion.session as sesion:
        return validar_contexto_equipo_en_sesion(sesion, alumno_id, equipo_id)
