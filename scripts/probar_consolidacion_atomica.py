from sqlalchemy import text

from core.base_datos import obtener_conexion
from core.respuestas import (
    consolidar_etapa,
    guardar_borrador,
    obtener_historial,
    obtener_respuesta,
)

ALUMNO = "CSC-DEMO-001"
CURSO = "3A"
MISION = "TEST-ATOMICA"
ETAPA = "OBSERVAR"
CAMPOS = ["caso_a", "caso_b", "caso_c", "reflexion"]


def verificar_demo():
    conexion = obtener_conexion()
    with conexion.session as sesion:
        fila = sesion.execute(
            text("""
                SELECT tipo_alumno, activo
                FROM alumnos
                WHERE alumno_id = :alumno_id
            """),
            {"alumno_id": ALUMNO},
        ).mappings().first()

    if not fila or fila["tipo_alumno"] != "DEMO" or not fila["activo"]:
        raise RuntimeError("Prueba cancelada: CSC-DEMO-001 no es DEMO activo.")


def limpiar():
    conexion = obtener_conexion()
    with conexion.session as sesion:
        try:
            sesion.execute(
                text("""
                    DELETE FROM respuestas_mision
                    WHERE alumno_id = :alumno_id
                      AND mision_id = :mision_id
                """),
                {"alumno_id": ALUMNO, "mision_id": MISION},
            )
            sesion.commit()
        except Exception:
            sesion.rollback()
            raise


def main():
    print("CSC Lab · Prueba de consolidación atómica")
    print("----------------------------------------")

    verificar_demo()
    limpiar()
    print("✓ Entorno DEMO limpio")

    valores = {
        "caso_a": "PROBLEMA",
        "caso_b": "SOLUCION_DISFRAZADA",
        "caso_c": "PROBLEMA",
        "reflexion": "Primero comprendo el problema y después pienso soluciones.",
    }

    for campo, valor in valores.items():
        guardar_borrador(
            alumno_id=ALUMNO,
            curso=CURSO,
            mision_id=MISION,
            etapa_id=ETAPA,
            campo_id=campo,
            tipo_respuesta="TEXTO",
            contenido=valor,
        )

    print("✓ Cuatro borradores creados")

    # Prueba de rollback: pedimos deliberadamente un campo inexistente.
    try:
        consolidar_etapa(
            alumno_id=ALUMNO,
            mision_id=MISION,
            etapa_id=ETAPA,
            campos_id=CAMPOS + ["campo_inexistente"],
            motivo="PRUEBA_ROLLBACK",
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("La prueba de rollback debía fallar.")

    for campo in CAMPOS:
        respuesta = obtener_respuesta(ALUMNO, MISION, ETAPA, campo)
        historial = obtener_historial(ALUMNO, MISION, ETAPA, campo)

        if respuesta["version_actual"] != 0 or historial:
            raise RuntimeError(
                "Falló la atomicidad: hubo escritura parcial durante el rollback."
            )

    print("✓ Rollback verificado: 0 escrituras parciales")

    resultado = consolidar_etapa(
        alumno_id=ALUMNO,
        mision_id=MISION,
        etapa_id=ETAPA,
        campos_id=CAMPOS,
        origen="ALUMNO",
        motivo="PRUEBA_ATOMICA",
    )

    if resultado["version"] != 1 or resultado["campos_consolidados"] != 4:
        raise RuntimeError("La consolidación atómica no devolvió el resultado esperado.")

    for campo in CAMPOS:
        respuesta = obtener_respuesta(ALUMNO, MISION, ETAPA, campo)
        historial = obtener_historial(ALUMNO, MISION, ETAPA, campo)

        if respuesta["version_actual"] != 1:
            raise RuntimeError(f"{campo} no quedó en V1.")

        if len(historial) != 1 or historial[0]["version"] != 1:
            raise RuntimeError(f"{campo} no conserva exactamente una V1.")

    print("✓ Los cuatro campos quedaron en V1")
    print("✓ Un único COMMIT cerró toda la etapa")
    print("----------------------------------------")
    print("✓ CONSOLIDACIÓN ATÓMICA VERIFICADA")
    print("✓ Ningún alumno REAL fue utilizado")


if __name__ == "__main__":
    main()
