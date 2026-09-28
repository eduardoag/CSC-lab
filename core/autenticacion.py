import unicodedata

from sqlalchemy import text

from core.base_datos import obtener_conexion


def normalizar_texto(texto):
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


def buscar_alumno(curso_id, numero_lista):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultado = sesion.execute(
            text(
                """
                SELECT
                    alumno_id,
                    numero_lista,
                    nombre,
                    apellido,
                    curso,
                    activo
                FROM alumnos
                WHERE curso = :curso
                  AND numero_lista = :numero
                LIMIT 1
                """
            ),
            {
                "curso": curso_id,
                "numero": int(numero_lista),
            },
        ).mappings().first()

    if resultado is None:
        return None

    return dict(resultado)


def validar_alumno(
    curso_id,
    numero_lista,
    nombre_ingresado,
):

    if (
        not curso_id
        or numero_lista is None
        or not nombre_ingresado
    ):
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

    if not alumno["activo"]:
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

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultado = sesion.execute(
            text(
                """
                SELECT
                    alumno_id,
                    numero_lista,
                    nombre,
                    apellido,
                    curso,
                    activo
                FROM alumnos
                WHERE alumno_id = :alumno_id
                LIMIT 1
                """
            ),
            {
                "alumno_id": alumno_id,
            },
        ).mappings().first()

    if resultado is None:
        return None

    return dict(resultado)
