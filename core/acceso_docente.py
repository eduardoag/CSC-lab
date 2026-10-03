import hmac

import streamlit as st


def docente_autenticado():
    return st.session_state.get(
        "docente_autenticado",
        False,
    )


def autenticar_docente(password_ingresado):

    try:
        password_correcto = st.secrets["docente"]["password"]
    except (KeyError, FileNotFoundError):
        return False

    if not password_ingresado:
        return False

    valido = hmac.compare_digest(
        password_ingresado,
        password_correcto,
    )

    if valido:
        st.session_state.docente_autenticado = True

    return valido


def cerrar_sesion_docente():

    st.session_state.docente_autenticado = False
