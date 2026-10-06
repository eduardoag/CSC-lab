from sqlalchemy import text

from core.base_datos import obtener_conexion
from core.respuestas_equipo import (
    ConflictoBorradorEquipoError,
    guardar_borrador_equipo_en_sesion,
    obtener_respuesta_equipo_en_sesion,
)


MISION_PRUEBA = "__TEST_MOTOR_EQUIPO__"
ETAPA_PRUEBA = "__CONCURRENCIA__"
CAMPO_PRUEBA = "__BORRADOR__"


def main():
    print("=" * 76)
    print("CSC LAB · PRUEBA RESPUESTAS POR EQUIPO · ROLLBACK FINAL")
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

            # La prueba exige un espacio reservado que no exista previamente.
            previo = sesion.execute(text("""
                SELECT 1
                FROM respuestas_equipo_mision
                WHERE equipo_id = :equipo_id
                  AND mision_id = :mision_id
                  AND etapa_id = :etapa_id
                  AND campo_id = :campo_id
            """), {
                "equipo_id": candidato["equipo_id"],
                "mision_id": MISION_PRUEBA,
                "etapa_id": ETAPA_PRUEBA,
                "campo_id": CAMPO_PRUEBA,
            }).first()

            if previo is not None:
                raise RuntimeError(
                    "Existe un dato previo con los identificadores reservados "
                    "de esta prueba. No se modificó."
                )

            creada = guardar_borrador_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                ETAPA_PRUEBA,
                CAMPO_PRUEBA,
                "TEXTO_LARGO",
                "Borrador inicial de prueba",
                revision_esperada=None,
            )

            assert creada["revision_borrador"] == 0
            assert creada["version_actual"] == 0
            print("✓ Borrador creado en revision_borrador = 0.")
            print("✓ version_actual permanece en 0.")

            actualizada = guardar_borrador_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                ETAPA_PRUEBA,
                CAMPO_PRUEBA,
                "TEXTO_LARGO",
                "Edición válida de prueba",
                revision_esperada=0,
            )

            assert actualizada["revision_borrador"] == 1
            assert actualizada["version_actual"] == 0
            print("✓ Edición válida: revision_borrador 0 → 1.")
            print("✓ Editar borrador no crea versión pedagógica.")

            try:
                guardar_borrador_equipo_en_sesion(
                    sesion,
                    candidato["alumno_id"],
                    candidato["equipo_id"],
                    MISION_PRUEBA,
                    ETAPA_PRUEBA,
                    CAMPO_PRUEBA,
                    "TEXTO_LARGO",
                    "Edición obsoleta que NO debe guardarse",
                    revision_esperada=0,
                )
            except ConflictoBorradorEquipoError:
                print("✓ Edición obsoleta correctamente rechazada.")
            else:
                raise AssertionError(
                    "FALLO: una revisión obsoleta logró sobrescribir el borrador."
                )

            final = obtener_respuesta_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                ETAPA_PRUEBA,
                CAMPO_PRUEBA,
            )

            assert final["revision_borrador"] == 1
            assert final["contenido_actual"]["valor"] == "Edición válida de prueba"
            print("✓ El conflicto no alteró el contenido válido.")

        finally:
            # La prueba ejercita INSERT y UPDATE reales, pero no deja datos.
            sesion.rollback()

    # Verificación independiente posterior al rollback.
    with conexion.session as verificacion:
        resto = verificacion.execute(text("""
            SELECT COUNT(*)
            FROM respuestas_equipo_mision
            WHERE mision_id = :mision_id
              AND etapa_id = :etapa_id
              AND campo_id = :campo_id
        """), {
            "mision_id": MISION_PRUEBA,
            "etapa_id": ETAPA_PRUEBA,
            "campo_id": CAMPO_PRUEBA,
        }).scalar_one()

    if resto != 0:
        raise AssertionError(
            "FALLO: la prueba dejó datos persistidos en PostgreSQL."
        )

    print("✓ ROLLBACK final verificado: no quedaron datos de prueba.")
    print("✓ Prueba finalizada correctamente.")


if __name__ == "__main__":
    main()
