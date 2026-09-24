# ============================================================
# CSC LAB
# Aplicación principal
# ============================================================

import streamlit as st

from componentes.encabezado import mostrar_encabezado
from componentes.perfil_alumno import mostrar_perfil_alumno
from config.cursos import CURSOS
from core.acceso import (
    obtener_cursos_habilitados,
    obtener_fecha_hora_actual,
)
from core.autenticacion import validar_alumno
from core.estilos import cargar_css
from core.sesiones import (
    cerrar_sesion,
    crear_sesion,
    expirar_sesiones_abandonadas,
    inicializar_base_datos,
    registrar_actividad,
)

from componentes.cultura_constructor import (
    mostrar_bienvenida_constructor,
)

from core.cultura import (
    aceptar_reglas,
    alumno_acepto_reglas,
    inicializar_cultura,
)

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
# INICIALIZACIÓN
# ============================================================

inicializar_base_datos()
inicializar_cultura()
expirar_sesiones_abandonadas()

cargar_css()
mostrar_encabezado()


# ============================================================
# ESTADO DE SESIÓN DE STREAMLIT
# ============================================================

if "alumno" not in st.session_state:
    st.session_state.alumno = None

if "sesion_id" not in st.session_state:
    st.session_state.sesion_id = None


# ============================================================
# ESTADO ACTUAL DEL LABORATORIO
# ============================================================

momento_actual = obtener_fecha_hora_actual()

cursos_habilitados = obtener_cursos_habilitados(
    momento_actual
)

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
# LABORATORIO ABIERTO
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

    st.markdown(
        html_abierto,
        unsafe_allow_html=True,
    )


    # ========================================================
    # ALUMNO SIN IDENTIFICAR
    # ========================================================

    if st.session_state.alumno is None:

        st.subheader(
            "👤 Identificate para comenzar"
        )

        st.write(
            "Ingresá tu número de lista y tu nombre."
        )

        with st.form(
            "formulario_identificacion"
        ):

            numero_lista = st.number_input(
                "Número de lista",
                min_value=1,
                max_value=60,
                step=1,
            )

            nombre_ingresado = st.text_input(
                "Tu nombre",
                placeholder="Ejemplo: Agustín José",
            )

            ingresar = st.form_submit_button(
                "Ingresar a CSC Lab →",
                use_container_width=True,
            )

        if ingresar:

            alumno = validar_alumno(
                curso_id,
                numero_lista,
                nombre_ingresado,
            )

            if alumno is not None:

                sesion_id = crear_sesion(
                    alumno
                )

                st.session_state.alumno = alumno
                st.session_state.sesion_id = sesion_id

                st.rerun()

            else:

                st.error(
                    "No pudimos verificar esos datos. "
                    "Revisá tu número de lista y tu nombre."
                )


    # ========================================================
    # ALUMNO IDENTIFICADO
    # ========================================================

    else:

        alumno = st.session_state.alumno
        sesion_id = st.session_state.sesion_id

        # ----------------------------------------------------
        # VERIFICAR QUE SIGUE EN SU CURSO
        # ----------------------------------------------------

        if alumno["curso"] != curso_id:

            if sesion_id is not None:
                cerrar_sesion(
                    sesion_id,
                    motivo="CAMBIO_CURSO",
                )

            st.session_state.alumno = None
            st.session_state.sesion_id = None

            st.rerun()


        # ----------------------------------------------------
        # SESIÓN VÁLIDA
        # ----------------------------------------------------

        else:

            if sesion_id is not None:
                registrar_actividad(
                    sesion_id
                )

            st.success(
                f"¡Hola, {alumno['nombre']}! "
                "Tu sesión está activa."
            )

            mostrar_perfil_alumno(
                alumno
            )

            # ========================================================
            # CULTURA DEL CONSTRUCTOR
            # Sólo corresponde a 3.º año
            # ========================================================

            if alumno["curso"] in ("3A", "3B"):

                acepto_reglas = alumno_acepto_reglas(
                    alumno["alumno_id"]
                )

                if not acepto_reglas:

                    mostrar_bienvenida_constructor()

                    if st.button(
                        "✓ Acepto el desafío",
                        use_container_width=True,
                        type="primary",
                    ):

                        aceptar_reglas(
                            alumno["alumno_id"]
                        )

                        if sesion_id is not None:
                            registrar_actividad(
                                sesion_id
                            )

                        st.rerun()

                else:

                    st.success(
                        "🏗️ Sos parte del programa "
                        "Constructores."
                    )

                    st.markdown(
                        "### 🎯 Misión 01 · ENCONTRAR"
                    )

                    st.write(
                        "Encontrar un problema real "
                        "que merezca ser resuelto."
                    )

                    st.info(
                        "La primera misión está a punto "
                        "de comenzar."
                    )

            else:

                st.info(
                    "Tu espacio de TIC estará disponible aquí."
                )

            if st.button(
                "Cerrar mi sesión",
                use_container_width=True,
            ):

                if sesion_id is not None:
                    cerrar_sesion(
                        sesion_id,
                        motivo="CIERRE_ALUMNO",
                    )

                st.session_state.alumno = None
                st.session_state.sesion_id = None

                st.rerun()


# ============================================================
# LABORATORIO CERRADO
# ============================================================

else:

    # --------------------------------------------------------
    # CERRAR UNA SESIÓN QUE HAYA QUEDADO ABIERTA
    # --------------------------------------------------------

    if st.session_state.sesion_id is not None:

        cerrar_sesion(
            st.session_state.sesion_id,
            motivo="FIN_HORARIO",
        )

    st.session_state.alumno = None
    st.session_state.sesion_id = None


    # --------------------------------------------------------
    # PANTALLA DE LABORATORIO CERRADO
    # --------------------------------------------------------

    html_cerrado = """<div class="csc-card csc-closed">
<div class="csc-card-title">🔒 Laboratorio cerrado</div>
<div class="csc-message">
Las misiones de CSC Lab están disponibles solamente durante nuestras clases.
<br><br>
Nos volvemos a encontrar en el aula.
</div>
</div>"""

    st.markdown(
        html_cerrado,
        unsafe_allow_html=True,
    )

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

st.markdown(
    html_estado,
    unsafe_allow_html=True,
)


# ============================================================
# PIE
# ============================================================

st.divider()

st.caption(
    "CSC Lab · Aprendemos en clase. "
    "En casa, disfrutamos de la familia y los amigos."
)
