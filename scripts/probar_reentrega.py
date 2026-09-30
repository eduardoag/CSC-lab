from core.progreso import obtener_progreso
from core.reentregas import reenviar_mision


ALUMNO_ID = "CSC-3A-001"
MISION_ID = "TEST-M01"


def main():

    print()
    print("=" * 60)
    print("CSC LAB · PRUEBA DE REENTREGA")
    print("=" * 60)

    anterior = obtener_progreso(
        ALUMNO_ID,
        MISION_ID,
    )

    if anterior is None:
        raise RuntimeError(
            "No existe la misión de prueba."
        )

    print()
    print("Estado anterior:", anterior["estado"])
    print(
        "Devolución:",
        anterior["devolucion_docente"],
    )

    if anterior["estado"] != "REQUIERE_AJUSTES":
        raise RuntimeError(
            "La prueba requiere el estado REQUIERE_AJUSTES."
        )

    reenviar_mision(
        alumno_id=ALUMNO_ID,
        mision_id=MISION_ID,
        descripcion_cambios=(
            "Prueba técnica: revisé la definición "
            "del problema y agregué evidencia."
        ),
    )

    actual = obtener_progreso(
        ALUMNO_ID,
        MISION_ID,
    )

    print()
    print("Estado nuevo:", actual["estado"])
    print("Fecha de reentrega:", actual["fecha_envio"])

    assert actual["estado"] == "PENDIENTE_REVISION"

    print()
    print("✅ REENTREGA REGISTRADA CORRECTAMENTE")


if __name__ == "__main__":
    main()
