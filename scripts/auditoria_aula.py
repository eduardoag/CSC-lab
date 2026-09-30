from datetime import date
import psycopg

from scripts.probar_postgresql import cargar_configuracion


CURSOS = ("3A", "3B")


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


def minutos(segundos):
    if segundos is None:
        return 0.0
    return round(segundos / 60, 1)


def main():

    hoy = date.today()

    print()
    print("=" * 70)
    print("CSC LAB · PRIMERA AUDITORÍA DE AULA")
    print(f"Fecha: {hoy}")
    print("=" * 70)

    with conectar() as db:
        with db.cursor() as cur:

            # ==================================================
            # 1. MATRÍCULA Y ALUMNOS QUE INGRESARON
            # ==================================================

            print()
            print("1. PARTICIPACIÓN")
            print("-" * 70)

            for curso in CURSOS:

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM alumnos
                    WHERE curso = %s
                      AND activo = TRUE
                    """,
                    (curso,),
                )

                matricula = cur.fetchone()[0]

                cur.execute(
                    """
                    SELECT COUNT(DISTINCT alumno_id)
                    FROM sesiones
                    WHERE curso = %s
                      AND fecha = %s
                    """,
                    (curso, hoy),
                )

                ingresaron = cur.fetchone()[0]

                porcentaje = (
                    ingresaron / matricula * 100
                    if matricula
                    else 0
                )

                print(
                    f"{curso}: "
                    f"{ingresaron}/{matricula} alumnos "
                    f"({porcentaje:.1f} %)"
                )

            # ==================================================
            # 2. SESIONES
            # ==================================================

            print()
            print("2. SESIONES")
            print("-" * 70)

            cur.execute(
                """
                SELECT
                    curso,
                    COUNT(*) AS sesiones,
                    COUNT(DISTINCT alumno_id) AS alumnos,
                    COALESCE(SUM(segundos_activos), 0)
                FROM sesiones
                WHERE fecha = %s
                  AND curso IN ('3A', '3B')
                GROUP BY curso
                ORDER BY curso
                """,
                (hoy,),
            )

            for curso, sesiones, alumnos, segundos in cur.fetchall():

                print(
                    f"{curso}: "
                    f"{sesiones} sesiones · "
                    f"{alumnos} alumnos · "
                    f"{minutos(segundos)} min activos acumulados"
                )

            # ==================================================
            # 3. ESTADO DE LAS SESIONES
            # ==================================================

            print()
            print("3. ESTADO DE SESIONES")
            print("-" * 70)

            cur.execute(
                """
                SELECT
                    curso,
                    estado,
                    COALESCE(cierre_motivo, 'SIN_MOTIVO'),
                    COUNT(*)
                FROM sesiones
                WHERE fecha = %s
                  AND curso IN ('3A', '3B')
                GROUP BY
                    curso,
                    estado,
                    cierre_motivo
                ORDER BY curso, estado, cierre_motivo
                """,
                (hoy,),
            )

            filas = cur.fetchall()

            if not filas:
                print("Sin sesiones.")

            for curso, estado, motivo, cantidad in filas:
                print(
                    f"{curso}: {estado} · "
                    f"{motivo} → {cantidad}"
                )

            # ==================================================
            # 4. TIEMPO ACTIVO
            # ==================================================

            print()
            print("4. TIEMPO ACTIVO POR CURSO")
            print("-" * 70)

            cur.execute(
                """
                SELECT
                    curso,
                    ROUND(
                        AVG(segundos_activos) / 60.0,
                        1
                    ),
                    ROUND(
                        MIN(segundos_activos) / 60.0,
                        1
                    ),
                    ROUND(
                        MAX(segundos_activos) / 60.0,
                        1
                    )
                FROM sesiones
                WHERE fecha = %s
                  AND curso IN ('3A', '3B')
                GROUP BY curso
                ORDER BY curso
                """,
                (hoy,),
            )

            for curso, promedio, minimo, maximo in cur.fetchall():

                print(
                    f"{curso}: "
                    f"promedio {promedio} min · "
                    f"mín {minimo} · "
                    f"máx {maximo}"
                )

            # ==================================================
            # 5. ALUMNOS CON MÁS DE UNA SESIÓN
            # ==================================================

            print()
            print("5. REINGRESOS")
            print("-" * 70)

            cur.execute(
                """
                SELECT
                    curso,
                    alumno_id,
                    COUNT(*) AS cantidad
                FROM sesiones
                WHERE fecha = %s
                  AND curso IN ('3A', '3B')
                GROUP BY curso, alumno_id
                HAVING COUNT(*) > 1
                ORDER BY curso, cantidad DESC
                """,
                (hoy,),
            )

            reingresos = cur.fetchall()

            if not reingresos:
                print("✓ Ningún alumno generó múltiples sesiones.")
            else:
                for curso, alumno_id, cantidad in reingresos:
                    print(
                        f"{curso}: {alumno_id} → "
                        f"{cantidad} sesiones"
                    )

            # ==================================================
            # 6. CULTURA CONSTRUCTOR
            # ==================================================

            print()
            print("6. CULTURA CONSTRUCTOR")
            print("-" * 70)

            for curso in CURSOS:

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM alumnos a
                    JOIN adhesiones_programa ap
                      ON ap.alumno_id = a.alumno_id
                    WHERE a.curso = %s
                      AND a.activo = TRUE
                      AND ap.programa = 'constructor'
                      AND ap.version = 'v1'
                    """,
                    (curso,),
                )

                aceptaron = cur.fetchone()[0]

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM alumnos
                    WHERE curso = %s
                      AND activo = TRUE
                    """,
                    (curso,),
                )

                total = cur.fetchone()[0]

                print(
                    f"{curso}: "
                    f"{aceptaron}/{total} adhesiones"
                )

            # ==================================================
            # 7. EQUIPOS
            # ==================================================

            print()
            print("7. EQUIPOS")
            print("-" * 70)

            for curso in CURSOS:

                cur.execute(
                    """
                    SELECT COUNT(DISTINCT m.alumno_id)
                    FROM miembros_equipo m
                    JOIN alumnos a
                      ON a.alumno_id = m.alumno_id
                    WHERE a.curso = %s
                      AND a.activo = TRUE
                      AND m.activo = TRUE
                    """,
                    (curso,),
                )

                con_equipo = cur.fetchone()[0]

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM alumnos
                    WHERE curso = %s
                      AND activo = TRUE
                    """,
                    (curso,),
                )

                total = cur.fetchone()[0]

                print(
                    f"{curso}: "
                    f"{con_equipo} con equipo · "
                    f"{total - con_equipo} todavía sin equipo"
                )

            # ==================================================
            # 8. INTEGRIDAD
            # ==================================================

            print()
            print("8. CONTROL DE INTEGRIDAD")
            print("-" * 70)

            cur.execute(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT alumno_id
                    FROM miembros_equipo
                    WHERE activo = TRUE
                    GROUP BY alumno_id
                    HAVING COUNT(*) > 1
                ) x
                """
            )

            duplicados = cur.fetchone()[0]

            print(
                "Membresías activas duplicadas: "
                f"{duplicados}"
            )

            cur.execute(
                """
                SELECT COUNT(*)
                FROM sesiones s
                LEFT JOIN alumnos a
                  ON a.alumno_id = s.alumno_id
                WHERE a.alumno_id IS NULL
                """
            )

            sesiones_huerfanas = cur.fetchone()[0]

            print(
                "Sesiones sin alumno asociado: "
                f"{sesiones_huerfanas}"
            )

            print()
            print("=" * 70)
            print("FIN DE AUDITORÍA")
            print("=" * 70)
            print()


if __name__ == "__main__":
    main()
