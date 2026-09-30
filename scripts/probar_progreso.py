from sqlalchemy import text

from core.autenticacion import obtener_alumno_por_id
from core.base_datos import obtener_conexion
from core.bitacora import registrar_evento
from core.progreso import (
    obtener_progreso,
    iniciar_mision,
    actualizar_etapa,
    cambiar_estado,
)


ALUMNO_ID = "CSC-3A-001"
MISION_ID = "TEST-M01"


def mostrar_progreso(titulo):

    progreso = obtener_progreso(
        ALUMNO_ID,
        MISION_ID,
    )

    print()
    print(titulo)
    print("-" * 60)

    if progreso is None:
        print("Sin registro de progreso.")
        return

    print(f"Alumno:       {progreso['alumno_id']}")
    print(f"Misión:       {progreso['mision_id']}")
    print(f"Estado:       {progreso['estado']}")
    print(f"Etapa actual: {progreso['etapa_actual']}")
    print(f"Inicio:       {progreso['fecha_inicio']}")
    print(f"Última act.:  {progreso['fecha_ultima_actividad']}")
    print(f"Envío:        {progreso['fecha_envio']}")
    print(f"Revisión:     {progreso['fecha_revision']}")


def mostrar_bitacora():

    conexion = obtener_conexion()

    with conexion.session as sesion:

        eventos = sesion.execute(
            text(
                """
                SELECT
                    fecha_hora,
                    tipo_evento,
                    etapa_id,
                    detalle
                FROM eventos_aprendizaje
                WHERE alumno_id = :alumno_id
                  AND mision_id = :mision_id
                ORDER BY fecha_hora
                """
            ),
            {
                "alumno_id": ALUMNO_ID,
                "mision_id": MISION_ID,
            },
        ).mappings().all()

    print()
    print("BITÁCORA")
    print("-" * 60)

    for evento in eventos:
        print(
            evento["fecha_hora"],
            "·",
            evento["tipo_evento"],
            "·",
            evento["etapa_id"] or "-",
            "·",
            evento["detalle"],
        )


def limpiar_prueba():

    conexion = obtener_conexion()

    with conexion.session as sesion:

        sesion.execute(
            text(
                """
                DELETE FROM eventos_aprendizaje
                WHERE alumno_id = :alumno_id
                  AND mision_id = :mision_id
                """
            ),
            {
                "alumno_id": ALUMNO_ID,
                "mision_id": MISION_ID,
            },
        )

        sesion.execute(
            text(
                """
                DELETE FROM progreso_misiones
                WHERE alumno_id = :alumno_id
                  AND mision_id = :mision_id
                """
            ),
            {
                "alumno_id": ALUMNO_ID,
                "mision_id": MISION_ID,
            },
        )

        sesion.commit()


def main():

    print()
    print("=" * 60)
    print("CSC LAB · PRUEBA CONTROLADA DE PROGRESO")
    print("=" * 60)

    alumno = obtener_alumno_por_id(ALUMNO_ID)

    if alumno is None:
        raise RuntimeError(
            f"No existe el alumno {ALUMNO_ID}"
        )

    print()
    print(
        f"Alumno de prueba: "
        f"{alumno['nombre']} {alumno['apellido']}"
    )

    # ------------------------------------------
    # 0. Limpiar cualquier prueba anterior
    # ------------------------------------------

    limpiar_prueba()

    mostrar_progreso(
        "0. ESTADO INICIAL"
    )

    # ------------------------------------------
    # 1. Iniciar misión
    # ------------------------------------------

    iniciar_mision(
        alumno,
        MISION_ID,
    )

    registrar_evento(
        alumno=alumno,
        mision_id=MISION_ID,
        tipo_evento="INICIO_MISION",
        detalle={
            "origen": "prueba_controlada"
        },
    )

    mostrar_progreso(
        "1. MISIÓN INICIADA"
    )

    # ------------------------------------------
    # 2. Completar OBSERVAR
    # ------------------------------------------

    actualizar_etapa(
        ALUMNO_ID,
        MISION_ID,
        "OBSERVAR",
    )

    registrar_evento(
        alumno=alumno,
        mision_id=MISION_ID,
        etapa_id="OBSERVAR",
        tipo_evento="ETAPA_COMPLETADA",
        detalle={
            "resultado": "ok",
            "origen": "prueba_controlada",
        },
    )

    mostrar_progreso(
        "2. OBSERVAR COMPLETADA"
    )

    # ------------------------------------------
    # 3. Guardar DEFINIR
    # ------------------------------------------

    actualizar_etapa(
        ALUMNO_ID,
        MISION_ID,
        "DEFINIR",
    )

    registrar_evento(
        alumno=alumno,
        mision_id=MISION_ID,
        etapa_id="DEFINIR",
        tipo_evento="RESPUESTA_GUARDADA",
        detalle={
            "origen": "prueba_controlada"
        },
    )

    # ------------------------------------------
    # 4. Agregar evidencia
    # ------------------------------------------

    actualizar_etapa(
        ALUMNO_ID,
        MISION_ID,
        "EVIDENCIAR",
    )

    registrar_evento(
        alumno=alumno,
        mision_id=MISION_ID,
        etapa_id="EVIDENCIAR",
        tipo_evento="EVIDENCIA_AGREGADA",
        detalle={
            "cantidad_evidencias": 1,
            "origen": "prueba_controlada",
        },
    )

    # ------------------------------------------
    # 5. Revisión del alumno
    # ------------------------------------------

    registrar_evento(
        alumno=alumno,
        mision_id=MISION_ID,
        tipo_evento="REVISION_REALIZADA",
        detalle={
            "origen": "prueba_controlada"
        },
    )

    # ------------------------------------------
    # 6. Enviar al profesor
    # ------------------------------------------

    cambiar_estado(
        ALUMNO_ID,
        MISION_ID,
        "PENDIENTE_REVISION",
    )

    registrar_evento(
        alumno=alumno,
        mision_id=MISION_ID,
        tipo_evento="ENVIO_REVISION",
        detalle={
            "estado": "PENDIENTE_REVISION",
            "origen": "prueba_controlada",
        },
    )

    mostrar_progreso(
        "3. RESULTADO FINAL"
    )

    mostrar_bitacora()

    print()
    print("=" * 60)
    print("✅ PRUEBA FINALIZADA")
    print("=" * 60)

    print()
    print(
        "IMPORTANTE: los datos TEST-M01 "
        "permanecen temporalmente en PostgreSQL "
        "para poder auditarlos."
    )
    print()


if __name__ == "__main__":
    main()
