"""CSC Lab · 5.º TIC · Misión 01. Interfaz de equipo sobre motor V2.2."""
import streamlit as st
from core.entregas_equipo import entregar_mision_equipo
from core.equipos import obtener_equipo_alumno
from core.progreso_equipo import iniciar_mision_equipo, obtener_progreso_equipo, actualizar_etapa_equipo
from core.respuestas_equipo import obtener_respuesta_equipo, guardar_borrador_equipo, ConflictoBorradorEquipoError
from misiones.quinto.mision_01_config import (MISION_ID,TITULO,OBJETIVO,INTRODUCCION,ORDEN_ETAPAS,ENTREGABLE,PROFESSOR_CHECKPOINT,METODOS_EVIDENCIA,CAMPOS_REQUERIDOS_ENTREGA,validar_entrega)

ETIQUETAS={"DESCUBRIR":"🔎 Descubrir","PERFILAR":"👥 Perfilar","INVESTIGAR":"🧭 Investigar","EVIDENCIAR":"🧾 Evidenciar","SUPUESTOS":"💡 Supuestos","FICHA":"📋 Ficha"}
BLOQUEADOS={"PENDIENTE_REVISION","APROBADA"}

def _respuesta(alumno_id,equipo_id,etapa,campo):
    return obtener_respuesta_equipo(alumno_id,equipo_id,MISION_ID,etapa,campo)

def _valor(alumno_id,equipo_id,etapa,campo,defecto=""):
    r=_respuesta(alumno_id,equipo_id,etapa,campo)
    if not r: return defecto
    v=r["contenido_actual"]
    return v.get("valor",v) if isinstance(v,dict) else v

def _guardar(alumno_id,equipo_id,etapa,campos):
    # Cada campo conserva su revisión Bn en el motor universal.
    for campo,tipo,valor in campos:
        r=_respuesta(alumno_id,equipo_id,etapa,campo)
        guardar_borrador_equipo(alumno_id=alumno_id,equipo_id=equipo_id,mision_id=MISION_ID,etapa_id=etapa,campo_id=campo,tipo_respuesta=tipo,contenido=valor,revision_esperada=int(r["revision_borrador"]) if r else None)
    actualizar_etapa_equipo(alumno_id=alumno_id,equipo_id=equipo_id,mision_id=MISION_ID,etapa_visitada=etapa,orden_etapas=ORDEN_ETAPAS)
    st.session_state[f"m01_5_flash_{equipo_id}"]="✓ El trabajo del equipo quedó guardado."
    st.rerun()

def _formulario(alumno_id,equipo_id,etapa,bloqueado):
    preguntas={
        "DESCUBRIR": [("problema_una_oracion","¿Qué problema real identificaron? Exprésenlo en una oración."),("descripcion_problema","Describan qué ocurre y por qué merece investigarse.")],
        "PERFILAR": [("cliente_perfil","¿Quién experimenta el problema? Describan el perfil inicial del cliente."),("contexto_cliente","¿En qué situaciones o momentos lo experimenta?")],
        "INVESTIGAR": [("solucion_actual","¿Cómo resuelven hoy este problema las personas afectadas?")],
        "SUPUESTOS": [("supuestos_pendientes","¿Qué afirmaciones del equipo todavía son supuestos y no hechos comprobados?"),("como_validarlos","¿Cómo podrían comprobar o refutar esos supuestos?")],
    }
    st.write({"DESCUBRIR":"Un problema antes que una tecnología.","PERFILAR":"Conozcan a las personas, no inventen un cliente ideal.","INVESTIGAR":"Averigüen qué hacen hoy, incluso si no usan tecnología.","SUPUESTOS":"Distingan datos, opiniones e hipótesis."}[etapa])
    with st.form(f"m01_5_{etapa}_{equipo_id}"):
        nuevos=[]
        for campo,pregunta in preguntas[etapa]:
            v=st.text_area(pregunta,value=str(_valor(alumno_id,equipo_id,etapa,campo)),height=125,disabled=bloqueado,key=f"m01_5_{equipo_id}_{etapa}_{campo}")
            nuevos.append((campo,"TEXTO_LARGO",v.strip()))
        guardar=st.form_submit_button("💾 Guardar trabajo del equipo",disabled=bloqueado,use_container_width=True,type="primary")
    if guardar:
        if not all(v for _,_,v in nuevos): st.error("Completen todos los campos de esta etapa."); return
        _guardar(alumno_id,equipo_id,etapa,nuevos)

def _evidenciar(alumno_id,equipo_id,bloqueado):
    st.write("Registren evidencias concretas: entrevistas, encuestas, observaciones o investigación de mercado. La primera es obligatoria; pueden añadir dos más.")
    metodos=dict(METODOS_EVIDENCIA)
    with st.form(f"m01_5_evidencias_{equipo_id}"):
        nuevas=[]
        for n in (1,2,3):
            actual=_valor(alumno_id,equipo_id,"EVIDENCIAR",f"evidencia_{n}",{})
            if not isinstance(actual,dict): actual={}
            st.markdown(f"**Evidencia {n}{' · obligatoria' if n==1 else ' · opcional'}**")
            obs=st.text_area("¿Qué descubrieron?",value=str(actual.get("observado", "")),key=f"m01_5_ev_obs_{equipo_id}_{n}",disabled=bloqueado)
            metodo=st.selectbox("Método",options=list(metodos),index=list(metodos).index(actual["metodo"]) if actual.get("metodo") in metodos else 0,format_func=lambda x:metodos[x],key=f"m01_5_ev_met_{equipo_id}_{n}",disabled=bloqueado)
            contexto=st.text_input("Fuente, lugar o fecha",value=str(actual.get("contexto","")),key=f"m01_5_ev_ctx_{equipo_id}_{n}",disabled=bloqueado)
            if obs.strip() or contexto.strip(): nuevas.append((f"evidencia_{n}","JSON",{"observado":obs.strip(),"metodo":metodo,"contexto":contexto.strip()}))
            st.divider()
        guardar=st.form_submit_button("💾 Guardar evidencias",disabled=bloqueado,use_container_width=True,type="primary")
    if guardar:
        if not any(c=="evidencia_1" for c,_,_ in nuevas): st.error("La primera evidencia es obligatoria."); return
        if any(not v["observado"] or not v["contexto"] for _,_,v in nuevas): st.error("Cada evidencia registrada necesita descripción y fuente."); return
        _guardar(alumno_id,equipo_id,"EVIDENCIAR",nuevas)

def _ficha(alumno_id,equipo_id,progreso,bloqueado):
    st.markdown(f"### {ENTREGABLE}")
    for titulo,etapa,campo in [("Problema en una oración","DESCUBRIR","problema_una_oracion"),("Descripción del problema","DESCUBRIR","descripcion_problema"),("Perfil inicial del cliente","PERFILAR","cliente_perfil"),("Contexto del cliente","PERFILAR","contexto_cliente"),("Cómo se resuelve hoy","INVESTIGAR","solucion_actual")]:
        st.markdown(f"**{titulo}**"); st.write(_valor(alumno_id,equipo_id,etapa,campo) or "Todavía sin información.")
    st.markdown("**Evidencias**")
    for n in (1,2,3):
        ev=_valor(alumno_id,equipo_id,"EVIDENCIAR",f"evidencia_{n}",{})
        if isinstance(ev,dict) and ev.get("observado"): st.write(f"{n}. {ev['observado']} · {dict(METODOS_EVIDENCIA).get(ev.get('metodo'),'')} · {ev.get('contexto','')}")
    for titulo,campo in [("Supuestos pendientes","supuestos_pendientes"),("Cómo comprobarlos","como_validarlos")]:
        st.markdown(f"**{titulo}**"); st.write(_valor(alumno_id,equipo_id,"SUPUESTOS",campo) or "Todavía sin información.")
    st.info("👨‍🏫 Professor Checkpoint · "+PROFESSOR_CHECKPOINT)
    estado=progreso["estado"]; vn=int(progreso.get("ultima_version_entregada") or 0)
    if estado=="PENDIENTE_REVISION": st.warning(f"📨 V{vn} enviada. Esperen la revisión docente."); return
    if estado=="APROBADA": st.success(f"🎉 Misión aprobada · V{vn}."); return
    cambios=None
    if estado=="REQUIERE_AJUSTES":
        cambios=st.text_area("¿Qué corrigieron desde la entrega anterior?",key=f"m01_5_cambios_{equipo_id}_{vn+1}")
    if st.button("📨 Enviar Ficha al profesor",disabled=bloqueado,use_container_width=True,type="primary",key=f"m01_5_entregar_{equipo_id}_{vn+1}"):
        if estado=="REQUIERE_AJUSTES" and not str(cambios or "").strip(): st.error("Expliquen los cambios para reenviar."); return
        try:
            resultado=entregar_mision_equipo(alumno_id=alumno_id,equipo_id=equipo_id,mision_id=MISION_ID,campos_requeridos=CAMPOS_REQUERIDOS_ENTREGA,descripcion_cambios=cambios,validador_mision=validar_entrega,sesion_id=st.session_state.get("sesion_id"))
        except (ValueError,RuntimeError) as exc:
            st.error(f"No se pudo enviar: {exc}"); return
        st.session_state[f"m01_5_flash_{equipo_id}"]=f"✓ Ficha V{resultado['version_entrega']} enviada y congelada."
        st.rerun()

def mostrar_mision_01_quinto(alumno,*,modo_demo=False,solo_lectura=False):
    alumno_id=alumno["alumno_id"]
    st.markdown(f"## 🎯 Misión 01 · {TITULO}"); st.write(OBJETIVO); st.caption(INTRODUCCION)
    equipo=obtener_equipo_alumno(alumno_id)
    if equipo is None:
        st.warning("Esta misión es colaborativa: primero necesitás un equipo activo. Consultá al profesor.")
        return
    equipo_id=equipo["equipo_id"]
    st.markdown(f"**🏢 Equipo:** {equipo.get('nombre_equipo') or equipo_id}")
    progreso=obtener_progreso_equipo(alumno_id,equipo_id,MISION_ID)
    if progreso is None:
        st.info("La misión todavía no fue iniciada por este equipo.")
        if not solo_lectura and st.button("🚀 Iniciar Misión 01",key=f"m01_5_inicio_{equipo_id}",use_container_width=True):
            iniciar_mision_equipo(alumno_id=alumno_id,equipo_id=equipo_id,mision_id=MISION_ID,etapa_inicial="DESCUBRIR")
            st.rerun()
        return
    flash=st.session_state.pop(f"m01_5_flash_{equipo_id}",None)
    if flash: st.success(flash)
    estado=progreso["estado"]
    st.info({"EN_PROGRESO":"🟡 En progreso","PENDIENTE_REVISION":"🟠 Esperando revisión docente","REQUIERE_AJUSTES":"🔵 Requiere ajustes","APROBADA":"🟢 Aprobada"}.get(estado,estado))
    bloqueado=solo_lectura or estado in BLOQUEADOS
    clave=f"m01_5_etapa_{equipo_id}"
    if clave not in st.session_state: st.session_state[clave]=progreso.get("etapa_actual") if progreso.get("etapa_actual") in ORDEN_ETAPAS else "DESCUBRIR"
    etapa=st.session_state[clave]
    idx=ORDEN_ETAPAS.index(etapa)
    st.progress((idx+1)/len(ORDEN_ETAPAS)); st.markdown(f"### {ETIQUETAS[etapa]} · paso {idx+1} de {len(ORDEN_ETAPAS)}")
    try:
        if etapa in ("DESCUBRIR","PERFILAR","INVESTIGAR","SUPUESTOS"): _formulario(alumno_id,equipo_id,etapa,bloqueado)
        elif etapa=="EVIDENCIAR": _evidenciar(alumno_id,equipo_id,bloqueado)
        else: _ficha(alumno_id,equipo_id,progreso,bloqueado)
    except ConflictoBorradorEquipoError:
        st.error("Otro integrante modificó el borrador. Actualicen la página y revisen antes de volver a guardar.")
    st.divider()
    a,b=st.columns(2)
    with a:
        if idx>0 and st.button("← "+ETIQUETAS[ORDEN_ETAPAS[idx-1]],key=f"m01_5_prev_{equipo_id}_{etapa}",use_container_width=True):
            st.session_state[clave]=ORDEN_ETAPAS[idx-1]; st.rerun()
    with b:
        if idx<len(ORDEN_ETAPAS)-1 and st.button(ETIQUETAS[ORDEN_ETAPAS[idx+1]]+" →",key=f"m01_5_next_{equipo_id}_{etapa}",use_container_width=True):
            st.session_state[clave]=ORDEN_ETAPAS[idx+1]; st.rerun()
