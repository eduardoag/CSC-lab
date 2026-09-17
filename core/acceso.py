# ============================================================
# CSC LAB
# Motor de control de acceso por horario
# ============================================================

from datetime import datetime, time
from zoneinfo import ZoneInfo

from config.horarios import HORARIOS, ZONA_HORARIA


def obtener_fecha_hora_actual():
    """
    Devuelve la fecha y hora actual en la zona horaria
    configurada para CSC Lab.
    """

    zona = ZoneInfo(ZONA_HORARIA)

    return datetime.now(zona)


def convertir_hora(texto_hora):
    """
    Convierte una hora escrita como '07:30'
    en un objeto datetime.time.
    """

    return datetime.strptime(
        texto_hora,
        "%H:%M"
    ).time()


def curso_esta_habilitado(curso_id, momento=None):
    """
    Determina si un curso está habilitado en un momento dado.

    Si no se proporciona un momento, utiliza la fecha y hora
    actuales de Tucumán.
    """

    if momento is None:
        momento = obtener_fecha_hora_actual()

    if curso_id not in HORARIOS:
        return False

    dia_semana = momento.weekday()
    hora_actual = momento.time()

    horarios_del_dia = HORARIOS[curso_id].get(
        dia_semana,
        []
    )

    for hora_inicio_texto, hora_fin_texto in horarios_del_dia:

        hora_inicio = convertir_hora(hora_inicio_texto)
        hora_fin = convertir_hora(hora_fin_texto)

        if hora_inicio <= hora_actual <= hora_fin:
            return True

    return False


def obtener_cursos_habilitados(momento=None):
    """
    Devuelve una lista con todos los cursos habilitados
    en el momento indicado.
    """

    if momento is None:
        momento = obtener_fecha_hora_actual()

    cursos_habilitados = []

    for curso_id in HORARIOS:

        if curso_esta_habilitado(
            curso_id,
            momento
        ):
            cursos_habilitados.append(curso_id)

    return cursos_habilitados
