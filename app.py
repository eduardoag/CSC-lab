# ============================================================
# CSC LAB
# Aplicación principal
# ============================================================

import streamlit as st

from componentes.encabezado import mostrar_encabezado
from config.cursos import CURSOS
from core.acceso import (
    obtener_cursos_habilitados,
    obtener_fecha_hora_actual,
)
from core.estilos import cargar_css


# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================

st.set_page_config(
    page_title="CSC Lab",
    page_icon="🧪",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ============================================================
# ESTILOS Y ENCABEZADO
# ============================================================

cargar_css()
mostrar_encabezado()


# ============================================================
# ESTADO ACTUAL DEL LABORATORIO
# ============================================================

momento_actual = obtener_fecha_hora_actual()
cursos_habilitados = obtener_cursos_habilitados(momento_actual)

dias = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}

nombre_dia = dias[momento_actual.weekday()]
hora_actual = momento_actual.strftime("%H:%M")


# ============================================================
# LABORATORIO ABIERTO / CERRADO
# ============================================================

if cursos_habilitados:
    curso_id = cursos_habilitados[0]
    curso = CURSOS[curso_id]

    html_abierto = f"""<div class="csc-card csc-open">
<div class="csc-card-title">🟢 Laboratorio abierto</div>
<div class="csc-message">
Ahora estamos trabajando con:<br><br>
<strong>{curso["nombre"]} · {curso["materia"]}</strong>
</div>
</div>"""

    st.markdown(html_abierto, unsafe_allow_html=True)

    st.success(
        "¡Bienvenidos! Ya pueden ingresar a nuestro espacio de trabajo."
    )

    st.button(
        "Ingresar a CSC Lab →",
        use_container_width=True,
    )

else:
    html_cerrado = """<div class="csc-card csc-closed">
<div class="csc-card-title">🔒 Laboratorio cerrado</div>
<div class="csc-message">
Las misiones de CSC Lab están disponibles solamente durante nuestras clases.
<br><br>
Nos volvemos a encontrar en el aula.
</div>
</div>"""

    st.markdown(html_cerrado, unsafe_allow_html=True)

    st.info(
        "No hay actividades para hacer en casa. "
        "Ese tiempo es para disfrutar de la familia, "
        "los amigos y todo lo que también nos enseña la vida. 🌱"
    )


# ============================================================
# INFORMACIÓN DE ESTADO
# ============================================================

st.divider()

html_estado = f"""<div class="csc-small">
🕐 {nombre_dia} · {hora_actual} hs<br>
Zona horaria: Tucumán, Argentina
</div>"""

st.markdown(html_estado, unsafe_allow_html=True)


# ============================================================
# PIE
# ============================================================

st.divider()

st.caption(
    "CSC Lab · Aprendemos en clase. "
    "En casa, disfrutamos de la familia y los amigos."
)
