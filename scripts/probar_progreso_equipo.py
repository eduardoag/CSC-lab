from sqlalchemy import text

from core.base_datos import obtener_conexion
from core.progreso_equipo import (
    EstadoProgresoEquipoError,
    actualizar_etapa_equipo_en_sesion,
    iniciar_mision_equipo_en_sesion,
    obtener_progreso_equipo_en_sesion,
    verificar_mision_equipo_editable_en_sesion,
)


MISION_PRUEBA = "__TEST_PROGRESO_EQUIPO__"

ORDEN_ETAPAS = (
    "PREPARARSE",
    "OBSERVAR",
    "COMPRENDER",
    "INVESTIGAR",
    "EVIDENCIAR",
    "FORMULAR",
    "FICHA",
)


def main():
    print("=" * 76)
    print("CSC LAB · PRUEBA PROGRESO POR EQUIPO · ROLLBACK FINAL")
    print("=" * 76)

    conexion = obtener_conexion()

    with conexion.session as sesion:
        try:
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
                raise RuntimeError(
                    "No existe un alumno activo con equipo activo para probar."
                )

            previo = sesion.execute(text("""
                SELECT 1
                FROM progreso_equipo_misiones
                WHERE equipo_id = :equipo_id
                  AND mision_id = :mision_id
            """), {
                "equipo_id": candidato["equipo_id"],
                "mision_id": MISION_PRUEBA,
            }).first()

            if previo is not None:
                raise RuntimeError(
                    "Existe un progreso previo con el identificador reservado "
                    "de esta prueba. No se modificó."
                )

            assert obtener_progreso_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
            ) is None
            print("✓ Ausencia de fila interpretada como NO_INICIADA.")

            try:
                verificar_mision_equipo_editable_en_sesion(
                    sesion,
                    candidato["alumno_id"],
                    candidato["equipo_id"],
                    MISION_PRUEBA,
                )
            except EstadoProgresoEquipoError:
                print("✓ NO_INICIADA no permite edición.")
            else:
                raise AssertionError("FALLO: NO_INICIADA permitió edición.")

            iniciada = iniciar_mision_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                "PREPARARSE",
            )
            assert iniciada["estado"] == "EN_PROGRESO"
            assert iniciada["etapa_actual"] == "PREPARARSE"
            assert iniciada["ultima_version_entregada"] == 0
            print("✓ Misión iniciada exclusivamente en EN_PROGRESO.")
            print("✓ Etapa inicial PREPARARSE registrada.")
            print("✓ ultima_version_entregada permanece en 0.")

            repetida = iniciar_mision_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                "OBSERVAR",
            )
            assert repetida["etapa_actual"] == "PREPARARSE"
            print("✓ Reiniciar no pisa el progreso ya existente.")

            editable = verificar_mision_equipo_editable_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                bloquear=True,
            )
            assert editable["estado"] == "EN_PROGRESO"
            print("✓ EN_PROGRESO permite edición.")

            observar = actualizar_etapa_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                "OBSERVAR",
                ORDEN_ETAPAS,
            )
            assert observar["etapa_actual"] == "OBSERVAR"
            assert observar["estado"] == "EN_PROGRESO"
            print("✓ PREPARARSE → OBSERVAR avanza.")

            comprender = actualizar_etapa_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                "COMPRENDER",
                ORDEN_ETAPAS,
            )
            assert comprender["etapa_actual"] == "COMPRENDER"
            print("✓ OBSERVAR → COMPRENDER avanza.")

            regreso = actualizar_etapa_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                "OBSERVAR",
                ORDEN_ETAPAS,
            )
            assert regreso["etapa_actual"] == "COMPRENDER"
            print("✓ COMPRENDER → OBSERVAR no retrocede etapa_actual.")

            try:
                actualizar_etapa_equipo_en_sesion(
                    sesion,
                    candidato["alumno_id"],
                    candidato["equipo_id"],
                    MISION_PRUEBA,
                    "ETAPA_INEXISTENTE",
                    ORDEN_ETAPAS,
                )
            except ValueError:
                print("✓ Una etapa inexistente es rechazada.")
            else:
                raise AssertionError(
                    "FALLO: una etapa inexistente fue aceptada."
                )

            for estado, debe_editar in (
                ("PENDIENTE_REVISION", False),
                ("REQUIERE_AJUSTES", True),
                ("APROBADA", False),
            ):
                sesion.execute(text("""
                    UPDATE progreso_equipo_misiones
                    SET estado = :estado
                    WHERE equipo_id = :equipo_id
                      AND mision_id = :mision_id
                """), {
                    "estado": estado,
                    "equipo_id": candidato["equipo_id"],
                    "mision_id": MISION_PRUEBA,
                })

                if debe_editar:
                    resultado = verificar_mision_equipo_editable_en_sesion(
                        sesion,
                        candidato["alumno_id"],
                        candidato["equipo_id"],
                        MISION_PRUEBA,
                    )
                    assert resultado["estado"] == estado
                    print("✓ REQUIERE_AJUSTES vuelve a habilitar edición.")
                else:
                    try:
                        verificar_mision_equipo_editable_en_sesion(
                            sesion,
                            candidato["alumno_id"],
                            candidato["equipo_id"],
                            MISION_PRUEBA,
                        )
                    except EstadoProgresoEquipoError:
                        print(f"✓ {estado} bloquea edición.")
                    else:
                        raise AssertionError(
                            f"FALLO: {estado} permitió edición."
                        )

        finally:
            sesion.rollback()

    with conexion.session as verificacion:
        resto = verificacion.execute(text("""
            SELECT COUNT(*)
            FROM progreso_equipo_misiones
            WHERE mision_id = :mision_id
        """), {"mision_id": MISION_PRUEBA}).scalar_one()

    if resto != 0:
        raise AssertionError(
            "FALLO: la prueba dejó progreso persistido en PostgreSQL."
        )

    print("✓ ROLLBACK final verificado: no quedó progreso de prueba.")
    print("✓ Prueba finalizada correctamente.")


if __name__ == "__main__":
    main()
