from sqlalchemy import text

from core.base_datos import obtener_conexion


def inicializar_equipos():
    """
    PostgreSQL ya posee el esquema.
    Se conserva esta función para mantener
    compatible app.py.
    """
    return


def obtener_equipo_alumno(alumno_id):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultado = sesion.execute(
            text(
                """
                SELECT
                    e.equipo_id,
                    e.curso,
                    e.numero_equipo,
                    e.nombre_equipo,
                    e.nombre_empresa
                FROM miembros_equipo AS m

                JOIN equipos AS e
                    ON e.equipo_id = m.equipo_id

                WHERE m.alumno_id = :alumno_id
                  AND m.activo = TRUE
                  AND e.activo = TRUE

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


def obtener_integrantes_equipo(equipo_id):

    conexion = obtener_conexion()

    with conexion.session as sesion:

        resultados = sesion.execute(
            text(
                """
                SELECT alumno_id
                FROM miembros_equipo
                WHERE equipo_id = :equipo_id
                  AND activo = TRUE
                ORDER BY alumno_id
                """
            ),
            {
                "equipo_id": equipo_id,
            },
        ).scalars().all()

    return list(resultados)
