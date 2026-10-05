"""
CSC Lab - Auditoría estructural PostgreSQL (SOLO LECTURA)

Objetivo:
    Inspeccionar el esquema real de las tablas pedagógicas antes de diseñar
    migraciones para misiones grupales de 3.º y 5.º año.

Este script:
    - NO crea tablas.
    - NO altera columnas.
    - NO inserta, actualiza ni elimina datos.
    - NO imprime filas de alumnos ni credenciales.
    - Fuerza la transacción a READ ONLY como defensa adicional.

Ejecutar desde la raíz del proyecto:
    python -m scripts.auditar_estructura_postgresql
"""

import psycopg

from scripts.probar_postgresql import cargar_configuracion


TABLAS_OBJETIVO = (
    "alumnos",
    "equipos",
    "miembros_equipo",
    "eventos_aprendizaje",
    "progreso_misiones",
    "respuestas_mision",
    "versiones_respuesta_mision",
)


def conectar():
    config = cargar_configuracion()

    return psycopg.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["database"],
        user=config["username"],
        password=config["password"],
        sslmode="require",
    )


def titulo(texto):
    print()
    print("=" * 88)
    print(texto)
    print("=" * 88)


def subtitulo(texto):
    print()
    print(texto)
    print("-" * 88)


def existe_tabla(cursor, tabla):
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = %s
        );
        """,
        (tabla,),
    )
    return cursor.fetchone()[0]


def auditar_columnas(cursor, tabla):
    subtitulo("COLUMNAS")

    cursor.execute(
        """
        SELECT
            ordinal_position,
            column_name,
            data_type,
            udt_name,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position;
        """,
        (tabla,),
    )

    filas = cursor.fetchall()

    if not filas:
        print("(sin columnas)")
        return

    for posicion, nombre, tipo, udt, nullable, default in filas:
        tipo_real = tipo if tipo != "USER-DEFINED" else udt
        print(
            f"{posicion:>2}. {nombre:<34} "
            f"{tipo_real:<24} "
            f"NULL={nullable:<3} "
            f"DEFAULT={default or '-'}"
        )


def auditar_restricciones(cursor, tabla):
    subtitulo("RESTRICCIONES · PK / UNIQUE / CHECK")

    cursor.execute(
        """
        SELECT
            c.conname,
            CASE c.contype
                WHEN 'p' THEN 'PRIMARY KEY'
                WHEN 'u' THEN 'UNIQUE'
                WHEN 'c' THEN 'CHECK'
                WHEN 'x' THEN 'EXCLUDE'
                ELSE c.contype::text
            END AS tipo,
            pg_get_constraintdef(c.oid, true) AS definicion
        FROM pg_constraint AS c
        JOIN pg_class AS t
          ON t.oid = c.conrelid
        JOIN pg_namespace AS n
          ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
          AND t.relname = %s
          AND c.contype IN ('p', 'u', 'c', 'x')
        ORDER BY
            CASE c.contype
                WHEN 'p' THEN 1
                WHEN 'u' THEN 2
                WHEN 'c' THEN 3
                ELSE 4
            END,
            c.conname;
        """,
        (tabla,),
    )

    filas = cursor.fetchall()

    if not filas:
        print("(sin restricciones PK/UNIQUE/CHECK)")
        return

    for nombre, tipo, definicion in filas:
        print(f"{tipo:<12} {nombre}")
        print(f"             {definicion}")


def auditar_claves_foraneas(cursor, tabla):
    subtitulo("CLAVES FORÁNEAS")

    cursor.execute(
        """
        SELECT
            c.conname,
            pg_get_constraintdef(c.oid, true)
        FROM pg_constraint AS c
        JOIN pg_class AS t
          ON t.oid = c.conrelid
        JOIN pg_namespace AS n
          ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
          AND t.relname = %s
          AND c.contype = 'f'
        ORDER BY c.conname;
        """,
        (tabla,),
    )

    filas = cursor.fetchall()

    if not filas:
        print("(sin claves foráneas)")
        return

    for nombre, definicion in filas:
        print(f"{nombre}")
        print(f"  {definicion}")


def auditar_indices(cursor, tabla):
    subtitulo("ÍNDICES")

    cursor.execute(
        """
        SELECT
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = %s
        ORDER BY indexname;
        """,
        (tabla,),
    )

    filas = cursor.fetchall()

    if not filas:
        print("(sin índices)")
        return

    for nombre, definicion in filas:
        print(nombre)
        print(f"  {definicion}")


def auditar_estadisticas(cursor, tabla):
    subtitulo("ESTADÍSTICAS ESTRUCTURALES")

    # El nombre de tabla nunca proviene del usuario: sólo de TABLAS_OBJETIVO.
    cursor.execute(f'SELECT COUNT(*) FROM public."{tabla}";')
    cantidad = cursor.fetchone()[0]

    print(f"Filas actuales: {cantidad}")


def auditar_tabla(cursor, tabla):
    titulo(f"TABLA: public.{tabla}")

    if not existe_tabla(cursor, tabla):
        print("⚠️  La tabla no existe.")
        return

    auditar_columnas(cursor, tabla)
    auditar_restricciones(cursor, tabla)
    auditar_claves_foraneas(cursor, tabla)
    auditar_indices(cursor, tabla)
    auditar_estadisticas(cursor, tabla)


def auditar_relacion_equipos(cursor):
    titulo("CHEQUEOS ESPECÍFICOS · EQUIPOS")

    if not (
        existe_tabla(cursor, "equipos")
        and existe_tabla(cursor, "miembros_equipo")
    ):
        print("No se puede auditar la relación porque falta alguna tabla.")
        return

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM equipos
        WHERE activo = TRUE;
        """
    )
    equipos_activos = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM miembros_equipo
        WHERE activo = TRUE;
        """
    )
    membresias_activas = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT alumno_id
            FROM miembros_equipo
            WHERE activo = TRUE
            GROUP BY alumno_id
            HAVING COUNT(*) > 1
        ) AS duplicados;
        """
    )
    alumnos_con_membresia_duplicada = cursor.fetchone()[0]

    print(f"Equipos activos: {equipos_activos}")
    print(f"Membresías activas: {membresias_activas}")
    print(
        "Alumnos con más de una membresía activa: "
        f"{alumnos_con_membresia_duplicada}"
    )


def main():
    titulo("CSC LAB · AUDITORÍA ESTRUCTURAL POSTGRESQL · SOLO LECTURA")

    print(
        "Propósito: capturar la estructura real antes de diseñar "
        "el esqueleto común de misiones de 3.º y 5.º año."
    )
    print("No se mostrarán datos personales de alumnos.")
    print("No se ejecutarán INSERT, UPDATE, DELETE, CREATE, ALTER ni DROP.")

    with conectar() as conexion:
        # Defensa adicional: PostgreSQL rechazará operaciones de escritura
        # dentro de esta transacción.
        conexion.autocommit = False

        with conexion.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY;")

            cursor.execute(
                """
                SELECT
                    current_database(),
                    current_schema(),
                    current_setting('server_version');
                """
            )
            database, schema, version = cursor.fetchone()

            subtitulo("ENTORNO")
            print(f"Base de datos: {database}")
            print(f"Esquema actual: {schema}")
            print(f"PostgreSQL: {version}")

            for tabla in TABLAS_OBJETIVO:
                auditar_tabla(cursor, tabla)

            auditar_relacion_equipos(cursor)

        # No hay cambios que conservar. Cerramos explícitamente con rollback.
        conexion.rollback()

    titulo("AUDITORÍA FINALIZADA")
    print("✓ Inspección completada.")
    print("✓ No se modificó la base de datos.")
    print("✓ Próximo paso: revisar esta salida antes de diseñar la migración.")


if __name__ == "__main__":
    main()
