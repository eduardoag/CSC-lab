from pathlib import Path
import tomllib

import psycopg


RUTA_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_SECRETS = RUTA_PROYECTO / ".streamlit" / "secrets.toml"


def cargar_configuracion():
    with RUTA_SECRETS.open("rb") as archivo:
        secretos = tomllib.load(archivo)

    return secretos["connections"]["postgresql"]


def obtener_conexion():
    config = cargar_configuracion()

    return psycopg.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["database"],
        user=config["username"],
        password=config["password"],
        sslmode="require",
    )


def crear_esquema():
    print()
    print("=" * 60)
    print("CSC LAB - CREACIÓN DEL ESQUEMA POSTGRESQL")
    print("=" * 60)

    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:

            # ==================================================
            # ALUMNOS
            # ==================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS alumnos (
                    alumno_id TEXT PRIMARY KEY,
                    numero_lista INTEGER NOT NULL,
                    nombre TEXT NOT NULL,
                    apellido TEXT NOT NULL,
                    curso TEXT NOT NULL,
                    activo BOOLEAN NOT NULL DEFAULT TRUE,

                    UNIQUE (curso, numero_lista)
                );
                """
            )

            # ==================================================
            # EQUIPOS
            # ==================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS equipos (
                    equipo_id TEXT PRIMARY KEY,
                    curso TEXT NOT NULL,
                    numero_equipo INTEGER NOT NULL,
                    nombre_equipo TEXT NOT NULL,
                    nombre_empresa TEXT,
                    activo BOOLEAN NOT NULL DEFAULT TRUE,

                    UNIQUE (curso, numero_equipo)
                );
                """
            )

            # ==================================================
            # MIEMBROS DE EQUIPO
            # ==================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS miembros_equipo (
                    id BIGSERIAL PRIMARY KEY,
                    equipo_id TEXT NOT NULL
                        REFERENCES equipos(equipo_id),

                    alumno_id TEXT NOT NULL
                        REFERENCES alumnos(alumno_id),

                    fecha_desde TIMESTAMPTZ
                        NOT NULL DEFAULT CURRENT_TIMESTAMP,

                    fecha_hasta TIMESTAMPTZ,

                    activo BOOLEAN NOT NULL DEFAULT TRUE
                );
                """
            )

            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    idx_alumno_equipo_activo
                ON miembros_equipo(alumno_id)
                WHERE activo = TRUE;
                """
            )

            # ==================================================
            # SESIONES
            # ==================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sesiones (
                    sesion_id TEXT PRIMARY KEY,

                    alumno_id TEXT NOT NULL
                        REFERENCES alumnos(alumno_id),

                    curso TEXT NOT NULL,

                    fecha DATE NOT NULL,

                    hora_inicio TIMESTAMPTZ NOT NULL,

                    ultima_actividad TIMESTAMPTZ NOT NULL,

                    hora_fin TIMESTAMPTZ,

                    segundos_activos INTEGER
                        NOT NULL DEFAULT 0,

                    estado TEXT
                        NOT NULL DEFAULT 'ACTIVA',

                    cierre_motivo TEXT
                );
                """
            )

            # ==================================================
            # ADHESIONES AL PROGRAMA
            # ==================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS adhesiones_programa (
                    alumno_id TEXT NOT NULL
                        REFERENCES alumnos(alumno_id),

                    programa TEXT NOT NULL,

                    version TEXT NOT NULL,

                    fecha_aceptacion TIMESTAMPTZ NOT NULL,

                    PRIMARY KEY (
                        alumno_id,
                        programa,
                        version
                    )
                );
                """
            )

        conexion.commit()

    print()
    print("✅ ESQUEMA CREADO CORRECTAMENTE")
    print()


if __name__ == "__main__":
    crear_esquema()
