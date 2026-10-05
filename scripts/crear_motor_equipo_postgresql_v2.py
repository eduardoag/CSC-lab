"""
CSC Lab · Motor universal de misiones por equipo · V2

ESTADO
------
Archivo preparado para revisión final del diseño SQL.
NO ejecutar contra PostgreSQL productivo hasta aprobar esta V2.

Objetivo:
    Crear la infraestructura común para misiones grupales de 3.º y 5.º año,
    sin incorporar lógica específica de M01 ni de un curso particular.

Principios:
    - El producto construido pertenece al EQUIPO.
    - La acción pertenece al ALUMNO que la realizó.
    - El aprendizaje individual sigue perteneciendo al ALUMNO.
    - El borrador actual puede cambiar.
    - Las versiones consolidadas no se sobrescriben.
    - Cada entrega formal queda congelada como una Ficha/snapshot.
    - Cada Ficha recibe como máximo una revisión docente.
    - La edición colaborativa se prepara para concurrencia optimista.
    - El historial pedagógico no usa borrado en cascada.
    - NO_INICIADA se representa por ausencia de fila en progreso.

Crea:
    - respuestas_equipo_mision
    - versiones_respuesta_equipo_mision
    - progreso_equipo_misiones
    - fichas_equipo_mision
    - revisiones_docente_equipo

Amplía de forma compatible:
    - eventos_aprendizaje.equipo_id

Ejecución futura, SOLO después de revisión:
    python -m scripts.crear_motor_equipo_postgresql_v2
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

DECISIONES_DOCENTE = (
    "REQUIERE_AJUSTES",
    "APROBADA",
)


def _lista_sql(valores):
    return ", ".join(f"'{valor}'" for valor in valores)


def sentencias_migracion():
    """
    Devuelve las sentencias DDL de la migración.

    Se mantienen separadas para que el cambio de esquema pueda auditarse
    antes de ejecutarse.
    """

    tipos_respuesta = _lista_sql(TIPOS_RESPUESTA)
    estados_progreso = _lista_sql(ESTADOS_PROGRESO)
    origenes_version = _lista_sql(ORIGENES_VERSION)
    decisiones_docente = _lista_sql(DECISIONES_DOCENTE)

    return [
        # ==============================================================
        # 1. RESPUESTAS ACTUALES / BORRADORES DEL EQUIPO
        #
        # Una fila representa el estado editable actual de un campo.
        # La respuesta pertenece al equipo.
        # actualizado_por_alumno_id registra únicamente el actor de la
        # última escritura; no atribuye autoría intelectual ni mérito.
        # ==============================================================

        f"""
        CREATE TABLE IF NOT EXISTS respuestas_equipo_mision (
            respuesta_equipo_id BIGSERIAL PRIMARY KEY,

            equipo_id TEXT NOT NULL
                REFERENCES equipos(equipo_id)
                ON DELETE RESTRICT,

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

            actualizado_por_alumno_id TEXT NOT NULL
                REFERENCES alumnos(alumno_id)
                ON DELETE RESTRICT,

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
        # 2. VERSIONES HISTÓRICAS POR CAMPO
        #
        # Deliberadamente SIN ON DELETE CASCADE.
        # origen y actor son conceptos distintos. La aplicación decide
        # cuándo actor_alumno_id es obligatorio según la operación.
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
                )
        )
        """,

        # ==============================================================
        # 3. PROGRESO / MÁQUINA DE ESTADOS DEL EQUIPO
        #
        # NO_INICIADA no se almacena:
        # ausencia de fila = misión no iniciada.
        #
        # etapa_actual representa la etapa MÁS AVANZADA alcanzada,
        # no la única etapa editable.
        # ==============================================================

        f"""
        CREATE TABLE IF NOT EXISTS progreso_equipo_misiones (
            progreso_equipo_id BIGSERIAL PRIMARY KEY,

            equipo_id TEXT NOT NULL
                REFERENCES equipos(equipo_id)
                ON DELETE RESTRICT,

            curso TEXT NOT NULL,
            mision_id TEXT NOT NULL,

            estado TEXT NOT NULL,

            etapa_actual TEXT,

            iniciada_por_alumno_id TEXT NOT NULL
                REFERENCES alumnos(alumno_id)
                ON DELETE RESTRICT,

            fecha_inicio TIMESTAMPTZ NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            fecha_ultima_actividad TIMESTAMPTZ,

            fecha_envio TIMESTAMPTZ,

            fecha_revision TIMESTAMPTZ,

            ultima_version_entregada INTEGER NOT NULL DEFAULT 0
                CHECK (ultima_version_entregada >= 0),

            CONSTRAINT uq_progreso_equipo_mision
                UNIQUE (equipo_id, mision_id),

            CONSTRAINT ck_estado_progreso_equipo
                CHECK (
                    estado IN ({estados_progreso})
                )
        )
        """,

        # ==============================================================
        # 4. FICHAS / SNAPSHOTS COMPLETOS DE LAS ENTREGAS
        #
        # Cada envío formal genera una fila nueva.
        # descripcion_cambios describe la transición entre entregas:
        # V1 puede dejarla NULL; para V2+ la aplicación la exigirá.
        #
        # La aplicación NO implementará UPDATE ni DELETE de fichas.
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

            descripcion_cambios TEXT,

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
        # 5. REVISIONES DOCENTES
        #
        # Una revisión apunta a una Ficha concreta, por lo tanto queda
        # vinculada inequívocamente con equipo + misión + versión.
        #
        # No se crea docente_id todavía porque la arquitectura actual
        # autentica al docente mediante contraseña y no posee identidad
        # docente persistente.
        # ==============================================================

        f"""
        CREATE TABLE IF NOT EXISTS revisiones_docente_equipo (
            revision_docente_id BIGSERIAL PRIMARY KEY,

            ficha_equipo_id BIGINT NOT NULL
                REFERENCES fichas_equipo_mision(ficha_equipo_id)
                ON DELETE RESTRICT,

            decision TEXT NOT NULL,

            devolucion TEXT,

            fecha_revision TIMESTAMPTZ NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT uq_revision_docente_ficha
                UNIQUE (ficha_equipo_id),

            CONSTRAINT ck_decision_revision_docente
                CHECK (
                    decision IN ({decisiones_docente})
                )
        )
        """,

        # ==============================================================
        # 6. EVENTOS DE APRENDIZAJE
        #
        # alumno_id existente continúa representando al ACTOR.
        # equipo_id nullable permite identificar el objeto grupal afectado
        # sin romper eventos individuales existentes.
        #
        # No se fuerza una identidad ficticia de alumno para acciones del
        # docente. Las revisiones quedan auditadas en su tabla específica.
        # ==============================================================

        """
        ALTER TABLE eventos_aprendizaje
        ADD COLUMN IF NOT EXISTS equipo_id TEXT
            REFERENCES equipos(equipo_id)
            ON DELETE RESTRICT
        """,

        # ==============================================================
        # 7. ÍNDICES · RESPUESTAS
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
        # 8. ÍNDICES · PROGRESO
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
        # 9. ÍNDICES · FICHAS
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
        # 10. ÍNDICES · REVISIONES DOCENTES
        # ==============================================================

        """
        CREATE INDEX IF NOT EXISTS idx_revisiones_docente_fecha
            ON revisiones_docente_equipo(fecha_revision)
        """,

        # ==============================================================
        # 11. ÍNDICES · EVENTOS GRUPALES
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
              'fichas_equipo_mision',
              'revisiones_docente_equipo'
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
    print("=" * 76)
    print("CSC LAB · MOTOR UNIVERSAL DE MISIONES POR EQUIPO · V2")
    print("=" * 76)
    print()
    print("ADVERTENCIA:")
    print("Este script MODIFICA el esquema PostgreSQL.")
    print("Ejecutarlo solamente después de aprobar la revisión final de la V2.")
    print()

    crear_motor_equipo()

    tablas, eventos_tiene_equipo = verificar_motor_equipo()

    esperadas = {
        "respuestas_equipo_mision",
        "versiones_respuesta_equipo_mision",
        "progreso_equipo_misiones",
        "fichas_equipo_mision",
        "revisiones_docente_equipo",
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
    print("✓ revisiones_docente_equipo creada/verificada")
    print("✓ eventos_aprendizaje.equipo_id creado/verificado")
    print()
    print("✓ Estructura del motor universal creada")
    print("✓ No se insertaron respuestas ni progresos de alumnos")


if __name__ == "__main__":
    main()
