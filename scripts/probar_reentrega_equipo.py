from sqlalchemy import text

from core.base_datos import obtener_conexion
from core.entregas_equipo import EntregaEquipoError, entregar_mision_equipo_en_sesion
from core.progreso_equipo import iniciar_mision_equipo_en_sesion
from core.respuestas_equipo import guardar_borrador_equipo_en_sesion


MISION_PRUEBA = "__TEST_REENTREGA_EQUIPO__"

CAMPOS_REQUERIDOS = (
    {"etapa_id": "OBSERVAR", "campo_id": "campo_a"},
    {"etapa_id": "FORMULAR", "campo_id": "campo_b"},
)


def _obtener_candidato(sesion):
    candidato = sesion.execute(text("""
        SELECT a.alumno_id, a.curso, e.equipo_id
        FROM alumnos a
        JOIN miembros_equipo m
          ON m.alumno_id = a.alumno_id
         AND m.activo = TRUE
        JOIN equipos e
          ON e.equipo_id = m.equipo_id
         AND e.activo = TRUE
        WHERE a.activo = TRUE
        ORDER BY a.alumno_id
        LIMIT 1
    """)).mappings().first()

    if candidato is None:
        raise RuntimeError(
            "No existe un alumno activo con equipo activo para probar."
        )

    return candidato


def _verificar_sin_residuos(sesion, equipo_id):
    progreso = sesion.execute(text("""
        SELECT COUNT(*)
        FROM progreso_equipo_misiones
        WHERE equipo_id = :equipo_id
          AND mision_id = :mision_id
    """), {
        "equipo_id": equipo_id,
        "mision_id": MISION_PRUEBA,
    }).scalar_one()

    respuestas = sesion.execute(text("""
        SELECT COUNT(*)
        FROM respuestas_equipo_mision
        WHERE equipo_id = :equipo_id
          AND mision_id = :mision_id
    """), {
        "equipo_id": equipo_id,
        "mision_id": MISION_PRUEBA,
    }).scalar_one()

    fichas = sesion.execute(text("""
        SELECT COUNT(*)
        FROM fichas_equipo_mision
        WHERE equipo_id = :equipo_id
          AND mision_id = :mision_id
    """), {
        "equipo_id": equipo_id,
        "mision_id": MISION_PRUEBA,
    }).scalar_one()

    eventos = sesion.execute(text("""
        SELECT COUNT(*)
        FROM eventos_aprendizaje
        WHERE equipo_id = :equipo_id
          AND mision_id = :mision_id
    """), {
        "equipo_id": equipo_id,
        "mision_id": MISION_PRUEBA,
    }).scalar_one()

    versiones = sesion.execute(text("""
        SELECT COUNT(*)
        FROM versiones_respuesta_equipo_mision v
        JOIN respuestas_equipo_mision r
          ON r.respuesta_equipo_id = v.respuesta_equipo_id
        WHERE r.equipo_id = :equipo_id
          AND r.mision_id = :mision_id
    """), {
        "equipo_id": equipo_id,
        "mision_id": MISION_PRUEBA,
    }).scalar_one()

    if any((progreso, respuestas, fichas, eventos, versiones)):
        raise RuntimeError(
            "Existen datos previos con el identificador reservado "
            "de esta prueba. No se modificó nada."
        )


def main():
    print("=" * 76)
    print("CSC LAB · PRUEBA REENTREGA V1 → AJUSTES → V2 · ROLLBACK FINAL")
    print("=" * 76)

    conexion = obtener_conexion()

    with conexion.session as sesion:
        candidato = _obtener_candidato(sesion)
        _verificar_sin_residuos(sesion, candidato["equipo_id"])

        try:
            # -------------------------------------------------------------
            # 1. Preparar y entregar V1
            # -------------------------------------------------------------
            iniciar_mision_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                "OBSERVAR",
            )

            respuesta_a = guardar_borrador_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                "OBSERVAR",
                "campo_a",
                "TEXTO",
                "Contenido original A",
            )

            respuesta_b = guardar_borrador_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                "FORMULAR",
                "campo_b",
                "TEXTO_LARGO",
                "Contenido original B",
            )

            entrega_v1 = entregar_mision_equipo_en_sesion(
                sesion=sesion,
                alumno_id=candidato["alumno_id"],
                equipo_id=candidato["equipo_id"],
                mision_id=MISION_PRUEBA,
                campos_requeridos=CAMPOS_REQUERIDOS,
            )

            assert entrega_v1["version_entrega"] == 1
            assert entrega_v1["progreso"]["estado"] == "PENDIENTE_REVISION"
            assert entrega_v1["progreso"]["ultima_version_entregada"] == 1
            print("✓ V1 creada y enviada a revisión.")

            # Guardamos la evidencia histórica V1 para compararla después.
            historico_v1 = sesion.execute(text("""
                SELECT r.campo_id, v.contenido
                FROM versiones_respuesta_equipo_mision v
                JOIN respuestas_equipo_mision r
                  ON r.respuesta_equipo_id = v.respuesta_equipo_id
                WHERE r.equipo_id = :equipo_id
                  AND r.mision_id = :mision_id
                  AND v.version = 1
                ORDER BY r.campo_id
            """), {
                "equipo_id": candidato["equipo_id"],
                "mision_id": MISION_PRUEBA,
            }).mappings().all()

            assert len(historico_v1) == 2
            contenido_v1 = {
                fila["campo_id"]: fila["contenido"]
                for fila in historico_v1
            }

            ficha_v1 = sesion.execute(text("""
                SELECT ficha_equipo_id, contenido
                FROM fichas_equipo_mision
                WHERE equipo_id = :equipo_id
                  AND mision_id = :mision_id
                  AND version_entrega = 1
            """), {
                "equipo_id": candidato["equipo_id"],
                "mision_id": MISION_PRUEBA,
            }).mappings().one()

            ficha_v1_id = ficha_v1["ficha_equipo_id"]
            ficha_v1_contenido = ficha_v1["contenido"]

            # -------------------------------------------------------------
            # 2. Simular decisión docente REQUIERE_AJUSTES.
            # El motor docente real será la próxima capa.
            # -------------------------------------------------------------
            sesion.execute(text("""
                UPDATE progreso_equipo_misiones
                SET estado = 'REQUIERE_AJUSTES',
                    fecha_revision = CURRENT_TIMESTAMP
                WHERE equipo_id = :equipo_id
                  AND mision_id = :mision_id
            """), {
                "equipo_id": candidato["equipo_id"],
                "mision_id": MISION_PRUEBA,
            })

            print("✓ REQUIERE_AJUSTES simulado para habilitar la reentrega.")

            # -------------------------------------------------------------
            # 3. Modificar ambos borradores.
            # Deben partir de revision_borrador=0 y pasar a 1.
            # -------------------------------------------------------------
            assert respuesta_a["revision_borrador"] == 0
            assert respuesta_b["revision_borrador"] == 0

            corregida_a = guardar_borrador_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                "OBSERVAR",
                "campo_a",
                "TEXTO",
                "Contenido corregido A",
                revision_esperada=0,
            )

            corregida_b = guardar_borrador_equipo_en_sesion(
                sesion,
                candidato["alumno_id"],
                candidato["equipo_id"],
                MISION_PRUEBA,
                "FORMULAR",
                "campo_b",
                "TEXTO_LARGO",
                "Contenido corregido B",
                revision_esperada=0,
            )

            assert corregida_a["revision_borrador"] == 1
            assert corregida_b["revision_borrador"] == 1
            assert corregida_a["version_actual"] == 1
            assert corregida_b["version_actual"] == 1

            print("✓ Los borradores se corrigieron sin alterar version_actual=1.")

            # -------------------------------------------------------------
            # 4. V2 SIN descripcion_cambios debe ser rechazada.
            # -------------------------------------------------------------
            try:
                entregar_mision_equipo_en_sesion(
                    sesion=sesion,
                    alumno_id=candidato["alumno_id"],
                    equipo_id=candidato["equipo_id"],
                    mision_id=MISION_PRUEBA,
                    campos_requeridos=CAMPOS_REQUERIDOS,
                )
            except EntregaEquipoError:
                print("✓ V2 sin descripcion_cambios fue rechazada.")
            else:
                raise AssertionError(
                    "FALLO: se permitió V2 sin descripcion_cambios."
                )

            fichas_tras_rechazo = sesion.execute(text("""
                SELECT COUNT(*)
                FROM fichas_equipo_mision
                WHERE equipo_id = :equipo_id
                  AND mision_id = :mision_id
            """), {
                "equipo_id": candidato["equipo_id"],
                "mision_id": MISION_PRUEBA,
            }).scalar_one()

            versiones_tras_rechazo = sesion.execute(text("""
                SELECT COUNT(*)
                FROM versiones_respuesta_equipo_mision v
                JOIN respuestas_equipo_mision r
                  ON r.respuesta_equipo_id = v.respuesta_equipo_id
                WHERE r.equipo_id = :equipo_id
                  AND r.mision_id = :mision_id
            """), {
                "equipo_id": candidato["equipo_id"],
                "mision_id": MISION_PRUEBA,
            }).scalar_one()

            assert fichas_tras_rechazo == 1
            assert versiones_tras_rechazo == 2
            print("✓ El rechazo de V2 no creó Ficha ni versiones parciales.")

            # -------------------------------------------------------------
            # 5. V2 válida con descripción de cambios.
            # -------------------------------------------------------------
            descripcion = (
                "Revisamos las observaciones y reformulamos ambas respuestas."
            )

            entrega_v2 = entregar_mision_equipo_en_sesion(
                sesion=sesion,
                alumno_id=candidato["alumno_id"],
                equipo_id=candidato["equipo_id"],
                mision_id=MISION_PRUEBA,
                campos_requeridos=CAMPOS_REQUERIDOS,
                descripcion_cambios=descripcion,
            )

            assert entrega_v2["version_entrega"] == 2
            assert entrega_v2["progreso"]["estado"] == "PENDIENTE_REVISION"
            assert entrega_v2["progreso"]["ultima_version_entregada"] == 2

            print("✓ V2 válida creada con descripcion_cambios.")

            # -------------------------------------------------------------
            # 6. Deben coexistir Ficha V1 y Ficha V2.
            # -------------------------------------------------------------
            fichas = sesion.execute(text("""
                SELECT ficha_equipo_id, version_entrega,
                       contenido, descripcion_cambios
                FROM fichas_equipo_mision
                WHERE equipo_id = :equipo_id
                  AND mision_id = :mision_id
                ORDER BY version_entrega
            """), {
                "equipo_id": candidato["equipo_id"],
                "mision_id": MISION_PRUEBA,
            }).mappings().all()

            assert len(fichas) == 2
            assert [f["version_entrega"] for f in fichas] == [1, 2]
            assert fichas[0]["ficha_equipo_id"] == ficha_v1_id
            assert fichas[0]["contenido"] == ficha_v1_contenido
            assert fichas[0]["descripcion_cambios"] is None
            assert fichas[1]["descripcion_cambios"] == descripcion

            print("✓ Ficha V1 y Ficha V2 coexisten; V1 permanece intacta.")

            # -------------------------------------------------------------
            # 7. Las versiones históricas V1 deben seguir intactas y
            #    coexistir con V2.
            # -------------------------------------------------------------
            versiones = sesion.execute(text("""
                SELECT r.campo_id, v.version, v.contenido, v.motivo
                FROM versiones_respuesta_equipo_mision v
                JOIN respuestas_equipo_mision r
                  ON r.respuesta_equipo_id = v.respuesta_equipo_id
                WHERE r.equipo_id = :equipo_id
                  AND r.mision_id = :mision_id
                ORDER BY r.campo_id, v.version
            """), {
                "equipo_id": candidato["equipo_id"],
                "mision_id": MISION_PRUEBA,
            }).mappings().all()

            assert len(versiones) == 4

            v1_actual = {
                fila["campo_id"]: fila["contenido"]
                for fila in versiones
                if fila["version"] == 1
            }
            v2_actual = {
                fila["campo_id"]: fila["contenido"]
                for fila in versiones
                if fila["version"] == 2
            }

            assert v1_actual == contenido_v1
            assert v1_actual["campo_a"]["valor"] == "Contenido original A"
            assert v1_actual["campo_b"]["valor"] == "Contenido original B"
            assert v2_actual["campo_a"]["valor"] == "Contenido corregido A"
            assert v2_actual["campo_b"]["valor"] == "Contenido corregido B"

            motivos_v2 = {
                fila["motivo"]
                for fila in versiones
                if fila["version"] == 2
            }
            assert motivos_v2 == {descripcion}

            print("✓ Las versiones V1 permanecen intactas y coexisten con V2.")

            # -------------------------------------------------------------
            # 8. El borrador actual debe señalar V2.
            # -------------------------------------------------------------
            actuales = sesion.execute(text("""
                SELECT campo_id, version_actual, revision_borrador
                FROM respuestas_equipo_mision
                WHERE equipo_id = :equipo_id
                  AND mision_id = :mision_id
                ORDER BY campo_id
            """), {
                "equipo_id": candidato["equipo_id"],
                "mision_id": MISION_PRUEBA,
            }).mappings().all()

            assert len(actuales) == 2
            assert all(fila["version_actual"] == 2 for fila in actuales)
            assert all(fila["revision_borrador"] == 1 for fila in actuales)

            print("✓ Los borradores actuales apuntan a V2 sin perder su revisión.")

            # -------------------------------------------------------------
            # 9. Debe haber dos ENVIO_REVISION: uno para V1 y otro para V2.
            # -------------------------------------------------------------
            eventos = sesion.execute(text("""
                SELECT detalle
                FROM eventos_aprendizaje
                WHERE equipo_id = :equipo_id
                  AND mision_id = :mision_id
                  AND tipo_evento = 'ENVIO_REVISION'
                ORDER BY evento_id
            """), {
                "equipo_id": candidato["equipo_id"],
                "mision_id": MISION_PRUEBA,
            }).mappings().all()

            assert len(eventos) == 2
            assert [e["detalle"]["version_entrega"] for e in eventos] == [1, 2]

            print("✓ La bitácora conserva ENVIO_REVISION para V1 y V2.")

        finally:
            sesion.rollback()

    # -------------------------------------------------------------
    # 10. Verificación final fuera de la transacción.
    # -------------------------------------------------------------
    with conexion.session as verificacion:
        _verificar_sin_residuos(
            verificacion,
            candidato["equipo_id"],
        )

    print("✓ ROLLBACK final verificado: no quedaron datos de prueba.")
    print("✓ Historia pedagógica demostrada: V1 no se sobrescribe al crear V2.")
    print("✓ Prueba finalizada correctamente.")


if __name__ == "__main__":
    main()
