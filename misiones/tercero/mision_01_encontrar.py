"""
CSC Lab · 3.º año · Misión 01 — ENCONTRAR

Interfaz de alumno conectada al motor universal de misiones por equipo.

Compatibilidad:
    app.py sigue importando y llamando mostrar_observar(...).
    El nombre se conserva para no tocar todavía la aplicación principal,
    aunque esta función ahora muestra la misión completa.

Principios:
    - PREPARARSE: actividad individual complementaria.
    - OBSERVAR → FORMULAR: construcción compartida del equipo.
    - FICHA: consolidación automática; no duplica preguntas.
    - Reflexión final: individual y no bloquea la entrega.
    - PENDIENTE_REVISION/APROBADA: borrador grupal en solo lectura.
"""

import streamlit as st

from core.entregas_equipo import EntregaEquipoError, entregar_mision_equipo
from core.equipos import obtener_equipo_alumno
from core.progreso_equipo import (
    EstadoProgresoEquipoError,
    actualizar_etapa_equipo,
    iniciar_mision_equipo,
    obtener_progreso_equipo,
)
from core.respuestas import guardar_borrador, obtener_respuesta
from core.respuestas_equipo import (
    ConflictoBorradorEquipoError,
    guardar_borrador_equipo,
    listar_respuestas_etapa_equipo,
    obtener_respuesta_equipo,
)
from misiones.tercero.mision_01_config import (
    CAMPOS_REQUERIDOS_ENTREGA,
    CASOS_PREPARARSE,
    ENTREGABLE,
    ENTREGABLE_ITEMS,
    INTRODUCCION,
    METODOS_EVIDENCIA,
    MISION_ID,
    OBJETIVO,
    OPCIONES_CONSECUENCIAS,
    OPCIONES_FRECUENCIA,
    OPCIONES_PROBLEMA_SOLUCION,
    ORDEN_ETAPAS,
    PROFESSOR_CHECKPOINT,
    REFLEXION_INDIVIDUAL,
    TITULO,
    campos_de_etapa,
    validar_entrega,
)


# ============================================================
# CONSTANTES DE INTERFAZ
# ============================================================

ETIQUETAS_ETAPA = {
    "PREPARARSE": "🧠 Prepararse",
    "OBSERVAR": "👀 Observar",
    "COMPRENDER": "🧩 Comprender",
    "INVESTIGAR": "🔎 Investigar",
    "EVIDENCIAR": "🧾 Evidenciar",
    "FORMULAR": "✍️ Formular",
    "FICHA": "📋 Ficha",
}

DESCRIPCIONES_ETAPA = {
    "PREPARARSE": (
        "Antes de investigar su propio problema, entrená la mirada: "
        "aprendé a distinguir un problema de una solución."
    ),
    "OBSERVAR": (
        "Miren la realidad antes de pensar qué construir. Describan "
        "qué ocurre, dónde ocurre y cuándo ocurre."
    ),
    "COMPRENDER": (
        "Identifiquen quién vive el problema y qué saben —o todavía "
        "no saben— sobre su frecuencia."
    ),
    "INVESTIGAR": (
        "Averigüen cómo se resuelve hoy y qué consecuencias produce."
    ),
    "EVIDENCIAR": (
        "Un problema no se inventa: se demuestra. Registren al menos "
        "tres evidencias u observaciones."
    ),
    "FORMULAR": (
        "Con todo lo investigado, expresen el problema con claridad "
        "y formulen una primera oportunidad, todavía sin diseñar la solución."
    ),
    "FICHA": (
        "Revisen el trabajo completo del equipo antes de enviarlo "
        "al Professor Checkpoint."
    ),
}

ESTADOS_BLOQUEADOS = {"PENDIENTE_REVISION", "APROBADA"}

ETIQUETAS_ESTADO = {
    "EN_PROGRESO": "🟡 En progreso",
    "PENDIENTE_REVISION": "🟠 Esperando revisión del profesor",
    "REQUIERE_AJUSTES": "🔵 Requiere ajustes",
    "APROBADA": "🟢 Aprobada",
}


# ============================================================
# HELPERS GENERALES
# ============================================================

def _valor_contenido(contenido, defecto=None):
    if contenido is None:
        return defecto
    if isinstance(contenido, dict):
        if "valor" in contenido:
            return contenido.get("valor", defecto)
        if "valores" in contenido:
            return contenido.get("valores", defecto)
    return contenido


def _valor_individual(alumno_id, etapa_id, campo_id, defecto=None):
    respuesta = obtener_respuesta(
        alumno_id,
        MISION_ID,
        etapa_id,
        campo_id,
    )
    if not respuesta:
        return defecto
    return _valor_contenido(respuesta.get("contenido_actual"), defecto)


def _respuesta_equipo(alumno_id, equipo_id, etapa_id, campo_id):
    return obtener_respuesta_equipo(
        alumno_id,
        equipo_id,
        MISION_ID,
        etapa_id,
        campo_id,
    )


def _valor_equipo(alumno_id, equipo_id, etapa_id, campo_id, defecto=None):
    respuesta = _respuesta_equipo(
        alumno_id,
        equipo_id,
        etapa_id,
        campo_id,
    )
    if not respuesta:
        return defecto
    return _valor_contenido(respuesta.get("contenido_actual"), defecto)


def _revision_equipo(alumno_id, equipo_id, etapa_id, campo_id):
    respuesta = _respuesta_equipo(
        alumno_id,
        equipo_id,
        etapa_id,
        campo_id,
    )
    if not respuesta:
        return None
    return int(respuesta["revision_borrador"])


def _texto(valor):
    return "" if valor is None else str(valor)


def _indice(opciones, valor):
    return opciones.index(valor) if valor in opciones else None


def _opciones_codigos(opciones):
    return [codigo for codigo, _ in opciones]


def _etiqueta_codigo(opciones, codigo):
    mapa = dict(opciones)
    return mapa.get(codigo, codigo)


def _guardar_campo_equipo(
    alumno_id,
    equipo_id,
    etapa_id,
    campo_id,
    tipo_respuesta,
    contenido,
):
    revision = _revision_equipo(
        alumno_id,
        equipo_id,
        etapa_id,
        campo_id,
    )
    return guardar_borrador_equipo(
        alumno_id=alumno_id,
        equipo_id=equipo_id,
        mision_id=MISION_ID,
        etapa_id=etapa_id,
        campo_id=campo_id,
        tipo_respuesta=tipo_respuesta,
        contenido=contenido,
        revision_esperada=revision,
    )


def _guardar_varios_equipo(alumno_id, equipo_id, etapa_id, valores):
    """
    Guarda una etapa campo por campo usando concurrencia optimista.

    valores:
        [(campo_id, tipo_respuesta, contenido), ...]
    """
    for campo_id, tipo_respuesta, contenido in valores:
        _guardar_campo_equipo(
            alumno_id,
            equipo_id,
            etapa_id,
            campo_id,
            tipo_respuesta,
            contenido,
        )


def _actualizar_etapa(alumno_id, equipo_id, etapa_id):
    return actualizar_etapa_equipo(
        alumno_id=alumno_id,
        equipo_id=equipo_id,
        mision_id=MISION_ID,
        etapa_visitada=etapa_id,
        orden_etapas=ORDEN_ETAPAS,
    )


def _clave_navegacion(equipo_id):
    return f"m01_etapa_ui_{equipo_id}"


def _etapa_ui(equipo_id, progreso):
    clave = _clave_navegacion(equipo_id)
    if clave not in st.session_state:
        etapa = progreso.get("etapa_actual") or "PREPARARSE"
        st.session_state[clave] = (
            etapa if etapa in ORDEN_ETAPAS else "PREPARARSE"
        )
    return st.session_state[clave]


def _ir_a(equipo_id, etapa_id):
    st.session_state[_clave_navegacion(equipo_id)] = etapa_id
    st.rerun()


def _mostrar_barra_etapas(equipo_id, etapa_actual_ui):
    actual = ORDEN_ETAPAS.index(etapa_actual_ui)
    progreso_visual = (actual + 1) / len(ORDEN_ETAPAS)
    st.progress(progreso_visual)

    anterior = ORDEN_ETAPAS[actual - 1] if actual > 0 else None
    siguiente = (
        ORDEN_ETAPAS[actual + 1]
        if actual < len(ORDEN_ETAPAS) - 1
        else None
    )

    col_a, col_c = st.columns(2)

    with col_a:
        if anterior and st.button(
            "← " + ETIQUETAS_ETAPA[anterior],
            use_container_width=True,
            key=f"m01_anterior_{equipo_id}_{etapa_actual_ui}",
        ):
            _ir_a(equipo_id, anterior)

    with col_c:
        if siguiente and st.button(
            ETIQUETAS_ETAPA[siguiente] + " →",
            use_container_width=True,
            key=f"m01_siguiente_{equipo_id}_{etapa_actual_ui}",
        ):
            _ir_a(equipo_id, siguiente)


def _mostrar_cabecera(equipo, progreso):
    st.markdown(f"## 🎯 Misión 01 · {TITULO}")
    st.write(OBJETIVO)
    st.caption(INTRODUCCION)

    if equipo is not None:
        nombre = equipo.get("nombre_equipo") or equipo["equipo_id"]
        st.markdown(f"**🏢 Trabajo de equipo:** {nombre}")

    if progreso:
        estado = progreso["estado"]
        st.info(ETIQUETAS_ESTADO.get(estado, estado))


# ============================================================
# PREPARARSE · INDIVIDUAL
# ============================================================

def _prepararse_completo(alumno_id):
    for caso in CASOS_PREPARARSE:
        valor = _valor_individual(
            alumno_id,
            "PREPARARSE",
            caso["campo_id"],
        )
        if valor not in OPCIONES_PROBLEMA_SOLUCION:
            return False

    diferencia = _valor_individual(
        alumno_id,
        "PREPARARSE",
        "diferencia_problema_solucion",
        "",
    )
    return bool(_texto(diferencia).strip())


def _mostrar_prepararse(alumno, *, solo_lectura=False):
    alumno_id = alumno["alumno_id"]
    curso = alumno["curso"]

    st.markdown("### 🧠 1 · PREPARARSE")
    st.write(DESCRIPCIONES_ETAPA["PREPARARSE"])
    st.caption(
        "Actividad individual de entrenamiento · no forma parte de la "
        "Ficha del Problema."
    )

    guardados = {
        caso["campo_id"]: _valor_individual(
            alumno_id,
            "PREPARARSE",
            caso["campo_id"],
        )
        for caso in CASOS_PREPARARSE
    }
    diferencia_guardada = _valor_individual(
        alumno_id,
        "PREPARARSE",
        "diferencia_problema_solucion",
        "",
    )

    with st.form(f"m01_prepararse_{alumno_id}"):
        selecciones = {}

        for caso in CASOS_PREPARARSE:
            st.markdown(f"#### {caso['titulo']}")
            st.write(f"“{caso['texto']}”")
            selecciones[caso["campo_id"]] = st.radio(
                "¿Qué representa esta frase?",
                options=list(OPCIONES_PROBLEMA_SOLUCION),
                index=_indice(
                    list(OPCIONES_PROBLEMA_SOLUCION),
                    guardados[caso["campo_id"]],
                ),
                format_func=lambda opcion: (
                    "🧩 Describe un problema"
                    if opcion == "PROBLEMA"
                    else "🛠️ Ya propone una solución"
                ),
                key=f"m01_prep_{alumno_id}_{caso['campo_id']}",
                disabled=solo_lectura,
            )
            st.divider()

        diferencia = st.text_area(
            "¿Qué diferencia encontraste entre describir un problema "
            "y proponer una solución?",
            value=_texto(diferencia_guardada),
            placeholder=(
                "Explicalo con tus palabras. No buscamos una definición "
                "de memoria."
            ),
            height=120,
            disabled=solo_lectura,
            key=f"m01_prep_diferencia_{alumno_id}",
        )

        guardar = st.form_submit_button(
            "💾 Guardar mi entrenamiento",
            type="primary",
            use_container_width=True,
            disabled=solo_lectura,
        )

    if guardar:
        if any(v is None for v in selecciones.values()):
            st.error("Clasificá los tres casos antes de guardar.")
            return

        if not diferencia.strip():
            st.error("Explicá con tus palabras qué diferencia encontraste.")
            return

        for campo_id, valor in selecciones.items():
            guardar_borrador(
                alumno_id=alumno_id,
                curso=curso,
                mision_id=MISION_ID,
                etapa_id="PREPARARSE",
                campo_id=campo_id,
                tipo_respuesta="OPCION",
                contenido=valor,
            )

        guardar_borrador(
            alumno_id=alumno_id,
            curso=curso,
            mision_id=MISION_ID,
            etapa_id="PREPARARSE",
            campo_id="diferencia_problema_solucion",
            tipo_respuesta="TEXTO_LARGO",
            contenido=diferencia.strip(),
        )

        st.success("✓ Tu entrenamiento quedó guardado.")
        st.rerun()

    if _prepararse_completo(alumno_id):
        st.success(
            "✓ Preparación individual completa. Ya podés llevar esta mirada "
            "al trabajo con tu equipo."
        )


# ============================================================
# OBSERVAR · EQUIPO
# ============================================================

def _mostrar_observar_equipo(alumno_id, equipo_id, *, bloqueado=False):
    st.markdown("### 👀 2 · OBSERVAR")
    st.write(DESCRIPCIONES_ETAPA["OBSERVAR"])

    observacion = _valor_equipo(
        alumno_id, equipo_id, "OBSERVAR", "observacion_inicial", ""
    )
    donde = _valor_equipo(
        alumno_id, equipo_id, "OBSERVAR", "donde_ocurre", ""
    )
    cuando = _valor_equipo(
        alumno_id, equipo_id, "OBSERVAR", "cuando_ocurre", ""
    )

    with st.form(f"m01_observar_equipo_{equipo_id}"):
        nueva_observacion = st.text_area(
            "¿Qué problema o situación real observaron?",
            value=_texto(observacion),
            placeholder=(
                "Describan qué ocurre. Todavía no propongan una solución."
            ),
            height=150,
            disabled=bloqueado,
        )
        nuevo_donde = st.text_input(
            "¿Dónde ocurre?",
            value=_texto(donde),
            placeholder="Por ejemplo: en el aula, en casa, en el barrio...",
            disabled=bloqueado,
        )
        nuevo_cuando = st.text_input(
            "¿Cuándo ocurre?",
            value=_texto(cuando),
            placeholder="¿En qué momento o situación aparece?",
            disabled=bloqueado,
        )

        guardar = st.form_submit_button(
            "💾 Guardar observación del equipo",
            type="primary",
            use_container_width=True,
            disabled=bloqueado,
        )

    if guardar:
        if not all(
            x.strip()
            for x in (nueva_observacion, nuevo_donde, nuevo_cuando)
        ):
            st.error("Completen los tres campos antes de guardar.")
            return

        _guardar_varios_equipo(
            alumno_id,
            equipo_id,
            "OBSERVAR",
            [
                ("observacion_inicial", "TEXTO_LARGO", nueva_observacion.strip()),
                ("donde_ocurre", "TEXTO", nuevo_donde.strip()),
                ("cuando_ocurre", "TEXTO", nuevo_cuando.strip()),
            ],
        )
        _actualizar_etapa(alumno_id, equipo_id, "OBSERVAR")
        st.success("✓ La observación del equipo quedó guardada.")
        st.rerun()


# ============================================================
# COMPRENDER · EQUIPO
# ============================================================

def _mostrar_comprender(alumno_id, equipo_id, *, bloqueado=False):
    st.markdown("### 🧩 3 · COMPRENDER")
    st.write(DESCRIPCIONES_ETAPA["COMPRENDER"])

    grupo = _valor_equipo(
        alumno_id, equipo_id, "COMPRENDER", "grupo_afectado", ""
    )
    frecuencia = _valor_equipo(
        alumno_id, equipo_id, "COMPRENDER", "frecuencia"
    )
    como = _valor_equipo(
        alumno_id, equipo_id, "COMPRENDER", "como_averiguarlo", ""
    )

    codigos = _opciones_codigos(OPCIONES_FRECUENCIA)

    with st.form(f"m01_comprender_{equipo_id}"):
        nuevo_grupo = st.text_area(
            "¿A quién afecta?",
            value=_texto(grupo),
            placeholder=(
                "Describan a la persona o grupo afectado con la mayor "
                "precisión que puedan."
            ),
            height=120,
            disabled=bloqueado,
        )

        nueva_frecuencia = st.radio(
            "¿Con qué frecuencia ocurre?",
            options=codigos,
            index=_indice(codigos, frecuencia),
            format_func=lambda x: _etiqueta_codigo(OPCIONES_FRECUENCIA, x),
            disabled=bloqueado,
        )

        nuevo_como = st.text_area(
            "Si todavía no conocen la frecuencia, ¿cómo podrían averiguarla?",
            value=_texto(como),
            placeholder=(
                "Por ejemplo: observar durante una semana, entrevistar, "
                "hacer una encuesta o consultar registros."
            ),
            height=100,
            disabled=bloqueado,
        )

        guardar = st.form_submit_button(
            "💾 Guardar comprensión del equipo",
            type="primary",
            use_container_width=True,
            disabled=bloqueado,
        )

    if guardar:
        if not nuevo_grupo.strip():
            st.error("Describan a quién afecta el problema.")
            return
        if nueva_frecuencia is None:
            st.error("Seleccionen una opción de frecuencia.")
            return
        if (
            nueva_frecuencia == "TODAVIA_NO_SABEMOS"
            and not nuevo_como.strip()
        ):
            st.error(
                "Si todavía no lo saben, expliquen cómo podrían averiguarlo."
            )
            return

        _guardar_varios_equipo(
            alumno_id,
            equipo_id,
            "COMPRENDER",
            [
                ("grupo_afectado", "TEXTO_LARGO", nuevo_grupo.strip()),
                ("frecuencia", "OPCION", nueva_frecuencia),
                ("como_averiguarlo", "TEXTO_LARGO", nuevo_como.strip()),
            ],
        )
        _actualizar_etapa(alumno_id, equipo_id, "COMPRENDER")
        st.success("✓ La comprensión del problema quedó guardada.")
        st.rerun()


# ============================================================
# INVESTIGAR · EQUIPO
# ============================================================

def _mostrar_investigar(alumno_id, equipo_id, *, bloqueado=False):
    st.markdown("### 🔎 4 · INVESTIGAR")
    st.write(DESCRIPCIONES_ETAPA["INVESTIGAR"])

    solucion = _valor_equipo(
        alumno_id, equipo_id, "INVESTIGAR", "solucion_actual", ""
    )
    tipos = _valor_equipo(
        alumno_id, equipo_id, "INVESTIGAR", "consecuencias_tipos", []
    )
    if not isinstance(tipos, list):
        tipos = []

    descripcion = _valor_equipo(
        alumno_id,
        equipo_id,
        "INVESTIGAR",
        "consecuencias_descripcion",
        "",
    )

    opciones_tipos = _opciones_codigos(OPCIONES_CONSECUENCIAS)

    with st.form(f"m01_investigar_{equipo_id}"):
        nueva_solucion = st.text_area(
            "¿Cómo se resuelve hoy?",
            value=_texto(solucion),
            placeholder=(
                "¿Qué hacen actualmente las personas cuando aparece "
                "este problema?"
            ),
            height=130,
            disabled=bloqueado,
        )

        nuevos_tipos = st.multiselect(
            "¿Qué tipos de consecuencias observan? · opcional",
            options=opciones_tipos,
            default=[x for x in tipos if x in opciones_tipos],
            format_func=lambda x: _etiqueta_codigo(
                OPCIONES_CONSECUENCIAS, x
            ),
            disabled=bloqueado,
        )

        nueva_descripcion = st.text_area(
            "Expliquen con sus palabras qué consecuencias produce.",
            value=_texto(descripcion),
            placeholder=(
                "No alcanza con marcar categorías: cuenten qué pasa "
                "como consecuencia del problema."
            ),
            height=130,
            disabled=bloqueado,
        )

        guardar = st.form_submit_button(
            "💾 Guardar investigación del equipo",
            type="primary",
            use_container_width=True,
            disabled=bloqueado,
        )

    if guardar:
        if not nueva_solucion.strip():
            st.error("Expliquen cómo se resuelve actualmente.")
            return
        if not nueva_descripcion.strip():
            st.error("Describan las consecuencias del problema.")
            return

        _guardar_varios_equipo(
            alumno_id,
            equipo_id,
            "INVESTIGAR",
            [
                ("solucion_actual", "TEXTO_LARGO", nueva_solucion.strip()),
                ("consecuencias_tipos", "MULTIOPCION", nuevos_tipos),
                (
                    "consecuencias_descripcion",
                    "TEXTO_LARGO",
                    nueva_descripcion.strip(),
                ),
            ],
        )
        _actualizar_etapa(alumno_id, equipo_id, "INVESTIGAR")
        st.success("✓ La investigación del equipo quedó guardada.")
        st.rerun()


# ============================================================
# EVIDENCIAR · EQUIPO
# ============================================================

def _evidencia_guardada(alumno_id, equipo_id, numero):
    valor = _valor_equipo(
        alumno_id,
        equipo_id,
        "EVIDENCIAR",
        f"evidencia_{numero}",
        {},
    )
    return valor if isinstance(valor, dict) else {}


def _mostrar_evidenciar(alumno_id, equipo_id, *, bloqueado=False):
    st.markdown("### 🧾 5 · EVIDENCIAR")
    st.write(DESCRIPCIONES_ETAPA["EVIDENCIAR"])
    st.info(
        "Una evidencia puede surgir de observar, entrevistar, encuestar, "
        "medir o consultar un registro. Lo importante es poder contar "
        "qué averiguaron y de dónde salió."
    )

    metodos = _opciones_codigos(METODOS_EVIDENCIA)
    evidencias = {
        n: _evidencia_guardada(alumno_id, equipo_id, n)
        for n in (1, 2, 3)
    }

    with st.form(f"m01_evidenciar_{equipo_id}"):
        nuevas = {}

        for numero in (1, 2, 3):
            actual = evidencias[numero]
            st.markdown(f"#### Evidencia {numero}")

            observado = st.text_area(
                "¿Qué observaron o averiguaron?",
                value=_texto(actual.get("observado", "")),
                height=100,
                disabled=bloqueado,
                key=f"m01_ev_obs_{equipo_id}_{numero}",
            )

            metodo_actual = actual.get("metodo")
            metodo = st.selectbox(
                "¿Cómo obtuvieron esta evidencia?",
                options=metodos,
                index=(
                    metodos.index(metodo_actual)
                    if metodo_actual in metodos
                    else 0
                ),
                format_func=lambda x: _etiqueta_codigo(
                    METODOS_EVIDENCIA, x
                ),
                disabled=bloqueado,
                key=f"m01_ev_met_{equipo_id}_{numero}",
            )

            contexto = st.text_input(
                "¿Dónde o cuándo la obtuvieron?",
                value=_texto(actual.get("contexto", "")),
                disabled=bloqueado,
                key=f"m01_ev_ctx_{equipo_id}_{numero}",
            )

            nuevas[numero] = {
                "observado": observado.strip(),
                "metodo": metodo,
                "contexto": contexto.strip(),
            }
            st.divider()

        guardar = st.form_submit_button(
            "💾 Guardar evidencias del equipo",
            type="primary",
            use_container_width=True,
            disabled=bloqueado,
        )

    if guardar:
        for numero, evidencia in nuevas.items():
            if not evidencia["observado"] or not evidencia["contexto"]:
                st.error(
                    f"Completá la descripción y el contexto de la "
                    f"evidencia {numero}."
                )
                return

        _guardar_varios_equipo(
            alumno_id,
            equipo_id,
            "EVIDENCIAR",
            [
                (
                    f"evidencia_{numero}",
                    "JSON",
                    nuevas[numero],
                )
                for numero in (1, 2, 3)
            ],
        )
        _actualizar_etapa(alumno_id, equipo_id, "EVIDENCIAR")
        st.success("✓ Las tres evidencias quedaron guardadas.")
        st.rerun()


# ============================================================
# FORMULAR · EQUIPO
# ============================================================

def _mostrar_formular(alumno_id, equipo_id, *, bloqueado=False):
    st.markdown("### ✍️ 6 · FORMULAR")
    st.write(DESCRIPCIONES_ETAPA["FORMULAR"])

    problema = _valor_equipo(
        alumno_id,
        equipo_id,
        "FORMULAR",
        "problema_una_oracion",
        "",
    )
    oportunidad = _valor_equipo(
        alumno_id,
        equipo_id,
        "FORMULAR",
        "hipotesis_oportunidad",
        "",
    )

    st.info(
        "💡 Si necesitan ayuda para ordenar la idea pueden pensar: "
        "“Observamos que ___ afecta a ___ cuando ___, provocando ___”. "
        "No es obligatorio usar esta fórmula."
    )

    with st.form(f"m01_formular_{equipo_id}"):
        nuevo_problema = st.text_area(
            "Problema en una oración",
            value=_texto(problema),
            placeholder=(
                "Una oración clara que explique el problema, no la solución."
            ),
            height=120,
            disabled=bloqueado,
        )

        nueva_oportunidad = st.text_area(
            "Primera hipótesis de oportunidad",
            value=_texto(oportunidad),
            placeholder=(
                "¿Dónde ven una oportunidad de mejorar esta situación? "
                "Todavía no diseñen el producto."
            ),
            height=120,
            disabled=bloqueado,
        )

        guardar = st.form_submit_button(
            "💾 Guardar formulación del equipo",
            type="primary",
            use_container_width=True,
            disabled=bloqueado,
        )

    if guardar:
        if not nuevo_problema.strip():
            st.error("Escriban el problema en una oración.")
            return
        if not nueva_oportunidad.strip():
            st.error("Escriban una primera hipótesis de oportunidad.")
            return

        _guardar_varios_equipo(
            alumno_id,
            equipo_id,
            "FORMULAR",
            [
                (
                    "problema_una_oracion",
                    "TEXTO_LARGO",
                    nuevo_problema.strip(),
                ),
                (
                    "hipotesis_oportunidad",
                    "TEXTO_LARGO",
                    nueva_oportunidad.strip(),
                ),
            ],
        )
        _actualizar_etapa(alumno_id, equipo_id, "FORMULAR")
        st.success("✓ La formulación del problema quedó guardada.")
        st.rerun()


# ============================================================
# FICHA DEL PROBLEMA · CONSOLIDACIÓN
# ============================================================

def _mostrar_valor_ficha(titulo, valor):
    st.markdown(f"**{titulo}**")
    if isinstance(valor, list):
        if valor:
            for item in valor:
                st.write(f"- {item}")
        else:
            st.caption("Todavía sin información.")
    elif isinstance(valor, dict):
        if valor:
            st.write(valor)
        else:
            st.caption("Todavía sin información.")
    elif valor is None or not str(valor).strip():
        st.caption("Todavía sin información.")
    else:
        st.write(valor)


def _mostrar_ficha(alumno_id, equipo_id, progreso, *, bloqueado=False):
    st.markdown(f"### 📋 7 · {ENTREGABLE}")
    st.write(DESCRIPCIONES_ETAPA["FICHA"])
    st.caption(
        "Esta ficha se arma automáticamente con lo que el equipo fue "
        "construyendo. No tienen que escribir todo de nuevo."
    )

    problema = _valor_equipo(
        alumno_id, equipo_id, "FORMULAR", "problema_una_oracion", ""
    )
    grupo = _valor_equipo(
        alumno_id, equipo_id, "COMPRENDER", "grupo_afectado", ""
    )
    solucion = _valor_equipo(
        alumno_id, equipo_id, "INVESTIGAR", "solucion_actual", ""
    )
    consecuencias = _valor_equipo(
        alumno_id,
        equipo_id,
        "INVESTIGAR",
        "consecuencias_descripcion",
        "",
    )
    oportunidad = _valor_equipo(
        alumno_id, equipo_id, "FORMULAR", "hipotesis_oportunidad", ""
    )

    _mostrar_valor_ficha("Problema en una oración", problema)
    st.divider()
    _mostrar_valor_ficha("¿A quién afecta?", grupo)
    st.divider()

    st.markdown("**Situación actual**")
    _mostrar_valor_ficha("¿Cómo se resuelve hoy?", solucion)
    _mostrar_valor_ficha("Consecuencias", consecuencias)
    st.divider()

    st.markdown("**Tres evidencias u observaciones**")
    for numero in (1, 2, 3):
        evidencia = _evidencia_guardada(alumno_id, equipo_id, numero)
        if evidencia:
            metodo = _etiqueta_codigo(
                METODOS_EVIDENCIA,
                evidencia.get("metodo"),
            )
            st.markdown(f"**Evidencia {numero}**")
            st.write(evidencia.get("observado", ""))
            st.caption(
                f"{metodo} · {evidencia.get('contexto', '')}"
            )
        else:
            st.caption(f"Evidencia {numero}: todavía sin información.")

    st.divider()
    _mostrar_valor_ficha("Primera hipótesis de oportunidad", oportunidad)

    st.divider()
    st.markdown("#### 👨‍🏫 Professor Checkpoint")
    st.info(PROFESSOR_CHECKPOINT)

    estado = progreso["estado"]
    ultima_version = int(progreso.get("ultima_version_entregada") or 0)

    if estado == "PENDIENTE_REVISION":
        st.warning(
            f"📨 La versión V{ultima_version} ya fue enviada. "
            "El equipo debe esperar la revisión del profesor."
        )
        return

    if estado == "APROBADA":
        st.success(
            f"🎉 Misión aprobada · V{ultima_version}. "
            "El equipo demostró que su problema merece ser investigado."
        )
        return

    descripcion_cambios = None

    if estado == "REQUIERE_AJUSTES":
        st.warning(
            "El profesor pidió ajustes. Revisen las etapas anteriores, "
            "mejoren el borrador y vuelvan a la Ficha."
        )
        descripcion_cambios = st.text_area(
            "¿Qué cambiaron desde la entrega anterior?",
            placeholder=(
                "Para la reentrega cuenten brevemente qué corrigieron "
                "o mejoraron."
            ),
            key=f"m01_cambios_{equipo_id}_{ultima_version + 1}",
        )

    if st.button(
        "📨 Enviar Ficha al profesor",
        type="primary",
        use_container_width=True,
        disabled=bloqueado,
        key=f"m01_entregar_{equipo_id}_{ultima_version + 1}",
    ):
        if (
            estado == "REQUIERE_AJUSTES"
            and not _texto(descripcion_cambios).strip()
        ):
            st.error(
                "Para una reentrega necesitamos saber qué cambió "
                "desde la versión anterior."
            )
            return

        _actualizar_etapa(alumno_id, equipo_id, "FICHA")

        resultado = entregar_mision_equipo(
            alumno_id=alumno_id,
            equipo_id=equipo_id,
            mision_id=MISION_ID,
            campos_requeridos=CAMPOS_REQUERIDOS_ENTREGA,
            descripcion_cambios=descripcion_cambios,
            validador_mision=validar_entrega,
            sesion_id=st.session_state.get("sesion_id"),
        )

        version = resultado["version_entrega"]
        st.success(
            f"✓ Ficha V{version} enviada al profesor. "
            "La entrega quedó congelada como evidencia histórica."
        )
        st.rerun()


# ============================================================
# REFLEXIÓN INDIVIDUAL COMPLEMENTARIA
# ============================================================

def _mostrar_reflexion_individual(alumno, *, solo_lectura=False):
    alumno_id = alumno["alumno_id"]
    curso = alumno["curso"]

    actual = _valor_individual(
        alumno_id,
        REFLEXION_INDIVIDUAL["etapa_id"],
        REFLEXION_INDIVIDUAL["campo_id"],
        "",
    )

    with st.expander("🌱 Mi reflexión individual · complementaria"):
        st.caption(
            "Esta reflexión es personal. No forma parte de la Ficha y "
            "no bloquea el trabajo de tu equipo."
        )

        with st.form(f"m01_reflexion_{alumno_id}"):
            nueva = st.text_area(
                REFLEXION_INDIVIDUAL["pregunta"],
                value=_texto(actual),
                height=130,
                disabled=solo_lectura,
            )
            guardar = st.form_submit_button(
                "💾 Guardar mi reflexión",
                use_container_width=True,
                disabled=solo_lectura,
            )

        if guardar:
            if not nueva.strip():
                st.error("Escribí tu reflexión antes de guardarla.")
                return

            guardar_borrador(
                alumno_id=alumno_id,
                curso=curso,
                mision_id=MISION_ID,
                etapa_id=REFLEXION_INDIVIDUAL["etapa_id"],
                campo_id=REFLEXION_INDIVIDUAL["campo_id"],
                tipo_respuesta=REFLEXION_INDIVIDUAL["tipo_respuesta"],
                contenido=nueva.strip(),
            )
            st.success("✓ Tu reflexión individual quedó guardada.")
            st.rerun()


# ============================================================
# ORQUESTADOR
# ============================================================

def mostrar_observar(alumno, *, modo_demo=False, solo_lectura=False):
    """
    Entrada compatible con app.py.

    Históricamente mostraba sólo OBSERVAR. Ahora orquesta M01 completa
    sin obligar a modificar app.py en esta etapa del desarrollo.
    """
    alumno_id = alumno["alumno_id"]
    
    equipo = obtener_equipo_alumno(alumno_id)

    # --------------------------------------------------------
    # DEMO / INSPECCIÓN SIN EQUIPO
    # --------------------------------------------------------
    if equipo is None:
        _mostrar_cabecera(None, None)

        if modo_demo:
            st.info(
                "🧪 En modo DEMO podés probar la actividad individual "
                "PREPARARSE. El trabajo grupal requiere un equipo real "
                "para no mezclar datos técnicos con datos de alumnos."
            )
            _mostrar_prepararse(alumno, solo_lectura=solo_lectura)
        else:
            st.warning(
                "Esta misión tiene trabajo colaborativo y todavía no "
                "encontramos un equipo activo para este alumno."
            )
        return

    equipo_id = equipo["equipo_id"]

    # --------------------------------------------------------
    # INICIAR / RECUPERAR PROGRESO DEL EQUIPO
    # --------------------------------------------------------
    progreso = obtener_progreso_equipo(
        alumno_id,
        equipo_id,
        MISION_ID,
    )

    if progreso is None:
        _mostrar_cabecera(equipo, None)
        st.markdown("### 🚀 La misión está lista")
        st.write(
            "El primer integrante que la inicie abrirá el espacio de "
            "trabajo compartido para todo el equipo."
        )

        if solo_lectura:
            st.info(
                "👁️ Vista docente de inspección · la misión todavía "
                "no fue iniciada por el equipo."
            )
            return

        if st.button(
            "🚀 Iniciar Misión 01",
            type="primary",
            use_container_width=True,
            key=f"m01_iniciar_{equipo_id}",
        ):
            iniciar_mision_equipo(
                alumno_id=alumno_id,
                equipo_id=equipo_id,
                mision_id=MISION_ID,
                etapa_inicial="PREPARARSE",
            )
            st.session_state[_clave_navegacion(equipo_id)] = "PREPARARSE"
            st.rerun()
        return

    _mostrar_cabecera(equipo, progreso)

    estado = progreso["estado"]
    bloqueado_equipo = solo_lectura or estado in ESTADOS_BLOQUEADOS

    if estado == "PENDIENTE_REVISION":
        st.warning(
            "📨 La Ficha ya fue enviada. Mientras el profesor la revisa, "
            "el borrador del equipo permanece bloqueado."
        )
    elif estado == "REQUIERE_AJUSTES":
        st.warning(
            "🔧 El profesor pidió ajustes. El equipo puede volver a las "
            "etapas anteriores, corregir y realizar una nueva entrega."
        )
    elif estado == "APROBADA":
        st.success(
            "🎉 Misión aprobada. La Ficha y su historia quedan conservadas."
        )

    etapa = _etapa_ui(equipo_id, progreso)

    st.markdown(
        f"#### {ETIQUETAS_ETAPA[etapa]} "
        f"· paso {ORDEN_ETAPAS.index(etapa) + 1} de {len(ORDEN_ETAPAS)}"
    )

    # PREPARARSE es individual: el bloqueo de la Ficha grupal no impide
    # una reflexión personal, salvo en inspección docente.
    if etapa == "PREPARARSE":
        _mostrar_prepararse(alumno, solo_lectura=solo_lectura)
    elif etapa == "OBSERVAR":
        _mostrar_observar_equipo(
            alumno_id, equipo_id, bloqueado=bloqueado_equipo
        )
    elif etapa == "COMPRENDER":
        _mostrar_comprender(
            alumno_id, equipo_id, bloqueado=bloqueado_equipo
        )
    elif etapa == "INVESTIGAR":
        _mostrar_investigar(
            alumno_id, equipo_id, bloqueado=bloqueado_equipo
        )
    elif etapa == "EVIDENCIAR":
        _mostrar_evidenciar(
            alumno_id, equipo_id, bloqueado=bloqueado_equipo
        )
    elif etapa == "FORMULAR":
        _mostrar_formular(
            alumno_id, equipo_id, bloqueado=bloqueado_equipo
        )
    elif etapa == "FICHA":
        _mostrar_ficha(
            alumno_id,
            equipo_id,
            progreso,
            bloqueado=bloqueado_equipo,
        )

    st.divider()
    _mostrar_barra_etapas(equipo_id, etapa)

    if etapa in {"FORMULAR", "FICHA"}:
        _mostrar_reflexion_individual(
            alumno,
            solo_lectura=solo_lectura,
        )


# Alias semántico para código futuro.
mostrar_mision_01 = mostrar_observar
