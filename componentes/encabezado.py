# ============================================================
# CSC LAB
# Encabezado principal
# ============================================================

import streamlit as st


def mostrar_encabezado():
    """
    Muestra el encabezado principal de CSC Lab.
    """

    html = """<div class="csc-header">
<div class="csc-logo">🧪</div>
<div class="csc-title">CSC LAB</div>
<div class="csc-subtitle">
Tecnología · TIC<br>
Colegio Sagrado Corazón
</div>
</div>"""

    st.markdown(
        html,
        unsafe_allow_html=True,
    )
