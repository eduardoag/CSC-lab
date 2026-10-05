"""
CSC Lab · Migración del motor universal de misiones por equipo

IMPORTANTE
----------
Este archivo está preparado para revisión arquitectónica antes de ejecutarse
contra PostgreSQL productivo.

Objetivo:
    Crear la infraestructura genérica que podrán reutilizar las misiones de
    3.º y 5.º año sin introducir lógica específica de M01, 3A, 3B, 5A o 5B.

Crea:
    - respuestas_equipo_mision
    - versiones_respuesta_equipo_mision
    - progreso_equipo_misiones
    - fichas_equipo_mision

Amplía de forma compatible:
    - eventos_aprendizaje.equipo_id

Principios:
    - El producto construido pertenece al EQUIPO.
    - La acción pertenece al ALUMNO que la realizó.
    - El aprendizaje individual sigue perteneciendo al ALUMNO.
    - Un borrador puede cambiar.
    - Una versión consolidada no se sobrescribe.
    - Una ficha enviada queda congelada como snapshot histórico.
    - La edición colaborativa usa concurrencia optimista.
    - No se elimina en cascada el historial pedagógico del equipo.

Ejecución futura, SOLO después de revisión:
    python -m scripts.crear_motor_equipo_postgresql
"""

from sqlalchemy import text

from core.base_datos import obtener_conexion


TIPOS_RESPUESTA = (
    "TEXTO",
    "TEXTO_LARGO",
    "OPCION",
    "MULTIOPCION",
    "NUMERO",
    "ESCALA",
    "BOOLEANO",
    "JSON",
)

ESTADOS_PROGRESO = (
    "NO_INICIADA",
    "EN_PROGRESO",
    "PENDIENTE_REVISION",
    "REQUIERE_AJUSTES",
    "APROBADA",
)

ORIGENES_VERSION = (
    "ALUMNO",
    "DOCENTE",
    "SISTEMA",
    "IA_ASISTIDA",
)


def _lista_sql(valores):
    return ", ".join(f"'{valor}'" for valor in valores)


def sentencias_migracion():
    """
    Devuelve las sentencias DDL de la migración.

    Mantenerlas separadas permite revisar con claridad qué cambia antes
    de ejecutar la migración.
    """

    tipos_respuesta = _lista_sql(TIPOS_RESPUESTA)
    estados_progreso = _lista_sql(ESTADOS_PROGRESO)
    origenes_version = _lista_sql(ORIGENES_VERSION)

    return [
        # ==============================================================
        # 1. RESPUESTAS ACTUALES / BORRADORES DEL EQUIPO
        # ==============================================================
        f"""
        CREATE TABLE IF NOT EXISTS respuestas_equipo_mision (
            respuesta_equipo_id BIGSERIAL PRIMARY KEY,

            equipo_id TEXT NOT NULL
                REFERENCES equipos(equipo_id),

            curso TEXT NOT NULL,
            mision_id TEXT NOT NULL,
            etapa_id TEXT NOT NULL,
            campo_id TEXT NOT NULL,
            tipo_respuesta TEXT NOT NULL,

            contenido_actual JSONB NOT NULL DEFAULT '{{}}'::jsonb,

            version_actual INTEGER NOT NULL DEFAULT 0
                CHECK (version_actual >= 0),

            revision_borrador INTEGER NOT NULL DEFAULT 0
                CHECK (revision_borrador >= 0),

            fecha_creacion TIMESTAMPTZ NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            fecha_actualizacion TIMESTAMPTZ NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT uq_respuesta_equipo_campo
                UNIQUE (
                    equipo_id,
                    mision_id,
                    etapa_id,
                    campo_id
                ),

            CONSTRAINT ck_tipo_respuesta_equipo
                CHECK (
                    tipo_respuesta IN ({tipos_respuesta})
                )
        )
        """,

        # ==============================================================
        # 2. VERSIONES INMUTABLES DE RESPUESTAS DEL EQUIPO
        #
        # Deliberadamente SIN ON DELETE CASCADE.
        # Una respuesta con historia no debe poder desaparecer arrastrando
        # silenciosamente sus versiones pedagógicas.
        # ==============================================================
        f"""
        CREATE TABLE IF NOT EXISTS versiones_respuesta_equipo_mision (
            version_equipo_id BIGSERIAL PRIMARY KEY,

            respuesta_equipo_id BIGINT NOT NULL
                REFERENCES respuestas_equipo_mision(respuesta_equipo_id)
                ON DELETE RESTRICT,

            version INTEGER NOT NULL
                CHECK (version >= 1),

            contenido JSONB NOT NULL,

            origen TEXT NOT NULL DEFAULT 'ALUMNO',

            actor_alumno_id TEXT
                REFERENCES alumnos(alumno_id)
                ON DELETE RESTRICT,

            motivo TEXT,

            fecha_creacion TIMESTAMPTZ NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT uq_version_respuesta_equipo
                UNIQUE (respuesta_equipo_id, version),

            CONSTRAINT ck_origen_version_equipo
                CHECK (
                    origen IN ({origenes_version})
                ),

            CONSTRAINT ck_actor_version_equipo
                CHECK (
                    (origen = 'ALUMNO' AND actor_alumno_id IS NOT NULL)
                    OR
                    (origen <> 'ALUMNO')
                )
        )
        """,

        # ==============================================================
        # 3. PROGRESO DE LA MISIÓN COMO PRODUCTO DEL EQUIPO
        # ==============================================================
        f"""
        CREATE TABLE IF NOT EXISTS progreso_equipo_misiones (
            progreso_equipo_id BIGSERIAL PRIMARY KEY,

            equipo_id TEXT NOT NULL
                REFERENCES equipos(equipo_id)
                ON DELETE RESTRICT,

            curso TEXT NOT NULL,
            mision_id TEXT NOT NULL,

            estado TEXT NOT NULL DEFAULT 'NO_INICIADA',

            etapa_actual TEXT,

            fecha_inicio TIMESTAMPTZ,
            fecha_ultima_actividad TIMESTAMPTZ,
            fecha_envio TIMESTAMPTZ,
            fecha_revision TIMESTAMPTZ,

            devolucion_docente TEXT,

            version_entrega_actual INTEGER NOT NULL DEFAULT 0
                CHECK (version_entrega_actual >= 0),

            CONSTRAINT uq_progreso_equipo_mision
                UNIQUE (equipo_id, mision_id),

            CONSTRAINT ck_estado_progreso_equipo
                CHECK (
                    estado IN ({estados_progreso})
                )
        )
        """,

        # ==============================================================
        # 4. FICHA / SNAPSHOT COMPLETO DE CADA ENTREGA
        #
        # Cada envío al docente produce una fila nueva. No se actualiza
        # una ficha anterior para representar una entrega posterior.
        # ==============================================================
        """
        CREATE TABLE IF NOT EXISTS fichas_equipo_mision (
            ficha_equipo_id BIGSERIAL PRIMARY KEY,

            equipo_id TEXT NOT NULL
                REFERENCES equipos(equipo_id)
                ON DELETE RESTRICT,

            curso TEXT NOT NULL,
            mision_id TEXT NOT NULL,

            version_entrega INTEGER NOT NULL
                CHECK (version_entrega >= 1),

            contenido JSONB NOT NULL,

            actor_alumno_id TEXT NOT NULL
                REFERENCES alumnos(alumno_id)
                ON DELETE RESTRICT,

            fecha_envio TIMESTAMPTZ NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT uq_ficha_equipo_mision_version
                UNIQUE (
                    equipo_id,
                    mision_id,
                    version_entrega
                )
        )
        """,

        # ==============================================================
        # 5. EVENTOS DE APRENDIZAJE
        #
        # alumno_id continúa siendo el ACTOR de la acción.
        # equipo_id identifica el OBJETO grupal afectado.
        #
        # Es nullable para preservar compatibilidad con todos los eventos
        # individuales ya existentes.
        # ==============================================================
        """
        ALTER TABLE eventos_aprendizaje
        ADD COLUMN IF NOT EXISTS equipo_id TEXT
            REFERENCES equipos(equipo_id)
            ON DELETE RESTRICT
        """,

        # ==============================================================
        # 6. ÍNDICES · RESPUESTAS DE EQUIPO
        # ==============================================================
        """
        CREATE INDEX IF NOT EXISTS idx_respuestas_equipo
            ON respuestas_equipo_mision(equipo_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_respuestas_equipo_mision
            ON respuestas_equipo_mision(equipo_id, mision_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_respuestas_equipo_curso_mision
            ON respuestas_equipo_mision(curso, mision_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_versiones_respuesta_equipo
            ON versiones_respuesta_equipo_mision(
                respuesta_equipo_id,
                version
            )
        """,

        # ==============================================================
        # 7. ÍNDICES · PROGRESO DE EQUIPO
        # ==============================================================
        """
        CREATE INDEX IF NOT EXISTS idx_progreso_equipo_curso_mision
            ON progreso_equipo_misiones(curso, mision_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_progreso_equipo_estado
            ON progreso_equipo_misiones(estado)
        """,

        # ==============================================================
        # 8. ÍNDICES · FICHAS HISTÓRICAS
        # ==============================================================
        """
        CREATE INDEX IF NOT EXISTS idx_fichas_equipo_mision
            ON fichas_equipo_mision(equipo_id, mision_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_fichas_equipo_fecha
            ON fichas_equipo_mision(fecha_envio)
        """,

        # ==============================================================
        # 9. ÍNDICES · EVENTOS GRUPALES
        # ==============================================================
        """
        CREATE INDEX IF NOT EXISTS idx_eventos_equipo
            ON eventos_aprendizaje(equipo_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_eventos_equipo_mision
            ON eventos_aprendizaje(equipo_id, mision_id)
            WHERE equipo_id IS NOT NULL
        """,
    ]


def crear_motor_equipo():
    """
    Ejecuta toda la migración en una única transacción.

    Si una sentencia falla, se realiza rollback de la migración completa.
    """

    conexion = obtener_conexion()

    with conexion.session as sesion:
        try:
            for sentencia in sentencias_migracion():
                sesion.execute(text(sentencia))

            sesion.commit()

        except Exception:
            sesion.rollback()
            raise


def verificar_motor_equipo():
    """
    Verificación estructural mínima posterior a la migración.

    No lee respuestas pedagógicas ni datos personales.
    """

    conexion = obtener_conexion()

    consulta_tablas = text(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN (
              'respuestas_equipo_mision',
              'versiones_respuesta_equipo_mision',
              'progreso_equipo_misiones',
              'fichas_equipo_mision'
          )
        ORDER BY table_name
        """
    )

    consulta_columna_eventos = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'eventos_aprendizaje'
              AND column_name = 'equipo_id'
        )
        """
    )

    with conexion.session as sesion:
        tablas = set(
            sesion.execute(consulta_tablas).scalars().all()
        )
        eventos_tiene_equipo = bool(
            sesion.execute(consulta_columna_eventos).scalar()
        )

    return tablas, eventos_tiene_equipo


def main():
    print()
    print("=" * 72)
    print("CSC LAB · MIGRACIÓN DEL MOTOR UNIVERSAL DE MISIONES POR EQUIPO")
    print("=" * 72)
    print()
    print("ADVERTENCIA:")
    print("Este script modifica el esquema PostgreSQL.")
    print("Ejecutarlo solamente después de la revisión arquitectónica.")
    print()

    crear_motor_equipo()

    tablas, eventos_tiene_equipo = verificar_motor_equipo()

    esperadas = {
        "respuestas_equipo_mision",
        "versiones_respuesta_equipo_mision",
        "progreso_equipo_misiones",
        "fichas_equipo_mision",
    }

    faltantes = esperadas - tablas

    if faltantes:
        raise RuntimeError(
            "La migración terminó, pero faltan tablas: "
            f"{sorted(faltantes)}"
        )

    if not eventos_tiene_equipo:
        raise RuntimeError(
            "La migración terminó, pero eventos_aprendizaje "
            "no contiene equipo_id."
        )

    print("✓ respuestas_equipo_mision creada/verificada")
    print("✓ versiones_respuesta_equipo_mision creada/verificada")
    print("✓ progreso_equipo_misiones creada/verificada")
    print("✓ fichas_equipo_mision creada/verificada")
    print("✓ eventos_aprendizaje.equipo_id creado/verificado")
    print()
    print("✓ MOTOR UNIVERSAL DE EQUIPOS CREADO")
    print("✓ No se insertaron respuestas ni progresos de alumnos")


if __name__ == "__main__":
    main()
