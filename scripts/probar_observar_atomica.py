from core.respuestas import (
    guardar_borrador,
    obtener_historial,
    obtener_respuesta,
)
from misiones.tercero.mision_01_encontrar import (
    ETAPA_ID,
    MISION_ID,
    _campos_observar,
    _consolidar_observar,
)

ALUMNO = "CSC-DEMO-001"
CURSO = "3A"

VALORES_NUEVOS = {
    "caso_a": "PROBLEMA",
    "caso_b": "SOLUCION_DISFRAZADA",
    "caso_c": "PROBLEMA",
    "diferencia_problema_solucion": (
        "Un problema describe una necesidad o dificultad real; "
        "una solución ya propone qué construir para responder a ella."
    ),
}


def main():
    print("CSC Lab · Prueba final OBSERVAR atómica")
    print("--------------------------------------")

    versiones_antes = {}

    for campo in _campos_observar():
        respuesta = obtener_respuesta(
            ALUMNO,
            MISION_ID,
            ETAPA_ID,
            campo,
        )

        if respuesta is None:
            raise RuntimeError(
                f"Falta el campo {campo}. "
                "Primero completá OBSERVAR con el alumno DEMO."
            )

        versiones_antes[campo] = int(respuesta["version_actual"])

    if len(set(versiones_antes.values())) != 1:
        raise RuntimeError(
            "OBSERVAR ya está desalineada antes de la prueba."
        )

    version_inicial = next(iter(versiones_antes.values()))

    print(f"✓ OBSERVAR alineada inicialmente en V{version_inicial}")

    for campo, valor in VALORES_NUEVOS.items():
        guardar_borrador(
            alumno_id=ALUMNO,
            curso=CURSO,
            mision_id=MISION_ID,
            etapa_id=ETAPA_ID,
            campo_id=campo,
            tipo_respuesta=(
                "TEXTO_LARGO"
                if campo == "diferencia_problema_solucion"
                else "OPCION"
            ),
            contenido=valor,
        )

    print("✓ Nuevos borradores guardados")
    print(
        f"✓ version_actual continúa en V{version_inicial} "
        "hasta consolidar"
    )

    nueva_version = _consolidar_observar(ALUMNO)

    if nueva_version != version_inicial + 1:
        raise RuntimeError(
            "La nueva versión no es consecutiva."
        )

    for campo in _campos_observar():
        respuesta = obtener_respuesta(
            ALUMNO,
            MISION_ID,
            ETAPA_ID,
            campo,
        )
        historial = obtener_historial(
            ALUMNO,
            MISION_ID,
            ETAPA_ID,
            campo,
        )

        if int(respuesta["version_actual"]) != nueva_version:
            raise RuntimeError(
                f"{campo} no quedó en V{nueva_version}."
            )

        if not historial:
            raise RuntimeError(
                f"{campo} no tiene historial."
            )

        if int(historial[-1]["version"]) != nueva_version:
            raise RuntimeError(
                f"El historial de {campo} no termina en "
                f"V{nueva_version}."
            )

    print(
        f"✓ Los cuatro campos fueron consolidados juntos "
        f"como V{nueva_version}"
    )
    print("✓ Historial anterior preservado")
    print("--------------------------------------")
    print("✓ OBSERVAR ATÓMICA VERIFICADA")
    print("✓ Ningún alumno REAL fue utilizado")


if __name__ == "__main__":
    main()
