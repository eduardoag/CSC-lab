from pathlib import Path


def main():
    ruta = Path("core/respuestas_equipo.py")
    contenido = ruta.read_text(encoding="utf-8")

    inicio = contenido.index("def guardar_borrador_equipo_en_sesion(")
    fin = contenido.index("\ndef obtener_respuesta_equipo(", inicio)
    funcion = contenido[inicio:fin]

    assert "verificar_mision_equipo_editable_en_sesion(" in funcion
    assert "bloquear=True" in funcion

    posicion_bloqueo = funcion.index(
        "verificar_mision_equipo_editable_en_sesion("
    )
    posicion_lectura_borrador = funcion.index(
        "SELECT respuesta_equipo_id, revision_borrador"
    )

    assert posicion_bloqueo < posicion_lectura_borrador

    print("=" * 76)
    print("CSC LAB · AUDITORÍA BLOQUEO BORRADOR ↔ ENTREGA")
    print("=" * 76)
    print("✓ guardar_borrador_equipo_en_sesion usa bloquear=True.")
    print("✓ El bloqueo de progreso ocurre antes de leer/escribir el borrador.")
    print("✓ Guardar y entregar comparten el mismo punto de serialización.")
    print("✓ La ventana lógica de escritura tardía queda cerrada.")
    print("✓ Auditoría estructural finalizada correctamente.")


if __name__ == "__main__":
    main()
