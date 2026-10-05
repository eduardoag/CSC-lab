from sqlalchemy import text

from core.base_datos import obtener_conexion
from core.respuestas import (
    consolidar_respuesta,
    guardar_borrador,
    obtener_historial,
    obtener_respuesta,
)


ALUMNO_DEMO = "CSC-DEMO-001"
CURSO = "3A"
MISION = "M01"
ETAPA = "OBSERVAR"
CAMPO = "tipo_planteamiento"


def verificar_alumno_demo():
    conexion = obtener_conexion()

    consulta = text(
        """
        SELECT alumno_id, tipo_alumno, activo
        FROM alumnos
        WHERE alumno_id = :alumno_id
        LIMIT 1
        """
    )

    with conexion.session as sesion:
        alumno = sesion.execute(
            consulta,
            {"alumno_id": ALUMNO_DEMO},
        ).mappings().first()

    if alumno is None:
        raise RuntimeError("No existe CSC-DEMO-001.")

    if alumno["tipo_alumno"] != "DEMO":
        raise RuntimeError(
            "La prueba fue cancelada: CSC-DEMO-001 no es DEMO."
        )

    if not alumno["activo"]:
        raise RuntimeError(
            "La prueba fue cancelada: el alumno DEMO no está activo."
        )


def limpiar_prueba():
    """
    Elimina únicamente el campo artificial usado por esta prueba.
    ON DELETE CASCADE elimina también sus versiones.
    """
    conexion = obtener_conexion()

    consulta = text(
        """
        DELETE FROM respuestas_mision
        WHERE alumno_id = :alumno_id
          AND mision_id = :mision_id
          AND etapa_id = :etapa_id
          AND campo_id = :campo_id
        """
    )

    with conexion.session as sesion:
        try:
            sesion.execute(
                consulta,
                {
                    "alumno_id": ALUMNO_DEMO,
                    "mision_id": MISION,
                    "etapa_id": ETAPA,
                    "campo_id": CAMPO,
                },
            )
            sesion.commit()
        except Exception:
            sesion.rollback()
            raise


def main():
    print("CSC Lab · Prueba controlada de respuestas")
    print("----------------------------------------")

    verificar_alumno_demo()
    print("✓ Identidad DEMO verificada")

    # Garantiza que podamos repetir la prueba sin acumular basura.
    limpiar_prueba()
    print("✓ Área de prueba limpia")

    guardar_borrador(
        alumno_id=ALUMNO_DEMO,
        curso=CURSO,
        mision_id=MISION,
        etapa_id=ETAPA,
        campo_id=CAMPO,
        tipo_respuesta="OPCION",
        contenido="PROBLEMA",
    )

    respuesta = obtener_respuesta(
        ALUMNO_DEMO,
        MISION,
        ETAPA,
        CAMPO,
    )

    if respuesta is None:
        raise RuntimeError("El borrador no pudo recuperarse.")

    if respuesta["version_actual"] != 0:
        raise RuntimeError(
            "Un borrador nuevo debería tener version_actual = 0."
        )

    print("✓ Borrador guardado")
    print(
        f"  contenido_actual = {respuesta['contenido_actual']}"
    )
    print(
        f"  version_actual = {respuesta['version_actual']}"
    )

    version = consolidar_respuesta(
        alumno_id=ALUMNO_DEMO,
        mision_id=MISION,
        etapa_id=ETAPA,
        campo_id=CAMPO,
        origen="ALUMNO",
        motivo="prueba_controlada",
    )

    if version["version"] != 1:
        raise RuntimeError("La primera versión debería ser V1.")

    print("✓ Respuesta consolidada como V1")

    historial = obtener_historial(
        ALUMNO_DEMO,
        MISION,
        ETAPA,
        CAMPO,
    )

    if len(historial) != 1:
        raise RuntimeError(
            f"Se esperaba 1 versión y se encontraron {len(historial)}."
        )

    if historial[0]["contenido"] != {"valor": "PROBLEMA"}:
        raise RuntimeError(
            "El contenido histórico no coincide con el borrador."
        )

    respuesta_final = obtener_respuesta(
        ALUMNO_DEMO,
        MISION,
        ETAPA,
        CAMPO,
    )

    if respuesta_final["version_actual"] != 1:
        raise RuntimeError(
            "La respuesta actual debería indicar version_actual = 1."
        )

    print("✓ Historial verificado")
    print(
        f"  V1 = {historial[0]['contenido']}"
    )
    print(
        f"  origen = {historial[0]['origen']}"
    )
    print(
        f"  motivo = {historial[0]['motivo']}"
    )

    print("----------------------------------------")
    print("✓ PRUEBA COMPLETADA CORRECTAMENTE")
    print("✓ Ningún alumno REAL fue utilizado")


if __name__ == "__main__":
    main()
