from scripts.probar_postgresql import cargar_configuracion

import psycopg


def main():

    config = cargar_configuracion()

    with psycopg.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["database"],
        user=config["username"],
        password=config["password"],
        sslmode="require",
    ) as db:

        with db.cursor() as cur:

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS eventos_aprendizaje (

                    evento_id BIGSERIAL PRIMARY KEY,

                    alumno_id TEXT NOT NULL
                        REFERENCES alumnos(alumno_id),

                    sesion_id TEXT
                        REFERENCES sesiones(sesion_id),

                    curso TEXT NOT NULL,

                    mision_id TEXT NOT NULL,

                    etapa_id TEXT,

                    tipo_evento TEXT NOT NULL,

                    detalle JSONB,

                    fecha_hora TIMESTAMPTZ
                        NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_eventos_alumno
                ON eventos_aprendizaje(alumno_id);
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_eventos_mision
                ON eventos_aprendizaje(mision_id);
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_eventos_fecha
                ON eventos_aprendizaje(fecha_hora);
                """
            )

        db.commit()

    print()
    print("✅ BITÁCORA PEDAGÓGICA CREADA")
    print()


if __name__ == "__main__":
    main()
