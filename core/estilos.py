# ============================================================
# CSC LAB
# Carga de estilos CSS
# ============================================================

from pathlib import Path

import streamlit as st


def cargar_css():
    """
    Lee e inyecta la hoja de estilos principal de CSC Lab.
    """

    ruta_proyecto = Path(__file__).resolve().parent.parent
    ruta_css = ruta_proyecto / "assets" / "css" / "responsive.css"

    if not ruta_css.exists():
        st.error(f"No se encontró la hoja de estilos: {ruta_css}")
        return

    css = ruta_css.read_text(encoding="utf-8")

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )
