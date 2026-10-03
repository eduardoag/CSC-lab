from zoneinfo import ZoneInfo

import streamlit as st
from sqlalchemy import text

from config.cursos import CURSOS
from config.horarios import ZONA_HORARIA
from core.base_datos import obtener_conexion
from core.evaluacion import revisar_mision


# ==========================================================
# UTILIDADES
# ==========================================================

def hora_local(fecha):
    if fecha is None:
        return "—"

    zona = ZoneInfo(ZONA_HORARIA)

    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=ZoneInfo("UTC"))

    return fecha.astimezone(zona).strftime(
        "%d/%m/%Y · %H:%M:%S"
    )


def etiqueta_estado(estado):
    etiquetas = {
        "NO_INICIADA": "⚪ No iniciada",
        "EN_PROGRESO": "🔵 En progreso",
        "PENDIENTE_REVISION": "🟠 Pendiente de revisión",
        "REQUIERE_AJUSTES": "🟡 Requiere ajustes",
        "APROBADA": "🟢 Aprobada",
    }

    return etiquetas.get(estado, estado)


# ==========================================================
# CONSULTAS
# ==========================================================

def obtener_misiones(curso_id):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultados = sesion.execute(
            text("""
                SELECT DISTINCT mision_id
                FROM progreso_misiones
                WHERE curso = :curso
                ORDER BY mision_id
            """),
            {"curso": curso_id},
        ).scalars().all()

    return list(resultados)


def obtener_resumen(curso_id, mision_id):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        matricula = sesion.execute(
            text("""
                SELECT COUNT(*)
                FROM alumnos
                WHERE curso = :curso
                AND activo = TRUE
                AND tipo_alumno = 'REAL'
            """),
            {"curso": curso_id},
        ).scalar_one()

        filas = sesion.execute(
            text("""
                SELECT
                    estado,
                    COUNT(*)
                FROM progreso_misiones
                WHERE curso = :curso
                  AND mision_id = :mision
                GROUP BY estado
            """),
            {
                "curso": curso_id,
                "mision": mision_id,
            },
        ).all()

    estados = {
        "EN_PROGRESO": 0,
        "PENDIENTE_REVISION": 0,
        "REQUIERE_AJUSTES": 0,
        "APROBADA": 0,
    }

    for estado, cantidad in filas:
        estados[estado] = cantidad

    iniciaron = sum(estados.values())

    return {
        "matricula": matricula,
        "no_iniciaron": max(0, matricula - iniciaron),
        "iniciaron": iniciaron,
        **estados,
    }


def obtener_alumnos_mision(curso_id, mision_id):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultados = sesion.execute(
            text("""
                SELECT
                    a.alumno_id,
                    a.numero_lista,
                    a.nombre,
                    a.apellido,

                    COALESCE(
                        p.estado,
                        'NO_INICIADA'
                    ) AS estado,

                    p.etapa_actual,
                    p.fecha_inicio,
                    p.fecha_ultima_actividad,
                    p.fecha_envio,
                    p.fecha_revision,
                    p.devolucion_docente

                FROM alumnos AS a

                LEFT JOIN progreso_misiones AS p
                  ON p.alumno_id = a.alumno_id
                 AND p.mision_id = :mision

                WHERE a.curso = :curso
                    AND a.activo = TRUE
                    AND a.tipo_alumno = 'REAL'

                ORDER BY a.numero_lista
            """),
            {
                "curso": curso_id,
                "mision": mision_id,
            },
        ).mappings().all()

    return [dict(fila) for fila in resultados]


def obtener_bitacora(alumno_id, mision_id):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultados = sesion.execute(
            text("""
                SELECT
                    fecha_hora,
                    tipo_evento,
                    etapa_id,
                    detalle
                FROM eventos_aprendizaje
                WHERE alumno_id = :alumno_id
                  AND mision_id = :mision_id
                ORDER BY fecha_hora
            """),
            {
                "alumno_id": alumno_id,
                "mision_id": mision_id,
            },
        ).mappings().all()

    return [dict(fila) for fila in resultados]

def obtener_alumnos_curso(curso_id):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultados = sesion.execute(
            text("""
                SELECT
                    alumno_id,
                    numero_lista,
                    nombre,
                    apellido,
                    curso
                FROM alumnos
                WHERE curso = :curso
                    AND activo = TRUE
                    AND tipo_alumno = 'REAL'
                ORDER BY numero_lista
            """),
            {
                "curso": curso_id,
            },
        ).mappings().all()

    return [dict(fila) for fila in resultados]

def obtener_alumno_demo():

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultado = sesion.execute(
            text("""
                SELECT
                    alumno_id,
                    numero_lista,
                    nombre,
                    apellido,
                    curso,
                    activo,
                    tipo_alumno
                FROM alumnos
                WHERE alumno_id = 'CSC-DEMO-001'
                  AND tipo_alumno = 'DEMO'
                  AND activo = TRUE
            """)
        ).mappings().first()

    if resultado is None:
        return None

    return dict(resultado)

def mostrar_dashboard_docente():
    # ==========================================================
    # ENCABEZADO
    # ==========================================================

    st.title("🧪 CSC Lab · Dashboard Docente")

    st.caption(
        "Seguimiento pedagógico · Colegio Sagrado Corazón"
    )

    modo = st.radio(
        "Herramienta docente",
        options=[
            "📊 Seguimiento",
            "👁️ Vista como alumno",
            "🧪 Laboratorio DEMO",
    ],
    horizontal=True,
    key="herramienta_docente",
)

    st.divider()

    if modo == "👁️ Vista como alumno":
        mostrar_selector_vista_alumno()
        return

    if modo == "🧪 Laboratorio DEMO":
        mostrar_laboratorio_demo()
        return

    # ==========================================================
    # SELECTORES
    # ==========================================================

    col_curso, col_mision = st.columns(2)

    with col_curso:

        curso_id = st.selectbox(
            "Curso",
            options=list(CURSOS.keys()),
            format_func=lambda curso: CURSOS[curso]["nombre"],
            key="docente_curso",
        )

    misiones = obtener_misiones(curso_id)

    if not misiones:

        st.info(
            "Todavía no existen misiones iniciadas "
            "para este curso."
        )

        return

    with col_mision:

        mision_id = st.selectbox(
            "Misión",
            options=misiones,
            key="docente_mision",
        )


    # ==========================================================
    # RESUMEN
    # ==========================================================

    resumen = obtener_resumen(
        curso_id,
        mision_id,
    )

    st.markdown(
        f"## {CURSOS[curso_id]['nombre']} · {mision_id}"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Matrícula",
        resumen["matricula"],
    )

    c2.metric(
        "No iniciaron",
        resumen["no_iniciaron"],
    )

    c3.metric(
        "En progreso",
        resumen["EN_PROGRESO"],
    )

    c4.metric(
        "Esperando revisión",
        resumen["PENDIENTE_REVISION"],
    )

    c5.metric(
        "Aprobadas",
        resumen["APROBADA"],
    )

    if resumen["REQUIERE_AJUSTES"]:

        st.warning(
            f"🟡 {resumen['REQUIERE_AJUSTES']} "
            "trabajo(s) requieren ajustes."
        )

    st.divider()


    # ==========================================================
    # NECESITAN MI ATENCIÓN
    # ==========================================================

    st.subheader("🎯 Necesitan mi atención")

    alumnos = obtener_alumnos_mision(
        curso_id,
        mision_id,
    )

    pendientes = [
        alumno
        for alumno in alumnos
        if alumno["estado"]
        in {
            "PENDIENTE_REVISION",
            "REQUIERE_AJUSTES",
        }
    ]

    if not pendientes:

        st.success(
            "No hay trabajos esperando intervención docente."
        )

    else:

        for alumno in pendientes:

            st.markdown(
                f"**#{alumno['numero_lista']} · "
                f"{alumno['nombre']} "
                f"{alumno['apellido']}** — "
                f"{etiqueta_estado(alumno['estado'])}"
            )

    st.divider()


    # ==========================================================
    # MAPA DEL CURSO
    # ==========================================================

    st.subheader("🗺️ Mapa del curso")

    filtro_estado = st.selectbox(
        "Mostrar",
        options=[
            "TODOS",
            "NO_INICIADA",
            "EN_PROGRESO",
            "PENDIENTE_REVISION",
            "REQUIERE_AJUSTES",
            "APROBADA",
        ],
        format_func=lambda estado: (
            "Todos"
            if estado == "TODOS"
            else etiqueta_estado(estado)
        ),
        key="docente_filtro_estado",
    )

    if filtro_estado == "TODOS":

        alumnos_filtrados = alumnos

    else:

        alumnos_filtrados = [
            alumno
            for alumno in alumnos
            if alumno["estado"] == filtro_estado
        ]

    for alumno in alumnos_filtrados:

        titulo = (
            f"#{alumno['numero_lista']} · "
            f"{alumno['nombre']} "
            f"{alumno['apellido']} · "
            f"{etiqueta_estado(alumno['estado'])}"
        )

        with st.expander(titulo):

            st.write(
                "**Etapa actual:** "
                f"{alumno['etapa_actual'] or '—'}"
            )

            st.write(
                "**Inicio:** "
                f"{hora_local(alumno['fecha_inicio'])}"
            )

            st.write(
                "**Última actividad:** "
                f"{hora_local(alumno['fecha_ultima_actividad'])}"
            )

            if alumno["fecha_envio"]:

                st.write(
                    "**Enviado:** "
                    f"{hora_local(alumno['fecha_envio'])}"
                )

            if alumno["fecha_revision"]:

                st.write(
                    "**Revisado:** "
                    f"{hora_local(alumno['fecha_revision'])}"
                )
            if alumno["devolucion_docente"]:

                st.markdown("#### 📝 Última devolución docente")

                st.info(
                    alumno["devolucion_docente"]
                )
            # ==================================================
            # REVISIÓN DOCENTE
            # ==================================================

            if alumno["estado"] == "PENDIENTE_REVISION":

                st.markdown("#### 👨‍🏫 Revisión docente")

                with st.form(
                    key=(
                        f"revision_"
                        f"{alumno['alumno_id']}_"
                        f"{mision_id}"
                    )
                ):

                    devolucion = st.text_area(
                        "Devolución",
                        placeholder=(
                            "Escribí una devolución concreta "
                            "que ayude al alumno a avanzar..."
                        ),
                        height=130,
                    )

                    col_ajustes, col_aprobar = st.columns(2)

                    requiere_ajustes = col_ajustes.form_submit_button(
                        "🟡 Requiere ajustes",
                        use_container_width=True,
                    )

                    aprobar = col_aprobar.form_submit_button(
                        "🟢 Aprobar",
                        use_container_width=True,
                    )

                    if requiere_ajustes or aprobar:

                        if not devolucion.strip():

                            st.error(
                                "Escribí una devolución antes "
                                "de realizar la revisión."
                            )

                        else:

                            nuevo_estado = (
                                "REQUIERE_AJUSTES"
                                if requiere_ajustes
                                else "APROBADA"
                            )

                            try:

                                revisar_mision(
                                    alumno_id=alumno["alumno_id"],
                                    curso=curso_id,
                                    mision_id=mision_id,
                                    nuevo_estado=nuevo_estado,
                                    devolucion=devolucion,
                                )

                            except ValueError as error:

                                st.error(str(error))

                            else:

                                st.success(
                                    "Revisión registrada correctamente."
                                )

                                st.rerun()

            eventos = obtener_bitacora(
                alumno["alumno_id"],
                mision_id,
            )

            if eventos:

                st.markdown("#### 🕒 Trayectoria")

                for evento in eventos:

                    tipo = evento[
                        "tipo_evento"
                    ].replace("_", " ")

                    etapa = evento["etapa_id"]

                    descripcion = tipo

                    if etapa:
                        descripcion += f" · {etapa}"

                    st.markdown(
                        f"**{hora_local(evento['fecha_hora'])}** "
                        f"— {descripcion}"
                    )

                    if evento["detalle"]:

                        with st.expander(
                            "Detalle del evento"
                        ):
                            st.json(
                                evento["detalle"]
                            )

            elif alumno["estado"] == "NO_INICIADA":

                st.caption(
                    "Todavía no existen eventos "
                    "para esta misión."
                )
def mostrar_selector_vista_alumno():

    st.subheader("👁️ Vista como alumno")

    st.info(
        "Esta vista permite comprobar CSC Lab tal como lo verá "
        "un alumno, sin depender del horario de clases."
    )

    curso_id = st.selectbox(
        "Curso",
        options=list(CURSOS.keys()),
        format_func=lambda curso: CURSOS[curso]["nombre"],
        key="preview_curso",
    )

    alumnos = obtener_alumnos_curso(curso_id)

    if not alumnos:
        st.warning(
            "No hay alumnos activos en este curso."
        )
        return

    # Diccionario estable alumno_id -> datos del alumno
    alumnos_por_id = {
        alumno["alumno_id"]: alumno
        for alumno in alumnos
    }

    ids_validos = list(alumnos_por_id.keys())

    # Si Streamlit conserva un alumno perteneciente a otro curso,
    # restablecemos el selector al primer alumno válido.
    if st.session_state.get("preview_alumno_selector") not in ids_validos:
        st.session_state.preview_alumno_selector = ids_validos[0]

    alumno_id = st.selectbox(
        "Alumno de prueba",
        options=ids_validos,
        format_func=lambda identificador: (
            f"#{alumnos_por_id[identificador]['numero_lista']} · "
            f"{alumnos_por_id[identificador]['nombre']} "
            f"{alumnos_por_id[identificador]['apellido']}"
        ),
        key="preview_alumno_selector",
    )

    # Ya no usamos next().
    alumno = alumnos_por_id[alumno_id]

    st.caption(
        "⚠️ Modo de inspección docente. "
        "No se registrará una sesión del alumno "
        "ni se modificarán sus datos."
    )

    if st.button(
        "👁️ Entrar en vista como alumno",
        type="primary",
        use_container_width=True,
        key="entrar_preview_alumno",
    ):
        st.session_state.preview_alumno = alumno
        st.session_state.vista_alumno_docente = True
        st.session_state.modo_demo = False

        st.rerun()

def mostrar_laboratorio_demo():

    st.subheader("🧪 Laboratorio DEMO")

    st.info(
        "Entorno técnico de pruebas de CSC Lab. "
        "Todo el progreso que generemos aquí pertenecerá "
        "exclusivamente al alumno DEMO."
    )

    alumno = obtener_alumno_demo()

    if alumno is None:
        st.error(
            "No se encontró CSC-DEMO-001 en PostgreSQL."
        )
        return

    st.success(
        f"✓ {alumno['nombre']} {alumno['apellido']} · "
        f"{alumno['curso']} · entorno aislado"
    )

    st.markdown(
        """
**Este entorno podrá:**

- recorrer misiones completas;
- guardar respuestas de prueba;
- generar eventos pedagógicos;
- realizar entregas y reentregas;
- recibir devoluciones docentes;
- reiniciarse cuando necesitemos repetir una prueba.
"""
    )

    if st.button(
        "🧪 Entrar al laboratorio DEMO",
        type="primary",
        use_container_width=True,
        key="entrar_laboratorio_demo",
    ):
        st.session_state.preview_alumno = alumno
        st.session_state.vista_alumno_docente = True
        st.session_state.modo_demo = True

        st.rerun()
