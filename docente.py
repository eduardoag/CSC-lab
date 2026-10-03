import streamlit as st

from componentes.dashboard_docente import mostrar_dashboard_docente
from core.acceso_docente import (
    autenticar_docente,
    cerrar_sesion_docente,
    docente_autenticado,
)
from core.estilos import cargar_css


st.set_page_config(
    page_title="CSC Lab · Docente",
    page_icon="🧪",
    layout="wide",
)

cargar_css()

st.title("🧪 CSC Lab · Acceso docente")

if not docente_autenticado():
    st.caption("Ingresá con tu clave docente para abrir el Dashboard.")

    with st.form("login_docente_independiente"):
        password_docente = st.text_input(
            "Contraseña docente",
            type="password",
        )
        ingresar = st.form_submit_button(
            "Ingresar",
            use_container_width=True,
        )

    if ingresar:
        if autenticar_docente(password_docente):
            st.rerun()
        else:
            st.error("No se pudo validar el acceso docente.")

    st.stop()

col_info, col_salir = st.columns([3, 1])

with col_info:
    st.success("👨‍🏫 Modo docente activo")

with col_salir:
    if st.button(
        "Cerrar sesión docente",
        use_container_width=True,
        key="cerrar_sesion_docente_independiente",
    ):
        cerrar_sesion_docente()
        st.rerun()

st.divider()
mostrar_dashboard_docente()
