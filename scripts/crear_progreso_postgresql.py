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
                CREATE TABLE IF NOT EXISTS progreso_misiones (

                    progreso_id BIGSERIAL PRIMARY KEY,

                    alumno_id TEXT NOT NULL
                        REFERENCES alumnos(alumno_id),

                    curso TEXT NOT NULL,

                    mision_id TEXT NOT NULL,

                    estado TEXT NOT NULL
                        DEFAULT 'NO_INICIADA',

                    etapa_actual TEXT,

                    fecha_inicio TIMESTAMPTZ,

                    fecha_ultima_actividad TIMESTAMPTZ,

                    fecha_envio TIMESTAMPTZ,

                    fecha_revision TIMESTAMPTZ,

                    calificacion NUMERIC(5,2),

                    devolucion_docente TEXT,

                    UNIQUE (alumno_id, mision_id)
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_progreso_curso_mision
                ON progreso_misiones(curso, mision_id);
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_progreso_estado
                ON progreso_misiones(estado);
                """
            )

        db.commit()

    print()
    print("✅ TABLA DE PROGRESO CREADA")
    print()


if __name__ == "__main__":
    main()
