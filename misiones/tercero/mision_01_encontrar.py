import streamlit as st

from core.respuestas import (
    consolidar_etapa,
    guardar_borrador,
    obtener_respuesta,
)

MISION_ID = "M01"
ETAPA_ID = "OBSERVAR"

CASOS = {
    "caso_a": {
        "titulo": "Caso A",
        "texto": "Los alumnos olvidan frecuentemente las fechas de entrega de sus trabajos.",
    },
    "caso_b": {
        "titulo": "Caso B",
        "texto": "Necesitamos una aplicación que envíe recordatorios de las tareas.",
    },
    "caso_c": {
        "titulo": "Caso C",
        "texto": "Muchas familias tiran alimentos porque no recuerdan qué tienen guardado.",
    },
}
OPCIONES = ["PROBLEMA", "SOLUCION_DISFRAZADA"]


def _valor_guardado(alumno_id, campo_id, defecto=None):
    respuesta = obtener_respuesta(alumno_id, MISION_ID, ETAPA_ID, campo_id)
    if not respuesta:
        return defecto
    contenido = respuesta.get("contenido_actual") or {}
    return contenido.get("valor", defecto) if isinstance(contenido, dict) else defecto


def _indice_opcion(valor):
    return OPCIONES.index(valor) if valor in OPCIONES else None


def _campos_observar():
    return ["caso_a", "caso_b", "caso_c", "diferencia_problema_solucion"]


def _todos_completos(alumno_id):
    for campo_id in _campos_observar():
        respuesta = obtener_respuesta(alumno_id, MISION_ID, ETAPA_ID, campo_id)
        if not respuesta:
            return False
        valor = (respuesta.get("contenido_actual") or {}).get("valor")
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            return False
    return True


def _version_comun(alumno_id):
    versiones = []
    for campo_id in _campos_observar():
        respuesta = obtener_respuesta(alumno_id, MISION_ID, ETAPA_ID, campo_id)
        if not respuesta:
            return 0
        versiones.append(int(respuesta["version_actual"]))
    return versiones[0] if len(set(versiones)) == 1 else None


def _consolidar_observar(alumno_id):
    if not _todos_completos(alumno_id):
        raise ValueError(
            "Completá y guardá toda la observación antes de consolidarla."
        )

    version_actual = _version_comun(alumno_id)

    if version_actual is None:
        raise ValueError(
            "Las respuestas de OBSERVAR no están alineadas "
            "en la misma versión."
        )

    resultado = consolidar_etapa(
        alumno_id=alumno_id,
        mision_id=MISION_ID,
        etapa_id=ETAPA_ID,
        campos_id=_campos_observar(),
        origen="ALUMNO",
        motivo="CIERRE_OBSERVAR",
    )

    return resultado["version"]


def _mostrar_reflexion_guiada():
    st.markdown("### 🔎 Antes de cerrar tu observación")
    st.write("Volvé a mirar tus respuestas y hacete estas tres preguntas:")
    st.markdown(
        """
- **¿La frase cuenta algo que realmente ocurre o ya dice qué construir?**
- **¿Podría existir el problema aunque esa solución no existiera?**
- **¿Estoy describiendo una necesidad o enamorándome demasiado pronto de una idea?**
"""
    )
    st.info(
        "💡 Pista de constructor: una solución puede ser excelente, "
        "pero primero necesitamos comprender el problema que intenta resolver."
    )


def mostrar_observar(alumno, *, modo_demo=False, solo_lectura=False):
    alumno_id = alumno["alumno_id"]
    curso = alumno["curso"]

    st.markdown("## 🎯 Misión 01 · ENCONTRAR")
    st.write("Encontrar un problema real que merezca ser resuelto.")
    st.markdown("### 👀 Etapa 1 · OBSERVAR")
    st.info(
        "Los buenos proyectos no comienzan con una idea. "
        "Comienzan aprendiendo a observar."
    )

    if solo_lectura:
        st.warning("👁️ Vista de inspección docente · las respuestas no pueden modificarse.")
    elif modo_demo:
        st.caption("🧪 Laboratorio DEMO · estas respuestas pertenecen únicamente al alumno técnico.")

    st.markdown(
        """
Leé cada situación y preguntate:

**¿Describe algo que le ocurre a una persona o ya propone qué construir?**
"""
    )

    valores = {campo: _valor_guardado(alumno_id, campo) for campo in CASOS}
    diferencia_guardada = _valor_guardado(
        alumno_id, "diferencia_problema_solucion", ""
    )

    with st.form(key=f"m01_observar_{alumno_id}"):
        selecciones = {}

        for campo_id, caso in CASOS.items():
            st.markdown(f"#### {caso['titulo']}")
            st.write(f"“{caso['texto']}”")
            selecciones[campo_id] = st.radio(
                "¿Qué representa esta frase?",
                options=OPCIONES,
                index=_indice_opcion(valores[campo_id]),
                format_func=lambda opcion: (
                    "🧩 Es un problema"
                    if opcion == "PROBLEMA"
                    else "🛠️ Es una solución disfrazada de problema"
                ),
                key=f"{alumno_id}_{campo_id}",
                disabled=solo_lectura,
            )
            st.divider()

        diferencia = st.text_area(
            "¿Qué diferencia encontraste entre una frase que describe "
            "un problema y una que ya propone una solución?",
            value=diferencia_guardada or "",
            placeholder="Explicalo con tus palabras. No buscamos una definición de memoria.",
            height=130,
            disabled=solo_lectura,
            key=f"{alumno_id}_diferencia_problema_solucion",
        )

        guardar = st.form_submit_button(
            "💾 Guardar mi observación",
            type="primary",
            use_container_width=True,
            disabled=solo_lectura,
        )

    if guardar:
        if any(valor is None for valor in selecciones.values()):
            st.error("Clasificá los tres casos antes de guardar.")
            return
        if not diferencia.strip():
            st.error("Contanos con tus palabras qué diferencia encontraste.")
            return

        for campo_id, valor in selecciones.items():
            guardar_borrador(
                alumno_id=alumno_id,
                curso=curso,
                mision_id=MISION_ID,
                etapa_id=ETAPA_ID,
                campo_id=campo_id,
                tipo_respuesta="OPCION",
                contenido=valor,
            )

        guardar_borrador(
            alumno_id=alumno_id,
            curso=curso,
            mision_id=MISION_ID,
            etapa_id=ETAPA_ID,
            campo_id="diferencia_problema_solucion",
            tipo_respuesta="TEXTO_LARGO",
            contenido=diferencia.strip(),
        )

        st.success("✓ Tu observación quedó guardada como borrador.")
        st.caption(
            "Todavía no la convertimos en una versión histórica. "
            "Podés volver a leerla y mejorarla."
        )
        st.rerun()

    if _todos_completos(alumno_id):
        st.divider()
        _mostrar_reflexion_guiada()

        version_actual = _version_comun(alumno_id)

        if version_actual is None:
            st.error(
                "Las respuestas guardadas no tienen una versión común. "
                "No vamos a consolidar hasta revisar esta inconsistencia."
            )
            return

        if version_actual == 0:
            st.write(
                "Si después de releer querés cambiar algo, hacelo arriba y volvé a guardar."
            )
            st.warning(
                "Cuando confirmes, CSC Lab conservará esta observación como tu primera "
                "versión histórica. No se perderá aunque más adelante cambies de opinión."
            )

            confirmar = st.checkbox(
                "Releí mis respuestas y quiero conservarlas como mi V1.",
                key=f"{alumno_id}_confirmar_observar_v1",
                disabled=solo_lectura,
            )

            if st.button(
                "✓ Esta es mi respuesta",
                type="primary",
                use_container_width=True,
                key=f"{alumno_id}_consolidar_observar_v1",
                disabled=solo_lectura or not confirmar,
            ):
                try:
                    nueva_version = _consolidar_observar(alumno_id)
                except (ValueError, RuntimeError) as error:
                    st.error(str(error))
                else:
                    st.success(f"✓ OBSERVAR quedó conservada como V{nueva_version}.")
                    st.rerun()
        else:
            st.success(f"✓ OBSERVAR ya tiene una versión histórica V{version_actual}.")
            st.caption(
                "Tu pensamiento quedó guardado. Si más adelante lo revisás, "
                "esta versión seguirá existiendo."
            )
