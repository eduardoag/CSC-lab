# ============================================================
# CSC LAB
# Tarjeta del equipo del alumno
# ============================================================

import streamlit as st

from core.autenticacion import obtener_alumno_por_id
from core.equipos import (
    obtener_equipo_alumno,
    obtener_integrantes_equipo,
)


def mostrar_equipo_alumno(alumno):

    equipo = obtener_equipo_alumno(
        alumno["alumno_id"]
    )

    st.markdown("### 🏢 Mi equipo")

    # --------------------------------------------------------
    # TODAVÍA NO TIENE EQUIPO
    # --------------------------------------------------------

    if equipo is None:

        st.info(
            "⏳ Tu equipo todavía está en formación.\n\n"
            "Podés ingresar normalmente a CSC Lab. "
            "Cuando quede conformado, aparecerá aquí."
        )

        return

    # --------------------------------------------------------
    # EQUIPO ENCONTRADO
    # --------------------------------------------------------

    st.markdown(
        f"#### {equipo['nombre_equipo']}"
    )

    if equipo["nombre_empresa"]:

        st.write(
            f"**Empresa:** "
            f"{equipo['nombre_empresa']}"
        )

    integrantes_ids = obtener_integrantes_equipo(
        equipo["equipo_id"]
    )

    st.write("**Integrantes:**")

    for alumno_id in integrantes_ids:

        integrante = obtener_alumno_por_id(
            alumno_id
        )

        if integrante is None:
            continue

        nombre_completo = (
            f"{integrante['nombre']} "
            f"{integrante['apellido']}"
        )

        if alumno_id == alumno["alumno_id"]:

            st.markdown(
                f"- **{nombre_completo} · vos**"
            )

        else:

            st.markdown(
                f"- {nombre_completo}"
            )

    st.caption(
        f"{len(integrantes_ids)} integrantes"
    )
