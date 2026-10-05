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
    Elimina únicamente el campo artificial utilizado por esta prueba.
    Las versiones asociadas se eliminan mediante ON DELETE CASCADE.
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
    print("CSC Lab · Prueba de evolución V1 → V2")
    print("-------------------------------------")

    verificar_alumno_demo()
    print("✓ Identidad DEMO verificada")

    limpiar_prueba()
    print("✓ Área de prueba limpia")

    # --------------------------------------------------------
    # PRIMER PENSAMIENTO
    # --------------------------------------------------------
    guardar_borrador(
        alumno_id=ALUMNO_DEMO,
        curso=CURSO,
        mision_id=MISION,
        etapa_id=ETAPA,
        campo_id=CAMPO,
        tipo_respuesta="OPCION",
        contenido="PROBLEMA",
    )

    consolidar_respuesta(
        alumno_id=ALUMNO_DEMO,
        mision_id=MISION,
        etapa_id=ETAPA,
        campo_id=CAMPO,
        origen="ALUMNO",
        motivo="primera_consolidacion",
    )

    historial_v1 = obtener_historial(
        ALUMNO_DEMO,
        MISION,
        ETAPA,
        CAMPO,
    )

    if len(historial_v1) != 1:
        raise RuntimeError("Después de V1 debería existir 1 versión.")

    if historial_v1[0]["version"] != 1:
        raise RuntimeError("La primera versión debería ser V1.")

    if historial_v1[0]["contenido"] != {"valor": "PROBLEMA"}:
        raise RuntimeError("El contenido de V1 no coincide.")

    print("✓ V1 consolidada: PROBLEMA")

    # --------------------------------------------------------
    # EL ALUMNO MODIFICA SU BORRADOR
    # --------------------------------------------------------
    guardar_borrador(
        alumno_id=ALUMNO_DEMO,
        curso=CURSO,
        mision_id=MISION,
        etapa_id=ETAPA,
        campo_id=CAMPO,
        tipo_respuesta="OPCION",
        contenido="SOLUCION_DISFRAZADA",
    )

    respuesta_modificada = obtener_respuesta(
        ALUMNO_DEMO,
        MISION,
        ETAPA,
        CAMPO,
    )

    if respuesta_modificada["contenido_actual"] != {
        "valor": "SOLUCION_DISFRAZADA"
    }:
        raise RuntimeError("El nuevo borrador no se guardó correctamente.")

    # Guardar un borrador NO debe incrementar la versión.
    if respuesta_modificada["version_actual"] != 1:
        raise RuntimeError(
            "Modificar el borrador no debería crear una versión nueva."
        )

    historial_antes_v2 = obtener_historial(
        ALUMNO_DEMO,
        MISION,
        ETAPA,
        CAMPO,
    )

    if len(historial_antes_v2) != 1:
        raise RuntimeError(
            "Modificar el borrador alteró indebidamente el historial."
        )

    if historial_antes_v2[0]["contenido"] != {"valor": "PROBLEMA"}:
        raise RuntimeError("V1 fue sobrescrita. La prueba se cancela.")

    print("✓ Borrador modificado sin alterar V1")
    print("  actual = SOLUCION_DISFRAZADA")
    print("  historial todavía contiene solamente V1")

    # --------------------------------------------------------
    # SEGUNDA CONSOLIDACIÓN
    # --------------------------------------------------------
    version_2 = consolidar_respuesta(
        alumno_id=ALUMNO_DEMO,
        mision_id=MISION,
        etapa_id=ETAPA,
        campo_id=CAMPO,
        origen="ALUMNO",
        motivo="revision_del_alumno",
    )

    if version_2["version"] != 2:
        raise RuntimeError("La segunda consolidación debería crear V2.")

    historial_final = obtener_historial(
        ALUMNO_DEMO,
        MISION,
        ETAPA,
        CAMPO,
    )

    if len(historial_final) != 2:
        raise RuntimeError(
            f"Se esperaban 2 versiones y existen {len(historial_final)}."
        )

    if historial_final[0]["contenido"] != {"valor": "PROBLEMA"}:
        raise RuntimeError("V1 cambió después de crear V2.")

    if historial_final[1]["contenido"] != {
        "valor": "SOLUCION_DISFRAZADA"
    }:
        raise RuntimeError("El contenido de V2 no coincide.")

    respuesta_final = obtener_respuesta(
        ALUMNO_DEMO,
        MISION,
        ETAPA,
        CAMPO,
    )

    if respuesta_final["version_actual"] != 2:
        raise RuntimeError("version_actual debería ser 2.")

    print("✓ V2 consolidada: SOLUCION_DISFRAZADA")
    print("✓ V1 permanece intacta")

    print()
    print("Historial pedagógico:")
    for version in historial_final:
        print(
            f"  V{version['version']} = "
            f"{version['contenido']} "
            f"({version['motivo']})"
        )

    print("-------------------------------------")
    print("✓ EVOLUCIÓN V1 → V2 VERIFICADA")
    print("✓ Ninguna versión histórica fue sobrescrita")
    print("✓ Ningún alumno REAL fue utilizado")


if __name__ == "__main__":
    main()
