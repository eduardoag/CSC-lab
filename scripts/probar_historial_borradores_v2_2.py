"""
CSC Lab — Prueba controlada del historial de borradores V2.2

OBJETIVO
-------
Probar, exclusivamente sobre el equipo DEMO, cuatro garantías del motor:

1. Primera escritura:
   respuesta viva revision_borrador = 0 + historial B0.

2. Actualización válida:
   respuesta viva revision_borrador = 1 + historial B1.

3. Concurrencia optimista:
   un intento obsoleto con revision_esperada = 0 debe ser rechazado
   y NO debe crear B2 ni alterar la respuesta viva.

4. Rollback exterior:
   una escritura realizada con la función "_en_sesion" y luego revertida
   debe desaparecer tanto de respuestas_equipo_mision como del historial.

SEGURIDAD
---------
- Sólo trabaja con CSC-DEMO-E01.
- Sólo usa campos técnicos con prefijo __TEST_V22__.
- No modifica ni elimina respuestas pedagógicas reales de M01.
- La limpieza inicial/final afecta exclusivamente esos campos técnicos.
"""

from sqlalchemy import text

from core.base_datos import obtener_conexion
from core.respuestas_equipo import (
    ConflictoBorradorEquipoError,
    guardar_borrador_equipo,
    guardar_borrador_equipo_en_sesion,
)


EQUIPO_ID = "CSC-DEMO-E01"
ALUMNO_ID = "CSC-DEMO-001"
MISION_ID = "M01"
ETAPA_ID = "OBSERVAR"

CAMPO_PRINCIPAL = "__TEST_V22_HISTORIAL__"
CAMPO_ROLLBACK = "__TEST_V22_ROLLBACK__"


def limpiar_campos_tecnicos():
    """
    Elimina exclusivamente los datos técnicos creados por ESTE script.

    Primero borra historial y luego respuesta viva porque la FK del historial
    usa ON DELETE RESTRICT.
    """
    conexion = obtener_conexion()

    with conexion.session as sesion:
        try:
            ids = sesion.execute(
                text("""
                    SELECT respuesta_equipo_id
                    FROM respuestas_equipo_mision
                    WHERE equipo_id = :equipo_id
                      AND mision_id = :mision_id
                      AND etapa_id = :etapa_id
                      AND campo_id IN (:campo_principal, :campo_rollback)
                """),
                {
                    "equipo_id": EQUIPO_ID,
                    "mision_id": MISION_ID,
                    "etapa_id": ETAPA_ID,
                    "campo_principal": CAMPO_PRINCIPAL,
                    "campo_rollback": CAMPO_ROLLBACK,
                },
            ).scalars().all()

            if ids:
                sesion.execute(
                    text("""
                        DELETE FROM historial_borradores_equipo_mision
                        WHERE respuesta_equipo_id = ANY(:ids)
                    """),
                    {"ids": list(ids)},
                )

                sesion.execute(
                    text("""
                        DELETE FROM respuestas_equipo_mision
                        WHERE respuesta_equipo_id = ANY(:ids)
                    """),
                    {"ids": list(ids)},
                )

            sesion.commit()

        except Exception:
            sesion.rollback()
            raise


def leer_estado(campo_id):
    conexion = obtener_conexion()

    with conexion.session as sesion:
        viva = sesion.execute(
            text("""
                SELECT
                    respuesta_equipo_id,
                    revision_borrador,
                    contenido_actual,
                    actualizado_por_alumno_id
                FROM respuestas_equipo_mision
                WHERE equipo_id = :equipo_id
                  AND mision_id = :mision_id
                  AND etapa_id = :etapa_id
                  AND campo_id = :campo_id
            """),
            {
                "equipo_id": EQUIPO_ID,
                "mision_id": MISION_ID,
                "etapa_id": ETAPA_ID,
                "campo_id": campo_id,
            },
        ).mappings().first()

        if viva is None:
            return None, []

        historial = sesion.execute(
            text("""
                SELECT
                    revision_borrador,
                    contenido,
                    actor_alumno_id
                FROM historial_borradores_equipo_mision
                WHERE respuesta_equipo_id = :respuesta_equipo_id
                ORDER BY revision_borrador
            """),
            {"respuesta_equipo_id": viva["respuesta_equipo_id"]},
        ).mappings().all()

        return dict(viva), [dict(fila) for fila in historial]


def exigir(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)


def mostrar_estado(titulo, viva, historial):
    print()
    print("=" * 72)
    print(titulo)
    print("=" * 72)

    if viva is None:
        print("Respuesta viva: NO EXISTE")
    else:
        print(
            "Respuesta viva:",
            f"id={viva['respuesta_equipo_id']}",
            f"revision=B{viva['revision_borrador']}",
            f"contenido={viva['contenido_actual']}",
            f"actor={viva['actualizado_por_alumno_id']}",
        )

    if not historial:
        print("Historial: vacío")
    else:
        print("Historial:")
        for fila in historial:
            print(
                f"  B{fila['revision_borrador']}:",
                f"contenido={fila['contenido']}",
                f"actor={fila['actor_alumno_id']}",
            )


def prueba_b0():
    print("\n[1/4] Probando creación B0...")

    creada = guardar_borrador_equipo(
        alumno_id=ALUMNO_ID,
        equipo_id=EQUIPO_ID,
        mision_id=MISION_ID,
        etapa_id=ETAPA_ID,
        campo_id=CAMPO_PRINCIPAL,
        tipo_respuesta="TEXTO",
        contenido="Prueba V2.2 — B0",
        revision_esperada=None,
    )

    viva, historial = leer_estado(CAMPO_PRINCIPAL)
    mostrar_estado("RESULTADO B0", viva, historial)

    exigir(creada["revision_borrador"] == 0, "La creación no devolvió revisión 0.")
    exigir(viva is not None, "La respuesta viva B0 no existe.")
    exigir(viva["revision_borrador"] == 0, "La respuesta viva no quedó en B0.")
    exigir(len(historial) == 1, "B0 debe producir exactamente una fila histórica.")
    exigir(historial[0]["revision_borrador"] == 0, "La fila histórica no es B0.")
    exigir(
        viva["contenido_actual"] == historial[0]["contenido"],
        "El contenido vivo y B0 no coinciden.",
    )
    exigir(
        viva["actualizado_por_alumno_id"] == historial[0]["actor_alumno_id"],
        "El actor vivo y el actor de B0 no coinciden.",
    )

    print("OK — creación atómica B0 verificada.")


def prueba_b1():
    print("\n[2/4] Probando actualización B1...")

    actualizada = guardar_borrador_equipo(
        alumno_id=ALUMNO_ID,
        equipo_id=EQUIPO_ID,
        mision_id=MISION_ID,
        etapa_id=ETAPA_ID,
        campo_id=CAMPO_PRINCIPAL,
        tipo_respuesta="TEXTO",
        contenido="Prueba V2.2 — B1",
        revision_esperada=0,
    )

    viva, historial = leer_estado(CAMPO_PRINCIPAL)
    mostrar_estado("RESULTADO B1", viva, historial)

    exigir(actualizada["revision_borrador"] == 1, "La actualización no devolvió B1.")
    exigir(viva["revision_borrador"] == 1, "La respuesta viva no quedó en B1.")
    exigir(
        [fila["revision_borrador"] for fila in historial] == [0, 1],
        "El historial esperado es exactamente B0, B1.",
    )
    exigir(
        viva["contenido_actual"] == historial[-1]["contenido"],
        "El contenido vivo y B1 no coinciden.",
    )

    print("OK — actualización B1 verificada.")


def prueba_concurrencia_obsoleta():
    print("\n[3/4] Probando rechazo de escritura obsoleta...")

    conflicto_detectado = False

    try:
        guardar_borrador_equipo(
            alumno_id=ALUMNO_ID,
            equipo_id=EQUIPO_ID,
            mision_id=MISION_ID,
            etapa_id=ETAPA_ID,
            campo_id=CAMPO_PRINCIPAL,
            tipo_respuesta="TEXTO",
            contenido="ESTO NO DEBE PERSISTIR",
            revision_esperada=0,
        )
    except ConflictoBorradorEquipoError:
        conflicto_detectado = True

    exigir(conflicto_detectado, "El motor no rechazó la revisión obsoleta.")

    viva, historial = leer_estado(CAMPO_PRINCIPAL)
    mostrar_estado("RESULTADO CONCURRENCIA", viva, historial)

    exigir(viva["revision_borrador"] == 1, "El conflicto alteró la revisión viva.")
    exigir(
        viva["contenido_actual"].get("valor") == "Prueba V2.2 — B1",
        "El conflicto alteró el contenido vivo.",
    )
    exigir(
        [fila["revision_borrador"] for fila in historial] == [0, 1],
        "El conflicto dejó residuos en el historial.",
    )

    print("OK — conflicto obsoleto rechazado sin residuos.")


def prueba_rollback_exterior():
    print("\n[4/4] Probando rollback exterior...")

    conexion = obtener_conexion()

    with conexion.session as sesion:
        try:
            guardar_borrador_equipo_en_sesion(
                sesion=sesion,
                alumno_id=ALUMNO_ID,
                equipo_id=EQUIPO_ID,
                mision_id=MISION_ID,
                etapa_id=ETAPA_ID,
                campo_id=CAMPO_ROLLBACK,
                tipo_respuesta="TEXTO",
                contenido="ESTO DEBE DESAPARECER",
                revision_esperada=None,
            )

            # Simulamos que otra parte de una operación atómica falla después
            # del guardado. El rollback debe llevarse también respuesta + B0.
            raise RuntimeError("Fallo simulado posterior al guardado")

        except RuntimeError as exc:
            if str(exc) != "Fallo simulado posterior al guardado":
                sesion.rollback()
                raise
            sesion.rollback()

    viva, historial = leer_estado(CAMPO_ROLLBACK)
    mostrar_estado("RESULTADO ROLLBACK", viva, historial)

    exigir(viva is None, "El rollback dejó la respuesta viva.")
    exigir(len(historial) == 0, "El rollback dejó historial residual.")

    print("OK — rollback atómico verificado.")


def main():
    print("=" * 72)
    print("CSC LAB — PRUEBA CONTROLADA MOTOR V2.2")
    print(f"Equipo: {EQUIPO_ID}")
    print(f"Alumno actor: {ALUMNO_ID}")
    print("=" * 72)

    print("\nLimpiando únicamente residuos técnicos de pruebas anteriores...")
    limpiar_campos_tecnicos()

    try:
        prueba_b0()
        prueba_b1()
        prueba_concurrencia_obsoleta()
        prueba_rollback_exterior()

        print()
        print("=" * 72)
        print("TODAS LAS PRUEBAS V2.2 SUPERADAS")
        print("=" * 72)
        print("✓ B0 creado junto con la respuesta viva")
        print("✓ B1 creado junto con la actualización")
        print("✓ Escritura obsoleta rechazada sin residuos")
        print("✓ Rollback exterior revierte respuesta + historial")

    finally:
        print("\nLimpieza final de los campos técnicos...")
        limpiar_campos_tecnicos()
        print("Campos técnicos eliminados. Las respuestas pedagógicas no se tocaron.")


if __name__ == "__main__":
    main()
