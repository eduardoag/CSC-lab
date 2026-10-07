"""
CSC Lab · 3.º año · Misión 01 — ENCONTRAR

Definición pedagógica ejecutable.

Este archivo NO escribe en PostgreSQL y NO contiene lógica del motor universal.
Describe la misión para que la interfaz y los validadores consuman una única
fuente de verdad.

Contrato pedagógico:
    Encontrar un problema real que merezca ser resuelto.
"""

MISION_ID = "M01"
TITULO = "ENCONTRAR"
OBJETIVO = "Encontrar un problema real que merezca ser resuelto."

INTRODUCCION = (
    "Antes de pensar productos, logos o aplicaciones, investiguen la realidad. "
    "Una empresa fuerte nace de comprender un problema mejor que los demás."
)

ORDEN_ETAPAS = (
    "PREPARARSE",
    "OBSERVAR",
    "COMPRENDER",
    "INVESTIGAR",
    "EVIDENCIAR",
    "FORMULAR",
    "FICHA",
)

PREGUNTAS_GUIA = (
    "¿Qué problema observamos?",
    "¿Quién lo experimenta?",
    "¿Cuándo y dónde ocurre?",
    "¿Con qué frecuencia?",
    "¿Cómo se resuelve hoy?",
    "¿Qué consecuencias produce?",
    "¿Qué evidencia tenemos de que existe?",
)

ENTREGABLE = "Ficha del Problema"

ENTREGABLE_ITEMS = (
    "Definición del problema en una oración",
    "Persona o grupo afectado",
    "Situación actual",
    "Al menos 3 evidencias u observaciones",
    "Primera hipótesis de oportunidad",
)

PROFESSOR_CHECKPOINT = (
    "El equipo no avanza a la solución hasta poder explicar el problema "
    "con claridad y aportar evidencia de que no es una invención del grupo."
)

# ---------------------------------------------------------------------------
# PREPARARSE · actividad complementaria INDIVIDUAL
# No integra la Ficha del Problema y no bloquea la entrega grupal.
# ---------------------------------------------------------------------------

CASOS_PREPARARSE = (
    {
        "campo_id": "caso_a",
        "titulo": "Caso A",
        "texto": (
            "Los alumnos olvidan frecuentemente las fechas de entrega "
            "de sus trabajos."
        ),
    },
    {
        "campo_id": "caso_b",
        "titulo": "Caso B",
        "texto": (
            "Necesitamos una aplicación que envíe recordatorios "
            "de las tareas."
        ),
    },
    {
        "campo_id": "caso_c",
        "titulo": "Caso C",
        "texto": (
            "Muchas familias tiran alimentos porque no recuerdan "
            "qué tienen guardado."
        ),
    },
)

OPCIONES_PROBLEMA_SOLUCION = (
    "PROBLEMA",
    "SOLUCION_DISFRAZADA",
)

# ---------------------------------------------------------------------------
# CAMPOS GRUPALES
# Estos campos pertenecen al EQUIPO y forman el producto colaborativo.
# ---------------------------------------------------------------------------

CAMPOS_EQUIPO = (
    {
        "etapa_id": "OBSERVAR",
        "campo_id": "observacion_inicial",
        "tipo_respuesta": "TEXTO_LARGO",
        "obligatorio": True,
        "versionable": True,
        "pregunta": "¿Qué problema o situación real observaron?",
    },
    {
        "etapa_id": "OBSERVAR",
        "campo_id": "donde_ocurre",
        "tipo_respuesta": "TEXTO",
        "obligatorio": True,
        "versionable": True,
        "pregunta": "¿Dónde ocurre?",
    },
    {
        "etapa_id": "OBSERVAR",
        "campo_id": "cuando_ocurre",
        "tipo_respuesta": "TEXTO",
        "obligatorio": True,
        "versionable": True,
        "pregunta": "¿Cuándo ocurre?",
    },
    {
        "etapa_id": "COMPRENDER",
        "campo_id": "grupo_afectado",
        "tipo_respuesta": "TEXTO_LARGO",
        "obligatorio": True,
        "versionable": True,
        "pregunta": "¿A qué persona o grupo afecta?",
    },
    {
        "etapa_id": "COMPRENDER",
        "campo_id": "frecuencia",
        "tipo_respuesta": "OPCION",
        "obligatorio": True,
        "versionable": True,
        "pregunta": "¿Con qué frecuencia ocurre?",
    },
    {
        "etapa_id": "COMPRENDER",
        "campo_id": "como_averiguarlo",
        "tipo_respuesta": "TEXTO_LARGO",
        "obligatorio": False,
        "obligatorio_si": {
            "campo_id": "frecuencia",
            "valor": "TODAVIA_NO_SABEMOS",
        },
        "versionable": True,
        "pregunta": "Si todavía no lo saben, ¿cómo podrían averiguarlo?",
    },
    {
        "etapa_id": "INVESTIGAR",
        "campo_id": "solucion_actual",
        "tipo_respuesta": "TEXTO_LARGO",
        "obligatorio": True,
        "versionable": True,
        "pregunta": "¿Cómo se resuelve hoy?",
    },
    {
        "etapa_id": "INVESTIGAR",
        "campo_id": "consecuencias_tipos",
        "tipo_respuesta": "MULTIOPCION",
        "obligatorio": False,
        "versionable": True,
        "pregunta": "¿Qué tipos de consecuencias produce?",
    },
    {
        "etapa_id": "INVESTIGAR",
        "campo_id": "consecuencias_descripcion",
        "tipo_respuesta": "TEXTO_LARGO",
        "obligatorio": True,
        "versionable": True,
        "pregunta": "Expliquen con sus palabras qué consecuencias produce.",
    },
    {
        "etapa_id": "EVIDENCIAR",
        "campo_id": "evidencia_1",
        "tipo_respuesta": "JSON",
        "obligatorio": True,
        "versionable": True,
        "pregunta": "Evidencia u observación 1",
    },
    {
        "etapa_id": "EVIDENCIAR",
        "campo_id": "evidencia_2",
        "tipo_respuesta": "JSON",
        "obligatorio": True,
        "versionable": True,
        "pregunta": "Evidencia u observación 2",
    },
    {
        "etapa_id": "EVIDENCIAR",
        "campo_id": "evidencia_3",
        "tipo_respuesta": "JSON",
        "obligatorio": True,
        "versionable": True,
        "pregunta": "Evidencia u observación 3",
    },
    {
        "etapa_id": "FORMULAR",
        "campo_id": "problema_una_oracion",
        "tipo_respuesta": "TEXTO_LARGO",
        "obligatorio": True,
        "versionable": True,
        "pregunta": "Definan el problema en una sola oración.",
    },
    {
        "etapa_id": "FORMULAR",
        "campo_id": "hipotesis_oportunidad",
        "tipo_respuesta": "TEXTO_LARGO",
        "obligatorio": True,
        "versionable": True,
        "pregunta": "¿Cuál es su primera hipótesis de oportunidad?",
    },
)

# ---------------------------------------------------------------------------
# REFLEXIÓN INDIVIDUAL COMPLEMENTARIA
# No forma parte de la Ficha y NO bloquea la entrega del equipo.
# ---------------------------------------------------------------------------

REFLEXION_INDIVIDUAL = {
    "etapa_id": "CIERRE",
    "campo_id": "reflexion_individual",
    "tipo_respuesta": "TEXTO_LARGO",
    "pregunta": (
        "¿Qué descubriste durante esta misión que no pensabas al comenzar? "
        "¿Qué aportaste vos a la investigación de tu equipo?"
    ),
}

# ---------------------------------------------------------------------------
# OPCIONES DE APOYO PARA LA INTERFAZ
# ---------------------------------------------------------------------------

OPCIONES_FRECUENCIA = (
    ("MUY_FRECUENTE", "Muy frecuentemente"),
    ("FRECUENTE", "Frecuentemente"),
    ("A_VECES", "A veces"),
    ("POCO_FRECUENTE", "Poco frecuentemente"),
    ("TODAVIA_NO_SABEMOS", "Todavía no lo sabemos"),
)

OPCIONES_CONSECUENCIAS = (
    ("TIEMPO", "Pérdida de tiempo"),
    ("DINERO", "Pérdida de dinero o recursos"),
    ("SALUD_BIENESTAR", "Salud o bienestar"),
    ("AMBIENTE", "Impacto ambiental"),
    ("ORGANIZACION", "Problemas de organización"),
    ("APRENDIZAJE", "Dificultades de aprendizaje"),
    ("OTRA", "Otra"),
)

METODOS_EVIDENCIA = (
    ("OBSERVACION", "Lo observamos"),
    ("ENTREVISTA", "Entrevistamos a alguien"),
    ("ENCUESTA", "Hicimos una encuesta"),
    ("MEDICION", "Lo medimos"),
    ("REGISTRO", "Consultamos un registro"),
    ("OTRO", "Otro"),
)

# ---------------------------------------------------------------------------
# CONTRATO DE ENTREGA PARA core.entregas_equipo
# Sólo incluye campos obligatorios incondicionales.
# La condición de como_averiguarlo se valida con validador_mision.
# ---------------------------------------------------------------------------

CAMPOS_REQUERIDOS_ENTREGA = tuple(
    {
        "etapa_id": campo["etapa_id"],
        "campo_id": campo["campo_id"],
    }
    for campo in CAMPOS_EQUIPO
    if campo.get("obligatorio") is True
)

MAPA_CAMPOS = {
    (campo["etapa_id"], campo["campo_id"]): campo
    for campo in CAMPOS_EQUIPO
}


def campos_de_etapa(etapa_id):
    """Devuelve la definición de los campos grupales de una etapa."""
    return tuple(
        campo
        for campo in CAMPOS_EQUIPO
        if campo["etapa_id"] == etapa_id
    )


def _valor_snapshot(snapshot, etapa_id, campo_id):
    """Extrae el valor de un campo desde el snapshot del motor universal."""
    try:
        contenido = snapshot["etapas"][etapa_id][campo_id]["contenido"]
    except (KeyError, TypeError):
        return None

    if isinstance(contenido, dict) and set(contenido.keys()) == {"valor"}:
        return contenido["valor"]

    return contenido


def _tiene_texto(valor):
    return isinstance(valor, str) and bool(valor.strip())


def _validar_evidencia(valor, numero):
    if not isinstance(valor, dict):
        raise ValueError(
            f"La evidencia {numero} debe contener información estructurada."
        )

    observado = valor.get("observado")
    metodo = valor.get("metodo")
    contexto = valor.get("contexto")

    if not _tiene_texto(observado):
        raise ValueError(
            f"Completá qué observaron o averiguaron en la evidencia {numero}."
        )

    metodos_validos = {codigo for codigo, _ in METODOS_EVIDENCIA}
    if metodo not in metodos_validos:
        raise ValueError(
            f"Seleccioná cómo obtuvieron la evidencia {numero}."
        )

    if not _tiene_texto(contexto):
        raise ValueError(
            f"Indicá dónde o cuándo obtuvieron la evidencia {numero}."
        )


def validar_entrega(snapshot):
    """
    Reglas pedagógicas específicas de M01.

    El motor universal valida existencia/no-vacío de los campos requeridos.
    Aquí se mantienen únicamente reglas propias de ENCONTRAR.
    """
    frecuencia = _valor_snapshot(
        snapshot, "COMPRENDER", "frecuencia"
    )

    if frecuencia == "TODAVIA_NO_SABEMOS":
        como_averiguarlo = _valor_snapshot(
            snapshot, "COMPRENDER", "como_averiguarlo"
        )
        if not _tiene_texto(como_averiguarlo):
            raise ValueError(
                "Como todavía no conocen la frecuencia, expliquen "
                "cómo podrían averiguarla."
            )

    for numero in (1, 2, 3):
        evidencia = _valor_snapshot(
            snapshot, "EVIDENCIAR", f"evidencia_{numero}"
        )
        _validar_evidencia(evidencia, numero)

    problema = _valor_snapshot(
        snapshot, "FORMULAR", "problema_una_oracion"
    )
    if not _tiene_texto(problema):
        raise ValueError(
            "La definición del problema debe estar escrita en una oración."
        )

    oportunidad = _valor_snapshot(
        snapshot, "FORMULAR", "hipotesis_oportunidad"
    )
    if not _tiene_texto(oportunidad):
        raise ValueError(
            "Completen la primera hipótesis de oportunidad."
        )

    return True
