"""CSC Lab · 5.º TIC · M01 DESCUBRIR UNA OPORTUNIDAD.
Contrato pedagógico independiente del motor universal V2.2.
"""
MISION_ID = "M01"
TITULO = "DESCUBRIR UNA OPORTUNIDAD"
OBJETIVO = "Encontrar un problema o necesidad concreta y reunir evidencia suficiente para demostrar que vale la pena investigarlo."
INTRODUCCION = "Antes de elegir software o IA, comprendan a las personas, investiguen cómo resuelven hoy el problema y comprueben sus hipótesis."
ORDEN_ETAPAS = ("DESCUBRIR", "PERFILAR", "INVESTIGAR", "EVIDENCIAR", "SUPUESTOS", "FICHA")
ENTREGABLE = "Ficha del problema y perfil inicial del cliente"
PROFESSOR_CHECKPOINT = "El problema está expresado con claridad, existe evidencia y no solamente opinión, y el equipo distingue problema de solución."
METODOS_EVIDENCIA = (("ENTREVISTA","Entrevista"),("ENCUESTA","Encuesta"),("OBSERVACION","Observación"),("INVESTIGACION_MERCADO","Investigación de mercado"))
CAMPOS_EQUIPO = (
    {"etapa_id":"DESCUBRIR","campo_id":"problema_una_oracion","tipo_respuesta":"TEXTO_LARGO","obligatorio":True},
    {"etapa_id":"DESCUBRIR","campo_id":"descripcion_problema","tipo_respuesta":"TEXTO_LARGO","obligatorio":True},
    {"etapa_id":"PERFILAR","campo_id":"cliente_perfil","tipo_respuesta":"TEXTO_LARGO","obligatorio":True},
    {"etapa_id":"PERFILAR","campo_id":"contexto_cliente","tipo_respuesta":"TEXTO_LARGO","obligatorio":True},
    {"etapa_id":"INVESTIGAR","campo_id":"solucion_actual","tipo_respuesta":"TEXTO_LARGO","obligatorio":True},
    {"etapa_id":"EVIDENCIAR","campo_id":"evidencia_1","tipo_respuesta":"JSON","obligatorio":True},
    {"etapa_id":"EVIDENCIAR","campo_id":"evidencia_2","tipo_respuesta":"JSON","obligatorio":False},
    {"etapa_id":"EVIDENCIAR","campo_id":"evidencia_3","tipo_respuesta":"JSON","obligatorio":False},
    {"etapa_id":"SUPUESTOS","campo_id":"supuestos_pendientes","tipo_respuesta":"TEXTO_LARGO","obligatorio":True},
    {"etapa_id":"SUPUESTOS","campo_id":"como_validarlos","tipo_respuesta":"TEXTO_LARGO","obligatorio":True},
)
CAMPOS_REQUERIDOS_ENTREGA = tuple({"etapa_id":c["etapa_id"],"campo_id":c["campo_id"]} for c in CAMPOS_EQUIPO if c["obligatorio"])

def _valor(snapshot, etapa, campo):
    try:
        v=snapshot["etapas"][etapa][campo]["contenido"]
        return v.get("valor") if isinstance(v,dict) and set(v)=={"valor"} else v
    except (KeyError,TypeError): return None

def validar_entrega(snapshot):
    evidencia=_valor(snapshot,"EVIDENCIAR","evidencia_1")
    if not isinstance(evidencia,dict): raise ValueError("Registren al menos una evidencia verificable.")
    if not str(evidencia.get("observado") or "").strip(): raise ValueError("Describan qué descubrieron en la evidencia 1.")
    if evidencia.get("metodo") not in dict(METODOS_EVIDENCIA): raise ValueError("Indiquen el método de la evidencia 1.")
    if not str(evidencia.get("contexto") or "").strip(): raise ValueError("Indiquen la fuente o contexto de la evidencia 1.")
    for n in (2,3):
        ev=_valor(snapshot,"EVIDENCIAR",f"evidencia_{n}")
        if ev is None: continue
        if not isinstance(ev,dict) or not all(str(ev.get(k) or "").strip() for k in ("observado","metodo","contexto")) or ev["metodo"] not in dict(METODOS_EVIDENCIA):
            raise ValueError(f"Completen la evidencia {n} o déjenla sin registrar.")
    return True
