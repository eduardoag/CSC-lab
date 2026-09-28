from pathlib import Path
import tomllib

import psycopg


RUTA_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_SECRETS = RUTA_PROYECTO / ".streamlit" / "secrets.toml"


def cargar_configuracion():
    with RUTA_SECRETS.open("rb") as archivo:
        secretos = tomllib.load(archivo)

    return secretos["connections"]["postgresql"]


def main():
    print()
    print("=" * 60)
    print("CSC LAB - PRUEBA DE POSTGRESQL")
    print("=" * 60)

    config = cargar_configuracion()

    print()
    print("Intentando conectar con Supabase...")

    with psycopg.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["database"],
        user=config["username"],
        password=config["password"],
        sslmode="require",
    ) as conexion:

        with conexion.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    current_database(),
                    current_user,
                    version();
                """
            )

            base, usuario, version = cursor.fetchone()

    print()
    print("✅ CONEXIÓN EXITOSA")
    print()
    print(f"Base de datos : {base}")
    print(f"Usuario       : {usuario}")
    print(f"PostgreSQL    : {version}")
    print()


if __name__ == "__main__":
    main()
