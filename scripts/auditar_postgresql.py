import psycopg

from scripts.probar_postgresql import cargar_configuracion


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


def main():

    print()
    print("=" * 60)
    print("CSC LAB - AUDITORÍA DE DATOS")
    print("=" * 60)

    with conectar() as conexion:

        with conexion.cursor() as cursor:

            # ------------------------------------------
            # ALUMNOS POR CURSO
            # ------------------------------------------

            cursor.execute(
                """
                SELECT
                    curso,
                    COUNT(*)
                FROM alumnos
                WHERE activo = TRUE
                GROUP BY curso
                ORDER BY curso;
                """
            )

            alumnos_curso = cursor.fetchall()

            print()
            print("ALUMNOS ACTIVOS")
            print("-" * 30)

            total_alumnos = 0

            for curso, cantidad in alumnos_curso:

                print(
                    f"{curso:>2} : {cantidad}"
                )

                total_alumnos += cantidad

            print("-" * 30)
            print(
                f"TOTAL: {total_alumnos}"
            )

            # ------------------------------------------
            # EQUIPOS
            # ------------------------------------------

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM equipos
                WHERE activo = TRUE;
                """
            )

            total_equipos = cursor.fetchone()[0]

            print()
            print(
                f"EQUIPOS ACTIVOS: {total_equipos}"
            )

            # ------------------------------------------
            # MEMBRESÍAS
            # ------------------------------------------

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM miembros_equipo
                WHERE activo = TRUE;
                """
            )

            total_miembros = cursor.fetchone()[0]

            print(
                "MEMBRESÍAS ACTIVAS: "
                f"{total_miembros}"
            )

            # ------------------------------------------
            # DUPLICADOS
            # ------------------------------------------

            cursor.execute(
                """
                SELECT
                    alumno_id,
                    COUNT(*)
                FROM miembros_equipo
                WHERE activo = TRUE
                GROUP BY alumno_id
                HAVING COUNT(*) > 1;
                """
            )

            duplicados = cursor.fetchall()

            print(
                "MEMBRESÍAS DUPLICADAS: "
                f"{len(duplicados)}"
            )

            # ------------------------------------------
            # EQUIPOS Y TAMAÑOS
            # ------------------------------------------

            cursor.execute(
                """
                SELECT
                    e.curso,
                    e.numero_equipo,
                    COUNT(m.alumno_id)
                FROM equipos e

                LEFT JOIN miembros_equipo m
                    ON m.equipo_id =
                       e.equipo_id
                   AND m.activo = TRUE

                WHERE e.activo = TRUE

                GROUP BY
                    e.equipo_id,
                    e.curso,
                    e.numero_equipo

                ORDER BY
                    e.curso,
                    e.numero_equipo;
                """
            )

            print()
            print("EQUIPOS")
            print("-" * 30)

            for curso, numero, cantidad in cursor.fetchall():

                print(
                    f"{curso} · Equipo {numero}: "
                    f"{cantidad}"
                )

            # ------------------------------------------
            # SESIONES
            # ------------------------------------------

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM sesiones;
                """
            )

            sesiones = cursor.fetchone()[0]

            print()
            print(
                f"SESIONES PRODUCTIVAS: {sesiones}"
            )

            # ------------------------------------------
            # ADHESIONES
            # ------------------------------------------

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM adhesiones_programa;
                """
            )

            adhesiones = cursor.fetchone()[0]

            print(
                "ADHESIONES MIGRADAS: "
                f"{adhesiones}"
            )

            print()
            print("=" * 60)


if __name__ == "__main__":
    main()
