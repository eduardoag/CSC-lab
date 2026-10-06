from sqlalchemy import text

from core.base_datos import obtener_conexion
from core.entregas_equipo import entregar_mision_equipo_en_sesion
from core.evaluacion_equipo import (
    EvaluacionEquipoError,
    revisar_entrega_equipo_en_sesion,
)
from core.progreso_equipo import iniciar_mision_equipo_en_sesion
from core.respuestas_equipo import guardar_borrador_equipo_en_sesion


MISION_TEST = "__TEST_EVALUACION_EQUIPO__"
ETAPA_TEST = "OBSERVAR"
CAMPO_TEST = "observacion_test"


def _contexto_prueba(sesion):
    fila = sesion.execute(
        text("""
            SELECT me.alumno_id, me.equipo_id
            FROM miembros_equipo me
            JOIN equipos e ON e.equipo_id = me.equipo_id
            JOIN alumnos a ON a.alumno_id = me.alumno_id
            WHERE me.activo = TRUE
              AND e.activo = TRUE
              AND a.activo = TRUE
            ORDER BY me.equipo_id, me.alumno_id
            LIMIT 1
        """)
    ).mappings().first()

    if fila is None:
        raise RuntimeError("No hay un equipo activo disponible para la prueba.")

    return dict(fila)


def _limpiar(sesion, equipo_id):
    fichas = sesion.execute(
        text("""
            SELECT ficha_equipo_id
            FROM fichas_equipo_mision
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
        """),
        {"equipo_id": equipo_id, "mision_id": MISION_TEST},
    ).scalars().all()

    if fichas:
        sesion.execute(
            text("""
                DELETE FROM revisiones_docente_equipo
                WHERE ficha_equipo_id = ANY(:fichas)
            """),
            {"fichas": fichas},
        )

    respuestas = sesion.execute(
        text("""
            SELECT respuesta_equipo_id
            FROM respuestas_equipo_mision
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
        """),
        {"equipo_id": equipo_id, "mision_id": MISION_TEST},
    ).scalars().all()

    if respuestas:
        sesion.execute(
            text("""
                DELETE FROM versiones_respuesta_equipo_mision
                WHERE respuesta_equipo_id = ANY(:respuestas)
            """),
            {"respuestas": respuestas},
        )

    sesion.execute(
        text("""
            DELETE FROM eventos_aprendizaje
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
        """),
        {"equipo_id": equipo_id, "mision_id": MISION_TEST},
    )
    sesion.execute(
        text("""
            DELETE FROM fichas_equipo_mision
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
        """),
        {"equipo_id": equipo_id, "mision_id": MISION_TEST},
    )
    sesion.execute(
        text("""
            DELETE FROM respuestas_equipo_mision
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
        """),
        {"equipo_id": equipo_id, "mision_id": MISION_TEST},
    )
    sesion.execute(
        text("""
            DELETE FROM progreso_equipo_misiones
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
        """),
        {"equipo_id": equipo_id, "mision_id": MISION_TEST},
    )


def _contar(sesion, tabla, equipo_id):
    if tabla == "revisiones_docente_equipo":
        return sesion.execute(
            text("""
                SELECT COUNT(*)
                FROM revisiones_docente_equipo r
                JOIN fichas_equipo_mision f
                  ON f.ficha_equipo_id = r.ficha_equipo_id
                WHERE f.equipo_id = :equipo_id
                  AND f.mision_id = :mision_id
            """),
            {"equipo_id": equipo_id, "mision_id": MISION_TEST},
        ).scalar_one()

    return sesion.execute(
        text(f"""
            SELECT COUNT(*)
            FROM {tabla}
            WHERE equipo_id = :equipo_id
              AND mision_id = :mision_id
        """),
        {"equipo_id": equipo_id, "mision_id": MISION_TEST},
    ).scalar_one()


def main():
    print("=" * 76)
    print("CSC LAB · PRUEBA PROFESSOR CHECKPOINT · ROLLBACK FINAL")
    print("=" * 76)

    conexion = obtener_conexion()
    equipo_id = None

    with conexion.session as sesion:
        contexto = _contexto_prueba(sesion)
        alumno_id = contexto["alumno_id"]
        equipo_id = contexto["equipo_id"]

        _limpiar(sesion, equipo_id)

        iniciar_mision_equipo_en_sesion(
            sesion, alumno_id, equipo_id, MISION_TEST, ETAPA_TEST
        )

        guardar_borrador_equipo_en_sesion(
            sesion,
            alumno_id,
            equipo_id,
            MISION_TEST,
            ETAPA_TEST,
            CAMPO_TEST,
            "TEXTO_LARGO",
            "Versión original",
        )

        entregar_mision_equipo_en_sesion(
            sesion,
            alumno_id,
            equipo_id,
            MISION_TEST,
            [{"etapa_id": ETAPA_TEST, "campo_id": CAMPO_TEST}],
        )

        resultado_v1 = revisar_entrega_equipo_en_sesion(
            sesion,
            equipo_id,
            MISION_TEST,
            "REQUIERE_AJUSTES",
            "Profundicen la evidencia y expliquen mejor la observación.",
        )
        assert resultado_v1["progreso"]["estado"] == "REQUIERE_AJUSTES"
        assert resultado_v1["revision"]["decision"] == "REQUIERE_AJUSTES"
        print("✓ V1 fue revisada como REQUIERE_AJUSTES.")

        try:
            revisar_entrega_equipo_en_sesion(
                sesion,
                equipo_id,
                MISION_TEST,
                "APROBADA",
                "Intento de doble revisión.",
            )
            raise AssertionError("La doble revisión debía ser rechazada.")
        except EvaluacionEquipoError:
            pass
        print("✓ Una Ficha ya revisada no puede revisarse nuevamente.")

        borrador = sesion.execute(
            text("""
                SELECT revision_borrador
                FROM respuestas_equipo_mision
                WHERE equipo_id = :equipo_id
                  AND mision_id = :mision_id
                  AND etapa_id = :etapa_id
                  AND campo_id = :campo_id
            """),
            {
                "equipo_id": equipo_id,
                "mision_id": MISION_TEST,
                "etapa_id": ETAPA_TEST,
                "campo_id": CAMPO_TEST,
            },
        ).mappings().one()

        guardar_borrador_equipo_en_sesion(
            sesion,
            alumno_id,
            equipo_id,
            MISION_TEST,
            ETAPA_TEST,
            CAMPO_TEST,
            "TEXTO_LARGO",
            "Versión corregida con evidencia ampliada",
            revision_esperada=borrador["revision_borrador"],
        )

        entregar_mision_equipo_en_sesion(
            sesion,
            alumno_id,
            equipo_id,
            MISION_TEST,
            [{"etapa_id": ETAPA_TEST, "campo_id": CAMPO_TEST}],
            descripcion_cambios="Se amplió la evidencia solicitada por el docente.",
        )

        resultado_v2 = revisar_entrega_equipo_en_sesion(
            sesion,
            equipo_id,
            MISION_TEST,
            "APROBADA",
            "La reformulación incorpora la evidencia solicitada. Aprobada.",
        )
        assert resultado_v2["progreso"]["estado"] == "APROBADA"
        assert resultado_v2["revision"]["decision"] == "APROBADA"
        print("✓ V2 fue revisada como APROBADA.")

        assert _contar(
            sesion, "revisiones_docente_equipo", equipo_id
        ) == 2
        print("✓ V1 y V2 conservan revisiones docentes independientes.")

        try:
            revisar_entrega_equipo_en_sesion(
                sesion,
                equipo_id,
                MISION_TEST,
                "REQUIERE_AJUSTES",
                "No debería poder revisarse una misión aprobada.",
            )
            raise AssertionError("APROBADA debía bloquear nuevas revisiones.")
        except EvaluacionEquipoError:
            pass
        print("✓ APROBADA bloquea nuevas revisiones.")

        try:
            revisar_entrega_equipo_en_sesion(
                sesion,
                equipo_id,
                MISION_TEST,
                "INVALIDA",
                "Texto",
            )
            raise AssertionError("Una decisión inválida debía ser rechazada.")
        except ValueError:
            pass
        print("✓ Una decisión docente inválida es rechazada.")

        try:
            revisar_entrega_equipo_en_sesion(
                sesion,
                equipo_id,
                MISION_TEST,
                "APROBADA",
                "   ",
            )
            raise AssertionError("Una devolución vacía debía ser rechazada.")
        except ValueError:
            pass
        print("✓ La devolución docente es obligatoria.")

        sesion.rollback()
        print("✓ ROLLBACK final ejecutado.")

    with conexion.session as verificacion:
        assert _contar(
            verificacion, "progreso_equipo_misiones", equipo_id
        ) == 0
        assert _contar(
            verificacion, "respuestas_equipo_mision", equipo_id
        ) == 0
        assert _contar(
            verificacion, "fichas_equipo_mision", equipo_id
        ) == 0
        assert _contar(
            verificacion, "revisiones_docente_equipo", equipo_id
        ) == 0

    print("✓ No quedaron datos de prueba.")
    print("✓ Professor Checkpoint funciona V1 → AJUSTES → V2 → APROBADA.")
    print("✓ Prueba finalizada correctamente.")


if __name__ == "__main__":
    main()
