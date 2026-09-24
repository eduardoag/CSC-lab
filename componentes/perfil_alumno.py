# ============================================================
# CSC LAB
# Componente visual del perfil del alumno
# ============================================================

import streamlit as st


def mostrar_perfil_alumno(alumno):
    """
    Muestra la identidad del alumno que tiene
    una sesión activa en CSC Lab.
    """

    nombre = alumno["nombre"]
    apellido = alumno["apellido"]
    curso = alumno["curso"]
    alumno_id = alumno["alumno_id"]

    html = f"""<div class="csc-card">
<div class="csc-card-title">👤 Mi espacio</div>
<div class="csc-message">
<strong>{nombre} {apellido}</strong><br>
Curso: {curso}<br>
<span class="csc-small">{alumno_id}</span>
</div>
</div>"""

    st.markdown(
        html,
        unsafe_allow_html=True,
    )
