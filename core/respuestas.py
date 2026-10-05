import json

from sqlalchemy import text

from core.base_datos import obtener_conexion


TIPOS_RESPUESTA_VALIDOS = {
    "TEXTO",
    "TEXTO_LARGO",
    "OPCION",
    "MULTIOPCION",
    "NUMERO",
    "ESCALA",
    "BOOLEANO",
    "JSON",
}

ORIGENES_VALIDOS = {
    "ALUMNO",
    "DOCENTE",
    "SISTEMA",
    "IA_ASISTIDA",
}


def _normalizar_tipo(tipo_respuesta):
    tipo = str(tipo_respuesta).strip().upper()

    if tipo not in TIPOS_RESPUESTA_VALIDOS:
        raise ValueError(f"Tipo de respuesta no válido: {tipo_respuesta}")

    return tipo


def _normalizar_origen(origen):
    valor = str(origen).strip().upper()

    if valor not in ORIGENES_VALIDOS:
        raise ValueError(f"Origen no válido: {origen}")

    return valor


def _contenido_json(contenido):
    """
    Convierte valores Python a JSON válido para PostgreSQL JSONB.

    Ejemplos:
        "texto"              -> {"valor": "texto"}
        ["A", "B"]           -> {"valores": ["A", "B"]}
        {"valor": "..."}     -> se conserva
        True / 5 / 3.5       -> {"valor": ...}
    """
    if isinstance(contenido, dict):
        normalizado = contenido
    elif isinstance(contenido, (list, tuple)):
        normalizado = {"valores": list(contenido)}
    else:
        normalizado = {"valor": contenido}

    # Valida que el contenido sea serializable.
    json.dumps(normalizado, ensure_ascii=False)

    return normalizado


def obtener_respuesta(
    alumno_id,
    mision_id,
    etapa_id,
    campo_id,
):
    conexion = obtener_conexion()

    consulta = text(
        """
        SELECT
            respuesta_id,
            alumno_id,
            curso,
            mision_id,
            etapa_id,
            campo_id,
            tipo_respuesta,
            contenido_actual,
            version_actual,
            fecha_creacion,
            fecha_actualizacion
        FROM respuestas_mision
        WHERE alumno_id = :alumno_id
          AND mision_id = :mision_id
          AND etapa_id = :etapa_id
          AND campo_id = :campo_id
        LIMIT 1
        """
    )

    with conexion.session as sesion:
        resultado = sesion.execute(
            consulta,
            {
                "alumno_id": alumno_id,
                "mision_id": mision_id,
                "etapa_id": etapa_id,
                "campo_id": campo_id,
            },
        ).mappings().first()

    return dict(resultado) if resultado else None


def guardar_borrador(
    alumno_id,
    curso,
    mision_id,
    etapa_id,
    campo_id,
    tipo_respuesta,
    contenido,
):
    """
    Crea o actualiza el estado actual de un campo.

    IMPORTANTE:
    guardar un borrador NO crea una versión histórica.
    """
    tipo = _normalizar_tipo(tipo_respuesta)
    contenido_normalizado = _contenido_json(contenido)

    conexion = obtener_conexion()

    consulta = text(
        """
        INSERT INTO respuestas_mision (
            alumno_id,
            curso,
            mision_id,
            etapa_id,
            campo_id,
            tipo_respuesta,
            contenido_actual
        )
        VALUES (
            :alumno_id,
            :curso,
            :mision_id,
            :etapa_id,
            :campo_id,
            :tipo_respuesta,
            CAST(:contenido AS JSONB)
        )
        ON CONFLICT (
            alumno_id,
            mision_id,
            etapa_id,
            campo_id
        )
        DO UPDATE SET
            curso = EXCLUDED.curso,
            tipo_respuesta = EXCLUDED.tipo_respuesta,
            contenido_actual = EXCLUDED.contenido_actual,
            fecha_actualizacion = CURRENT_TIMESTAMP
        RETURNING
            respuesta_id,
            version_actual
        """
    )

    with conexion.session as sesion:
        try:
            resultado = sesion.execute(
                consulta,
                {
                    "alumno_id": alumno_id,
                    "curso": curso,
                    "mision_id": mision_id,
                    "etapa_id": etapa_id,
                    "campo_id": campo_id,
                    "tipo_respuesta": tipo,
                    "contenido": json.dumps(
                        contenido_normalizado,
                        ensure_ascii=False,
                    ),
                },
            ).mappings().one()

            sesion.commit()

        except Exception:
            sesion.rollback()
            raise

    return dict(resultado)


def consolidar_respuesta(
    alumno_id,
    mision_id,
    etapa_id,
    campo_id,
    origen="ALUMNO",
    motivo=None,
):
    """
    Consolida el borrador actual como una nueva versión histórica.

    La operación es atómica:
      1. bloquea la respuesta actual;
      2. calcula la siguiente versión;
      3. inserta la versión histórica;
      4. actualiza version_actual.

    Las versiones anteriores nunca se modifican.
    """
    origen_normalizado = _normalizar_origen(origen)
    conexion = obtener_conexion()

    seleccionar = text(
        """
        SELECT
            respuesta_id,
            contenido_actual,
            version_actual
        FROM respuestas_mision
        WHERE alumno_id = :alumno_id
          AND mision_id = :mision_id
          AND etapa_id = :etapa_id
          AND campo_id = :campo_id
        FOR UPDATE
        """
    )

    insertar_version = text(
        """
        INSERT INTO versiones_respuesta_mision (
            respuesta_id,
            version,
            contenido,
            origen,
            motivo
        )
        VALUES (
            :respuesta_id,
            :version,
            CAST(:contenido AS JSONB),
            :origen,
            :motivo
        )
        RETURNING
            version_id,
            version,
            fecha_creacion
        """
    )

    actualizar = text(
        """
        UPDATE respuestas_mision
        SET
            version_actual = :version,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE respuesta_id = :respuesta_id
        """
    )

    parametros_busqueda = {
        "alumno_id": alumno_id,
        "mision_id": mision_id,
        "etapa_id": etapa_id,
        "campo_id": campo_id,
    }

    with conexion.session as sesion:
        try:
            respuesta = sesion.execute(
                seleccionar,
                parametros_busqueda,
            ).mappings().first()

            if respuesta is None:
                raise ValueError(
                    "No existe un borrador para consolidar."
                )

            nueva_version = int(respuesta["version_actual"]) + 1

            version_creada = sesion.execute(
                insertar_version,
                {
                    "respuesta_id": respuesta["respuesta_id"],
                    "version": nueva_version,
                    "contenido": json.dumps(
                        respuesta["contenido_actual"],
                        ensure_ascii=False,
                    ),
                    "origen": origen_normalizado,
                    "motivo": motivo,
                },
            ).mappings().one()

            sesion.execute(
                actualizar,
                {
                    "respuesta_id": respuesta["respuesta_id"],
                    "version": nueva_version,
                },
            )

            sesion.commit()

        except Exception:
            sesion.rollback()
            raise

    return dict(version_creada)



def consolidar_etapa(
    alumno_id,
    mision_id,
    etapa_id,
    campos_id,
    origen="ALUMNO",
    motivo=None,
):
    """
    Consolida varios campos de una etapa en UNA sola transacción.

    Garantías:
    - todos los borradores deben existir;
    - todos deben estar en la misma version_actual;
    - las filas se bloquean con FOR UPDATE;
    - o se crean TODAS las nuevas versiones, o no se crea ninguna;
    - version_actual se actualiza para todos los campos en el mismo commit.
    """
    origen_normalizado = _normalizar_origen(origen)

    campos = sorted({str(campo).strip() for campo in campos_id if str(campo).strip()})

    if not campos:
        raise ValueError("Indicá al menos un campo para consolidar.")

    conexion = obtener_conexion()

    seleccionar = text(
        """
        SELECT
            respuesta_id,
            campo_id,
            contenido_actual,
            version_actual
        FROM respuestas_mision
        WHERE alumno_id = :alumno_id
          AND mision_id = :mision_id
          AND etapa_id = :etapa_id
          AND campo_id = ANY(CAST(:campos AS TEXT[]))
        ORDER BY campo_id
        FOR UPDATE
        """
    )

    insertar_version = text(
        """
        INSERT INTO versiones_respuesta_mision (
            respuesta_id,
            version,
            contenido,
            origen,
            motivo
        )
        VALUES (
            :respuesta_id,
            :version,
            CAST(:contenido AS JSONB),
            :origen,
            :motivo
        )
        """
    )

    actualizar = text(
        """
        UPDATE respuestas_mision
        SET
            version_actual = :version,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE respuesta_id = :respuesta_id
        """
    )

    with conexion.session as sesion:
        try:
            respuestas = sesion.execute(
                seleccionar,
                {
                    "alumno_id": alumno_id,
                    "mision_id": mision_id,
                    "etapa_id": etapa_id,
                    "campos": campos,
                },
            ).mappings().all()

            encontradas = {fila["campo_id"] for fila in respuestas}
            faltantes = set(campos) - encontradas

            if faltantes:
                raise ValueError(
                    "Faltan borradores para consolidar: "
                    + ", ".join(sorted(faltantes))
                )

            versiones_actuales = {
                int(fila["version_actual"])
                for fila in respuestas
            }

            if len(versiones_actuales) != 1:
                raise ValueError(
                    "Los campos de la etapa no están alineados "
                    "en la misma versión."
                )

            nueva_version = versiones_actuales.pop() + 1

            for respuesta in respuestas:
                sesion.execute(
                    insertar_version,
                    {
                        "respuesta_id": respuesta["respuesta_id"],
                        "version": nueva_version,
                        "contenido": json.dumps(
                            respuesta["contenido_actual"],
                            ensure_ascii=False,
                        ),
                        "origen": origen_normalizado,
                        "motivo": motivo,
                    },
                )

            for respuesta in respuestas:
                sesion.execute(
                    actualizar,
                    {
                        "respuesta_id": respuesta["respuesta_id"],
                        "version": nueva_version,
                    },
                )

            sesion.commit()

        except Exception:
            sesion.rollback()
            raise

    return {
        "version": nueva_version,
        "campos_consolidados": len(respuestas),
        "campos_id": [fila["campo_id"] for fila in respuestas],
    }

def obtener_historial(
    alumno_id,
    mision_id,
    etapa_id,
    campo_id,
):
    conexion = obtener_conexion()

    consulta = text(
        """
        SELECT
            v.version_id,
            v.version,
            v.contenido,
            v.origen,
            v.motivo,
            v.fecha_creacion
        FROM versiones_respuesta_mision AS v
        JOIN respuestas_mision AS r
          ON r.respuesta_id = v.respuesta_id
        WHERE r.alumno_id = :alumno_id
          AND r.mision_id = :mision_id
          AND r.etapa_id = :etapa_id
          AND r.campo_id = :campo_id
        ORDER BY v.version ASC, v.version_id ASC
        """
    )

    with conexion.session as sesion:
        resultados = sesion.execute(
            consulta,
            {
                "alumno_id": alumno_id,
                "mision_id": mision_id,
                "etapa_id": etapa_id,
                "campo_id": campo_id,
            },
        ).mappings().all()

    return [dict(fila) for fila in resultados]
