import streamlit as st


def obtener_conexion():
    """
    Devuelve una conexión SQL de CSC Lab.

    La configuración se obtiene de:
    - .streamlit/secrets.toml en desarrollo local.
    - Streamlit Secrets en producción.
    """
    return st.connection(
        "postgresql",
        type="sql",
    )
