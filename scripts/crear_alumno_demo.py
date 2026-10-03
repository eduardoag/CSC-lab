import psycopg
import streamlit as st


def main():

    configuracion = st.secrets["connections"]["postgresql"]

    conexion = psycopg.connect(
        host=configuracion["host"],
        port=configuracion["port"],
        dbname=configuracion["database"],
        user=configuracion["username"],
        password=configuracion["password"],
    )

    try:

        with conexion:

            with conexion.cursor() as cursor:

                # ------------------------------------------------
                # 1. AGREGAR CLASIFICACIÓN
                # ------------------------------------------------

                cursor.execute("""
                    ALTER TABLE alumnos
                    ADD COLUMN IF NOT EXISTS tipo_alumno
                    VARCHAR(10)
                    NOT NULL
                    DEFAULT 'REAL';
                """)

                # ------------------------------------------------
                # 2. RESTRICCIÓN DE VALORES
                # ------------------------------------------------

                cursor.execute("""
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'alumnos_tipo_alumno_check';
                """)

                existe_constraint = cursor.fetchone()

                if existe_constraint is None:

                    cursor.execute("""
                        ALTER TABLE alumnos
                        ADD CONSTRAINT alumnos_tipo_alumno_check
                        CHECK (
                            tipo_alumno IN ('REAL', 'DEMO')
                        );
                    """)

                # ------------------------------------------------
                # 3. CREAR ALUMNO DEMO
                # ------------------------------------------------

                cursor.execute("""
                    SELECT alumno_id
                    FROM alumnos
                    WHERE alumno_id = 'CSC-DEMO-001';
                """)

                existe_demo = cursor.fetchone()

                if existe_demo is None:

                    cursor.execute("""
                        INSERT INTO alumnos (
                            alumno_id,
                            curso,
                            numero_lista,
                            nombre,
                            apellido,
                            activo,
                            tipo_alumno
                        )
                        VALUES (
                            'CSC-DEMO-001',
                            '3A',
                            0,
                            'Alumno',
                            'DEMO',
                            TRUE,
                            'DEMO'
                        );
                    """)

                    print("✓ Alumno DEMO creado.")

                else:

                    print("✓ Alumno DEMO ya existía.")

                # ------------------------------------------------
                # 4. AUDITORÍA
                # ------------------------------------------------

                cursor.execute("""
                    SELECT
                        tipo_alumno,
                        COUNT(*)
                    FROM alumnos
                    GROUP BY tipo_alumno
                    ORDER BY tipo_alumno;
                """)

                print("\nAlumnos por tipo:")

                for tipo, cantidad in cursor.fetchall():
                    print(f"  {tipo}: {cantidad}")

                cursor.execute("""
                    SELECT
                        alumno_id,
                        curso,
                        numero_lista,
                        nombre,
                        apellido,
                        activo,
                        tipo_alumno
                    FROM alumnos
                    WHERE alumno_id = 'CSC-DEMO-001';
                """)

                demo = cursor.fetchone()

                print("\nAlumno DEMO:")
                print(demo)

    finally:

        conexion.close()


if __name__ == "__main__":
    main()
