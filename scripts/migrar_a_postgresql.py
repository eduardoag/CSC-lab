import csv
import sqlite3
from pathlib import Path

import psycopg

from scripts.probar_postgresql import cargar_configuracion


RUTA_PROYECTO = Path(__file__).resolve().parent.parent

RUTA_ALUMNOS = RUTA_PROYECTO / "data" / "alumnos.csv"
RUTA_SQLITE = RUTA_PROYECTO / "data" / "csc_lab.db"


def cargar_alumnos():
    if not RUTA_ALUMNOS.exists():
        raise FileNotFoundError(
            f"No existe {RUTA_ALUMNOS}"
        )

    with RUTA_ALUMNOS.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as archivo:

        return list(
            csv.DictReader(archivo)
        )


def cargar_sqlite():

    if not RUTA_SQLITE.exists():
        raise FileNotFoundError(
            f"No existe {RUTA_SQLITE}"
        )

    conexion = sqlite3.connect(RUTA_SQLITE)
    conexion.row_factory = sqlite3.Row

    return conexion


def conectar_postgresql():

    config = cargar_configuracion()

    return psycopg.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["database"],
        user=config["username"],
        password=config["password"],
        sslmode="require",
    )


def tabla_existe_sqlite(conexion, tabla):

    resultado = conexion.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (tabla,),
    ).fetchone()

    return resultado is not None


def migrar():

    print()
    print("=" * 65)
    print("CSC LAB - MIGRACIÓN A POSTGRESQL")
    print("=" * 65)

    alumnos = cargar_alumnos()

    print()
    print(
        f"Alumnos encontrados: {len(alumnos)}"
    )

    with cargar_sqlite() as sqlite_db:

        equipos = sqlite_db.execute(
            """
            SELECT
                equipo_id,
                curso,
                numero_equipo,
                nombre_equipo,
                nombre_empresa,
                activo
            FROM equipos
            ORDER BY curso, numero_equipo
            """
        ).fetchall()

        miembros = sqlite_db.execute(
            """
            SELECT
                equipo_id,
                alumno_id,
                fecha_desde,
                fecha_hasta,
                activo
            FROM miembros_equipo
            ORDER BY id
            """
        ).fetchall()

        if tabla_existe_sqlite(
            sqlite_db,
            "adhesiones_programa",
        ):
            adhesiones = sqlite_db.execute(
                """
                SELECT
                    alumno_id,
                    programa,
                    version,
                    fecha_aceptacion
                FROM adhesiones_programa
                """
            ).fetchall()
        else:
            adhesiones = []

        print(
            f"Equipos encontrados: {len(equipos)}"
        )

        print(
            f"Membresías encontradas: {len(miembros)}"
        )

        print(
            f"Adhesiones encontradas: {len(adhesiones)}"
        )

        print()
        print("Migrando...")

        with conectar_postgresql() as postgres:

            try:

                with postgres.cursor() as cursor:

                    # ==========================================
                    # ALUMNOS
                    # ==========================================

                    for alumno in alumnos:

                        activo = (
                            str(
                                alumno.get(
                                    "activo",
                                    "",
                                )
                            )
                            .strip()
                            .lower()
                            in (
                                "true",
                                "1",
                                "si",
                                "sí",
                            )
                        )

                        cursor.execute(
                            """
                            INSERT INTO alumnos (
                                alumno_id,
                                numero_lista,
                                nombre,
                                apellido,
                                curso,
                                activo
                            )
                            VALUES (
                                %s, %s, %s,
                                %s, %s, %s
                            )

                            ON CONFLICT (alumno_id)
                            DO UPDATE SET
                                numero_lista =
                                    EXCLUDED.numero_lista,
                                nombre =
                                    EXCLUDED.nombre,
                                apellido =
                                    EXCLUDED.apellido,
                                curso =
                                    EXCLUDED.curso,
                                activo =
                                    EXCLUDED.activo;
                            """,
                            (
                                alumno["alumno_id"],
                                int(
                                    alumno[
                                        "numero_lista"
                                    ]
                                ),
                                alumno["nombre"],
                                alumno["apellido"],
                                alumno["curso"],
                                activo,
                            ),
                        )

                    # ==========================================
                    # EQUIPOS
                    # ==========================================

                    for equipo in equipos:

                        cursor.execute(
                            """
                            INSERT INTO equipos (
                                equipo_id,
                                curso,
                                numero_equipo,
                                nombre_equipo,
                                nombre_empresa,
                                activo
                            )
                            VALUES (
                                %s, %s, %s,
                                %s, %s, %s
                            )

                            ON CONFLICT (equipo_id)
                            DO UPDATE SET
                                curso =
                                    EXCLUDED.curso,
                                numero_equipo =
                                    EXCLUDED.numero_equipo,
                                nombre_equipo =
                                    EXCLUDED.nombre_equipo,
                                nombre_empresa =
                                    EXCLUDED.nombre_empresa,
                                activo =
                                    EXCLUDED.activo;
                            """,
                            (
                                equipo["equipo_id"],
                                equipo["curso"],
                                equipo["numero_equipo"],
                                equipo["nombre_equipo"],
                                equipo["nombre_empresa"],
                                bool(equipo["activo"]),
                            ),
                        )

                    # ==========================================
                    # MEMBRESÍAS
                    # ==========================================

                    #
                    # Primera migración productiva:
                    # PostgreSQL reproduce exactamente
                    # el historial local de membresías.
                    #
                    cursor.execute(
                        """
                        DELETE FROM miembros_equipo;
                        """
                    )

                    for miembro in miembros:

                        cursor.execute(
                            """
                            INSERT INTO miembros_equipo (
                                equipo_id,
                                alumno_id,
                                fecha_desde,
                                fecha_hasta,
                                activo
                            )
                            VALUES (
                                %s, %s, %s, %s, %s
                            );
                            """,
                            (
                                miembro["equipo_id"],
                                miembro["alumno_id"],
                                miembro["fecha_desde"],
                                miembro["fecha_hasta"],
                                bool(miembro["activo"]),
                            ),
                        )

                    # ==========================================
                    # CULTURA CONSTRUCTOR
                    # ==========================================

                    for adhesion in adhesiones:

                        cursor.execute(
                            """
                            INSERT INTO adhesiones_programa (
                                alumno_id,
                                programa,
                                version,
                                fecha_aceptacion
                            )
                            VALUES (
                                %s, %s, %s, %s
                            )

                            ON CONFLICT (
                                alumno_id,
                                programa,
                                version
                            )
                            DO UPDATE SET
                                fecha_aceptacion =
                                    EXCLUDED.fecha_aceptacion;
                            """,
                            (
                                adhesion["alumno_id"],
                                adhesion["programa"],
                                adhesion["version"],
                                adhesion[
                                    "fecha_aceptacion"
                                ],
                            ),
                        )

                postgres.commit()

            except Exception:

                postgres.rollback()

                print()
                print(
                    "❌ ERROR: se realizó ROLLBACK."
                )
                print(
                    "PostgreSQL no quedó a medio migrar."
                )
                print()

                raise

    print()
    print("✅ MIGRACIÓN FINALIZADA")
    print()


if __name__ == "__main__":
    migrar()
