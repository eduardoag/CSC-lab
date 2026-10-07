from sqlalchemy import text

from core.base_datos import obtener_conexion
from core.prerrequisitos_misiones import PrerrequisitoMisionError
from core.progreso_equipo import iniciar_mision_equipo_en_sesion


MISION_PREVIA = "__TEST_PRERREQ_M01__"
MISION_DESTINO = "__TEST_PRERREQ_M02__"
ETAPA_INICIAL = "PREPARARSE"


def _contexto_prueba(sesion):
    fila = sesion.execute(text("""
        SELECT me.alumno_id, me.equipo_id, a.curso
        FROM miembros_equipo me
        JOIN equipos e ON e.equipo_id = me.equipo_id
        JOIN alumnos a ON a.alumno_id = me.alumno_id
        WHERE me.activo = TRUE AND e.activo = TRUE AND a.activo = TRUE
        ORDER BY me.equipo_id, me.alumno_id LIMIT 1
    """)).mappings().first()
    if fila is None:
        raise RuntimeError("No hay un equipo activo disponible para la prueba.")
    return dict(fila)


def _borrar(sesion, equipo_id):
    sesion.execute(text("""
        DELETE FROM progreso_equipo_misiones
        WHERE equipo_id=:e AND mision_id IN (:m1,:m2)
    """), {"e": equipo_id, "m1": MISION_PREVIA, "m2": MISION_DESTINO})


def _insertar_estado(sesion, ctx, estado):
    sesion.execute(text("""
        INSERT INTO progreso_equipo_misiones
        (equipo_id,curso,mision_id,estado,etapa_actual,
         iniciada_por_alumno_id,fecha_ultima_actividad)
        VALUES (:e,:c,:m,:s,:et,:a,CURRENT_TIMESTAMP)
    """), {"e": ctx["equipo_id"], "c": ctx["curso"], "m": MISION_PREVIA,
           "s": estado, "et": ETAPA_INICIAL, "a": ctx["alumno_id"]})


def _destino_inexistente(sesion, equipo_id):
    n = sesion.execute(text("""
        SELECT COUNT(*) FROM progreso_equipo_misiones
        WHERE equipo_id=:e AND mision_id=:m
    """), {"e": equipo_id, "m": MISION_DESTINO}).scalar_one()
    assert n == 0


def _probar_bloqueo(sesion, ctx, estado):
    _borrar(sesion, ctx["equipo_id"])
    if estado is not None:
        _insertar_estado(sesion, ctx, estado)
    try:
        iniciar_mision_equipo_en_sesion(
            sesion, ctx["alumno_id"], ctx["equipo_id"],
            MISION_DESTINO, ETAPA_INICIAL,
            prerrequisitos=(MISION_PREVIA,),
        )
        raise AssertionError("La misión destino debía permanecer bloqueada.")
    except PrerrequisitoMisionError:
        pass
    _destino_inexistente(sesion, ctx["equipo_id"])


def main():
    print("=" * 76)
    print("CSC LAB · PRUEBA DESBLOQUEO PEDAGÓGICO · ROLLBACK FINAL")
    print("=" * 76)

    conexion = obtener_conexion()
    equipo_id = None
    with conexion.session as sesion:
        ctx = _contexto_prueba(sesion)
        equipo_id = ctx["equipo_id"]
        _borrar(sesion, equipo_id)

        primera = iniciar_mision_equipo_en_sesion(
            sesion, ctx["alumno_id"], equipo_id, MISION_PREVIA, ETAPA_INICIAL
        )
        assert primera["estado"] == "EN_PROGRESO"
        print("✓ Una misión sin prerrequisitos puede iniciarse normalmente.")

        for estado, etiqueta in [
            (None, "NO_INICIADA"),
            ("EN_PROGRESO", "EN_PROGRESO"),
            ("PENDIENTE_REVISION", "PENDIENTE_REVISION"),
            ("REQUIERE_AJUSTES", "REQUIERE_AJUSTES"),
        ]:
            _probar_bloqueo(sesion, ctx, estado)
            print(f"✓ M01 {etiqueta} mantiene M02 bloqueada.")

        _borrar(sesion, equipo_id)
        _insertar_estado(sesion, ctx, "APROBADA")
        destino = iniciar_mision_equipo_en_sesion(
            sesion, ctx["alumno_id"], equipo_id, MISION_DESTINO, ETAPA_INICIAL,
            prerrequisitos=(MISION_PREVIA,),
        )
        assert destino["estado"] == "EN_PROGRESO"
        print("✓ M01 APROBADA habilita el inicio de M02.")

        repetida = iniciar_mision_equipo_en_sesion(
            sesion, ctx["alumno_id"], equipo_id, MISION_DESTINO, ETAPA_INICIAL,
            prerrequisitos=(MISION_PREVIA,),
        )
        assert repetida["progreso_equipo_id"] == destino["progreso_equipo_id"]
        print("✓ Reiniciar M02 no pisa ni duplica su progreso existente.")

        sesion.rollback()
        print("✓ ROLLBACK final ejecutado.")

    with conexion.session as verificacion:
        n = verificacion.execute(text("""
            SELECT COUNT(*) FROM progreso_equipo_misiones
            WHERE equipo_id=:e AND mision_id IN (:m1,:m2)
        """), {"e": equipo_id, "m1": MISION_PREVIA,
               "m2": MISION_DESTINO}).scalar_one()
        assert n == 0

    print("✓ No quedaron datos de prueba.")
    print("✓ Sólo APROBADA habilita la siguiente misión.")
    print("✓ Prueba finalizada correctamente.")


if __name__ == "__main__":
    main()
