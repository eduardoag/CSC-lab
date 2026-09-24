# ============================================================
# CSC LAB
# Cultura del Constructor
# ============================================================

import streamlit as st


REGLAS_CONSTRUCTOR = [
    "Primero el problema; después la tecnología.",

    "Toda decisión importante debe poder "
    "explicarse y defenderse.",

    "Equivocarse está permitido. "
    "No aprender del error, no.",

    "Los datos son mejores que las opiniones: "
    "investigar, medir y contrastar.",

    "La IA puede ayudarnos a pensar; "
    "no puede reemplazar nuestro pensamiento.",

    "Nadie se esconde detrás del equipo: "
    "todos deben comprender la empresa completa.",

    "Respeto, responsabilidad y ética son parte "
    "de la tecnología, no un agregado.",
]


def mostrar_bienvenida_constructor():
    """
    Presenta la entrada al programa y
    las siete reglas del Constructor.
    """

    st.markdown("## 🏗️ Bienvenido, Constructor")

    st.write(
        "Durante este trimestre no vas simplemente "
        "a estudiar una empresa."
    )

    st.markdown(
        "### Vas a diseñar una."
    )

    st.info(
        "Tecnología es conocimiento puesto en acción "
        "para resolver problemas."
    )

    st.markdown("### 📜 Las 7 Reglas del Constructor")

    for numero, regla in enumerate(
        REGLAS_CONSTRUCTOR,
        start=1,
    ):
        st.markdown(
            f"**{numero}.** {regla}"
        )

    st.divider()

    st.write(
        "Estas reglas nos acompañarán durante "
        "todas las misiones."
    )
