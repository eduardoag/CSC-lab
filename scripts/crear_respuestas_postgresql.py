from sqlalchemy import text

from core.base_datos import obtener_conexion


def crear_tablas_respuestas():
    """
    Crea la capa de persistencia de respuestas pedagógicas de CSC Lab.

    respuestas_mision:
        conserva el estado/borrador actual de cada campo.

    versiones_respuesta_mision:
        conserva versiones pedagógicamente consolidadas.
        Una versión consolidada nunca se sobrescribe.
    """

    conexion = obtener_conexion()

    sentencias = [
        """
        CREATE TABLE IF NOT EXISTS respuestas_mision (
            respuesta_id BIGSERIAL PRIMARY KEY,
            alumno_id TEXT NOT NULL REFERENCES alumnos(alumno_id),
            curso TEXT NOT NULL,
            mision_id TEXT NOT NULL,
            etapa_id TEXT NOT NULL,
            campo_id TEXT NOT NULL,
            tipo_respuesta TEXT NOT NULL,
            contenido_actual JSONB NOT NULL DEFAULT '{}'::jsonb,
            version_actual INTEGER NOT NULL DEFAULT 0
                CHECK (version_actual >= 0),
            fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT uq_respuesta_campo
                UNIQUE (alumno_id, mision_id, etapa_id, campo_id),

            CONSTRAINT ck_tipo_respuesta
                CHECK (
                    tipo_respuesta IN (
                        'TEXTO',
                        'TEXTO_LARGO',
                        'OPCION',
                        'MULTIOPCION',
                        'NUMERO',
                        'ESCALA',
                        'BOOLEANO',
                        'JSON'
                    )
                )
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS versiones_respuesta_mision (
            version_id BIGSERIAL PRIMARY KEY,
            respuesta_id BIGINT NOT NULL
                REFERENCES respuestas_mision(respuesta_id)
                ON DELETE CASCADE,
            version INTEGER NOT NULL CHECK (version >= 1),
            contenido JSONB NOT NULL,
            origen TEXT NOT NULL DEFAULT 'ALUMNO',
            motivo TEXT,
            fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT uq_version_respuesta
                UNIQUE (respuesta_id, version),

            CONSTRAINT ck_origen_version
                CHECK (
                    origen IN (
                        'ALUMNO',
                        'DOCENTE',
                        'SISTEMA',
                        'IA_ASISTIDA'
                    )
                )
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_respuestas_alumno
            ON respuestas_mision(alumno_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_respuestas_mision
            ON respuestas_mision(mision_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_respuestas_alumno_mision
            ON respuestas_mision(alumno_id, mision_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_versiones_respuesta
            ON versiones_respuesta_mision(respuesta_id, version)
        """,
    ]

    with conexion.session as sesion:
        try:
            for sentencia in sentencias:
                sesion.execute(text(sentencia))
            sesion.commit()
        except Exception:
            sesion.rollback()
            raise


def verificar_tablas_respuestas():
    conexion = obtener_conexion()

    consulta = text(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN (
              'respuestas_mision',
              'versiones_respuesta_mision'
          )
        ORDER BY table_name
        """
    )

    with conexion.session as sesion:
        tablas = sesion.execute(consulta).scalars().all()

    return list(tablas)


def main():
    print("CSC Lab · Migración de respuestas pedagógicas")
    print("--------------------------------------------")

    crear_tablas_respuestas()
    tablas = verificar_tablas_respuestas()

    esperadas = {
        "respuestas_mision",
        "versiones_respuesta_mision",
    }

    encontradas = set(tablas)

    if encontradas == esperadas:
        print("✓ respuestas_mision creada/verificada")
        print("✓ versiones_respuesta_mision creada/verificada")
        print("✓ Migración completada correctamente")
        print("✓ No se insertaron respuestas de alumnos")
    else:
        faltantes = esperadas - encontradas
        raise RuntimeError(
            f"La migración terminó, pero faltan tablas: {sorted(faltantes)}"
        )


if __name__ == "__main__":
    main()
