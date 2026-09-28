# ============================================================
# CSC LAB
# Motor de autenticación de alumnos
# ============================================================

import csv
import unicodedata
from pathlib import Path


# ============================================================
# UBICACIÓN DE LA BASE PRIVADA DE ALUMNOS
# ============================================================

RUTA_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_ALUMNOS = RUTA_PROYECTO / "data" / "alumnos.csv"


# ============================================================
# NORMALIZACIÓN DE TEXTO
# ============================================================

def normalizar_texto(texto):
    """
    Normaliza un texto para poder compararlo de manera robusta.

    Ejemplos:
        "Agustín"  -> "agustin"
        " AGUSTIN " -> "agustin"
        "Tomás"    -> "tomas"
    """

    texto = str(texto).strip().lower()

    texto = unicodedata.normalize(
        "NFD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    return texto


# ============================================================
# CARGA DE ALUMNOS
# ============================================================

def cargar_alumnos():
    """
    Lee la base privada data/alumnos.csv.

    Devuelve una lista de diccionarios.
    """

    if not RUTA_ALUMNOS.exists():
        raise FileNotFoundError(
            f"No se encontró la base de alumnos: {RUTA_ALUMNOS}"
        )

    with RUTA_ALUMNOS.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as archivo:

        lector = csv.DictReader(archivo)

        return list(lector)


# ============================================================
# BÚSQUEDA DE ALUMNO
# ============================================================

def buscar_alumno(curso_id, numero_lista):
    """
    Busca un alumno exclusivamente dentro del curso indicado.

    No utiliza nombres para realizar la búsqueda inicial.
    """

    alumnos = cargar_alumnos()

    for alumno in alumnos:

        if alumno["curso"] != curso_id:
            continue

        try:
            numero_alumno = int(alumno["numero_lista"])
        except (ValueError, TypeError):
            continue

        if numero_alumno == int(numero_lista):
            return alumno

    return None


# ============================================================
# VALIDACIÓN DE IDENTIDAD
# ============================================================

def validar_alumno(curso_id, numero_lista, nombre_ingresado):
    """
    Valida la identidad mediante:

        curso
        + número de lista
        + nombre

    Devuelve el diccionario del alumno si la identidad
    es correcta.

    Devuelve None si la validación falla.
    """

    if not curso_id:
        return None

    if numero_lista is None:
        return None

    if not nombre_ingresado:
        return None

    try:
        numero_lista = int(numero_lista)
    except (ValueError, TypeError):
        return None

    alumno = buscar_alumno(
        curso_id,
        numero_lista,
    )

    if alumno is None:
        return None

    activo = normalizar_texto(
        alumno.get("activo", "")
    )

    if activo not in ("true", "1", "si", "sí"):
        return None

    nombre_real = normalizar_texto(
        alumno["nombre"]
    )

    nombre_escrito = normalizar_texto(
        nombre_ingresado
    )

    if nombre_real != nombre_escrito:
        return None

    return alumno

def obtener_alumno_por_id(alumno_id):
    """
    Busca un alumno utilizando su identificador
    interno de CSC Lab.
    """

    alumnos = cargar_alumnos()

    for alumno in alumnos:

        if alumno["alumno_id"] == alumno_id:
            return alumno

    return None
