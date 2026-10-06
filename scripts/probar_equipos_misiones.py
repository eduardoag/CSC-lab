from sqlalchemy import text
from core.base_datos import obtener_conexion
from core.equipos_misiones import obtener_contexto_equipo_en_sesion, validar_contexto_equipo_en_sesion

def main():
    print("=" * 76)
    print("CSC LAB · PRUEBA DE AUTORIZACIÓN DEL MOTOR POR EQUIPO · SOLO LECTURA")
    print("=" * 76)
    conexion = obtener_conexion()

    with conexion.session as sesion:
        sesion.execute(text("SET TRANSACTION READ ONLY;"))

        candidato = sesion.execute(text("""
            SELECT a.alumno_id, e.equipo_id
            FROM alumnos a
            JOIN miembros_equipo m
              ON m.alumno_id = a.alumno_id AND m.activo = TRUE
            JOIN equipos e
              ON e.equipo_id = m.equipo_id AND e.activo = TRUE
            WHERE a.activo = TRUE
            ORDER BY a.alumno_id
            LIMIT 1
        """)).mappings().first()

        if candidato is None:
            raise RuntimeError("No existe ningún alumno activo con equipo activo para probar.")

        contexto = obtener_contexto_equipo_en_sesion(sesion, candidato["alumno_id"])
        assert contexto["equipo_id"] == candidato["equipo_id"]
        print("✓ Alumno activo resuelto sin mostrar datos personales.")
        print("✓ Equipo activo resuelto desde PostgreSQL.")
        print("✓ Curso derivado y validado desde PostgreSQL.")

        autorizado = validar_contexto_equipo_en_sesion(
            sesion, candidato["alumno_id"], candidato["equipo_id"]
        )
        assert autorizado["equipo_id"] == candidato["equipo_id"]
        print("✓ Autorización positiva correcta.")

        otro_equipo = sesion.execute(text("""
            SELECT equipo_id FROM equipos
            WHERE activo = TRUE AND equipo_id <> :equipo_id
            ORDER BY equipo_id LIMIT 1
        """), {"equipo_id": candidato["equipo_id"]}).scalar_one_or_none()

        if otro_equipo is not None:
            try:
                validar_contexto_equipo_en_sesion(
                    sesion, candidato["alumno_id"], otro_equipo
                )
            except PermissionError:
                print("✓ Acceso a otro equipo correctamente rechazado.")
            else:
                raise AssertionError("FALLO DE SEGURIDAD: se autorizó un equipo ajeno.")

        sesion.rollback()

    print("✓ Prueba finalizada.")
    print("✓ No se modificó la base de datos.")

if __name__ == "__main__":
    main()
