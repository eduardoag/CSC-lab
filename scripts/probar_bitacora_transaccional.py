from sqlalchemy import text

from core.base_datos import obtener_conexion
from core.bitacora import registrar_evento_en_sesion


MISION_PRUEBA = "__TEST_BITACORA_TRANSACCIONAL__"
TIPO_EVENTO_PRUEBA = "__TEST_EVENTO_TRANSACCIONAL__"


def main():
    print("=" * 76)
    print("CSC LAB · PRUEBA BITÁCORA TRANSACCIONAL · ROLLBACK FINAL")
    print("=" * 76)

    conexion = obtener_conexion()

    with conexion.session as sesion:
        candidato = sesion.execute(text("""
            SELECT a.alumno_id, a.curso, e.equipo_id
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
            raise RuntimeError(
                "No existe un alumno activo con equipo activo para probar."
            )

        previos = sesion.execute(text("""
            SELECT COUNT(*)
            FROM eventos_aprendizaje
            WHERE mision_id = :mision_id
              AND tipo_evento = :tipo_evento
        """), {
            "mision_id": MISION_PRUEBA,
            "tipo_evento": TIPO_EVENTO_PRUEBA,
        }).scalar_one()

        if previos:
            raise RuntimeError(
                "Existen eventos previos con los identificadores reservados."
            )

        alumno = {
            "alumno_id": candidato["alumno_id"],
            "curso": candidato["curso"],
        }

        try:
            registrar_evento_en_sesion(
                sesion=sesion,
                alumno=alumno,
                mision_id=MISION_PRUEBA,
                tipo_evento=TIPO_EVENTO_PRUEBA,
                etapa_id="FICHA",
                detalle={"version_entrega": 1, "prueba": True},
                equipo_id=candidato["equipo_id"],
            )

            evento = sesion.execute(text("""
                SELECT alumno_id, equipo_id, curso, etapa_id, detalle
                FROM eventos_aprendizaje
                WHERE mision_id = :mision_id
                  AND tipo_evento = :tipo_evento
            """), {
                "mision_id": MISION_PRUEBA,
                "tipo_evento": TIPO_EVENTO_PRUEBA,
            }).mappings().one()

            assert evento["alumno_id"] == candidato["alumno_id"]
            assert evento["equipo_id"] == candidato["equipo_id"]
            assert evento["curso"] == candidato["curso"]
            assert evento["etapa_id"] == "FICHA"
            assert evento["detalle"]["version_entrega"] == 1

            print("✓ registrar_evento_en_sesion inserta en la sesión exterior.")
            print("✓ El evento conserva actor alumno + equipo propietario.")
            print("✓ El detalle JSONB se registró correctamente.")
        finally:
            sesion.rollback()

    with conexion.session as verificacion:
        finales = verificacion.execute(text("""
            SELECT COUNT(*)
            FROM eventos_aprendizaje
            WHERE mision_id = :mision_id
              AND tipo_evento = :tipo_evento
        """), {
            "mision_id": MISION_PRUEBA,
            "tipo_evento": TIPO_EVENTO_PRUEBA,
        }).scalar_one()

    if finales != 0:
        raise AssertionError(
            "FALLO: el evento sobrevivió al rollback exterior."
        )

    print("✓ ROLLBACK exterior eliminó el evento: no hubo commit interno.")
    print("✓ Prueba finalizada correctamente.")


if __name__ == "__main__":
    main()
