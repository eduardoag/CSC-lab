from sqlalchemy import text

from core.base_datos import obtener_conexion
from core.progreso_equipo import EstadoProgresoEquipoError, iniciar_mision_equipo_en_sesion
from core.respuestas_equipo import guardar_borrador_equipo_en_sesion

MISION_PRUEBA = "__TEST_INTEGRACION_BORRADOR_ESTADO__"
ETAPA_PRUEBA = "PREPARARSE"
CAMPO_PRUEBA = "__campo_integracion__"


def _cambiar_estado_prueba(sesion, equipo_id, estado):
    sesion.execute(
        text("""
            UPDATE progreso_equipo_misiones
            SET estado = :estado
            WHERE equipo_id = :equipo_id AND mision_id = :mision_id
        """),
        {"estado": estado, "equipo_id": equipo_id, "mision_id": MISION_PRUEBA},
    )


def main():
    print("=" * 76)
    print("CSC LAB · PRUEBA INTEGRACIÓN PROGRESO ↔ BORRADORES · ROLLBACK FINAL")
    print("=" * 76)
    conexion = obtener_conexion()

    with conexion.session as sesion:
        try:
            candidato = sesion.execute(text("""
                SELECT a.alumno_id, e.equipo_id
                FROM alumnos a
                JOIN miembros_equipo m ON m.alumno_id=a.alumno_id AND m.activo=TRUE
                JOIN equipos e ON e.equipo_id=m.equipo_id AND e.activo=TRUE
                WHERE a.activo=TRUE
                ORDER BY a.alumno_id LIMIT 1
            """)).mappings().first()
            if candidato is None:
                raise RuntimeError("No existe un alumno activo con equipo activo para probar.")

            restos = sesion.execute(text("""
                SELECT
                  (SELECT COUNT(*) FROM progreso_equipo_misiones WHERE mision_id=:m) AS p,
                  (SELECT COUNT(*) FROM respuestas_equipo_mision WHERE mision_id=:m) AS r
            """), {"m": MISION_PRUEBA}).mappings().one()
            if restos["p"] or restos["r"]:
                raise RuntimeError("Existen datos previos reservados de esta prueba.")

            try:
                guardar_borrador_equipo_en_sesion(
                    sesion, candidato["alumno_id"], candidato["equipo_id"],
                    MISION_PRUEBA, ETAPA_PRUEBA, CAMPO_PRUEBA,
                    "TEXTO", "No debería guardarse"
                )
            except EstadoProgresoEquipoError:
                print("✓ NO_INICIADA bloquea la creación de borradores.")
            else:
                raise AssertionError("FALLO: NO_INICIADA permitió crear borrador.")

            iniciar_mision_equipo_en_sesion(
                sesion, candidato["alumno_id"], candidato["equipo_id"],
                MISION_PRUEBA, ETAPA_PRUEBA
            )

            creada = guardar_borrador_equipo_en_sesion(
                sesion, candidato["alumno_id"], candidato["equipo_id"],
                MISION_PRUEBA, ETAPA_PRUEBA, CAMPO_PRUEBA,
                "TEXTO", "Borrador inicial"
            )
            assert creada["revision_borrador"] == 0
            assert creada["version_actual"] == 0
            print("✓ EN_PROGRESO permite crear borradores.")

            _cambiar_estado_prueba(sesion, candidato["equipo_id"], "PENDIENTE_REVISION")
            try:
                guardar_borrador_equipo_en_sesion(
                    sesion, candidato["alumno_id"], candidato["equipo_id"],
                    MISION_PRUEBA, ETAPA_PRUEBA, CAMPO_PRUEBA,
                    "TEXTO", "Intento bloqueado", revision_esperada=0
                )
            except EstadoProgresoEquipoError:
                print("✓ PENDIENTE_REVISION bloquea modificar borradores.")
            else:
                raise AssertionError("FALLO: PENDIENTE_REVISION permitió modificar.")

            _cambiar_estado_prueba(sesion, candidato["equipo_id"], "REQUIERE_AJUSTES")
            ajustada = guardar_borrador_equipo_en_sesion(
                sesion, candidato["alumno_id"], candidato["equipo_id"],
                MISION_PRUEBA, ETAPA_PRUEBA, CAMPO_PRUEBA,
                "TEXTO", "Borrador corregido", revision_esperada=0
            )
            assert ajustada["revision_borrador"] == 1
            assert ajustada["version_actual"] == 0
            print("✓ REQUIERE_AJUSTES vuelve a permitir modificar borradores.")
            print("✓ Editar borrador sigue sin crear versión pedagógica.")

            _cambiar_estado_prueba(sesion, candidato["equipo_id"], "APROBADA")
            try:
                guardar_borrador_equipo_en_sesion(
                    sesion, candidato["alumno_id"], candidato["equipo_id"],
                    MISION_PRUEBA, ETAPA_PRUEBA, CAMPO_PRUEBA,
                    "TEXTO", "Intento posterior", revision_esperada=1
                )
            except EstadoProgresoEquipoError:
                print("✓ APROBADA bloquea modificar borradores.")
            else:
                raise AssertionError("FALLO: APROBADA permitió modificar.")

            final = sesion.execute(text("""
                SELECT contenido_actual, revision_borrador, version_actual
                FROM respuestas_equipo_mision
                WHERE equipo_id=:e AND mision_id=:m
                  AND etapa_id=:et AND campo_id=:c
            """), {
                "e": candidato["equipo_id"], "m": MISION_PRUEBA,
                "et": ETAPA_PRUEBA, "c": CAMPO_PRUEBA
            }).mappings().one()
            assert final["revision_borrador"] == 1
            assert final["version_actual"] == 0
            assert final["contenido_actual"]["valor"] == "Borrador corregido"
            print("✓ Los intentos bloqueados no alteraron el borrador válido.")
        finally:
            sesion.rollback()

    with conexion.session as verificacion:
        restos = verificacion.execute(text("""
            SELECT
              (SELECT COUNT(*) FROM progreso_equipo_misiones WHERE mision_id=:m) AS p,
              (SELECT COUNT(*) FROM respuestas_equipo_mision WHERE mision_id=:m) AS r
        """), {"m": MISION_PRUEBA}).mappings().one()

    assert restos["p"] == 0 and restos["r"] == 0
    print("✓ ROLLBACK final verificado: no quedaron datos de prueba.")
    print("✓ Prueba finalizada correctamente.")


if __name__ == "__main__":
    main()
