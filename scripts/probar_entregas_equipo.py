from sqlalchemy import text
import core.entregas_equipo as entregas_modulo
from core.base_datos import obtener_conexion
from core.entregas_equipo import entregar_mision_equipo_en_sesion
from core.progreso_equipo import iniciar_mision_equipo_en_sesion
from core.respuestas_equipo import guardar_borrador_equipo_en_sesion

M="__TEST_ENTREGA_ATOMICA__"
REQ=({"etapa_id":"OBSERVAR","campo_id":"campo_a"},{"etapa_id":"FORMULAR","campo_id":"campo_b"})

def contar(s,t,e):
    if t=="versiones":
        return s.execute(text("""SELECT COUNT(*) FROM versiones_respuesta_equipo_mision v
        JOIN respuestas_equipo_mision r ON r.respuesta_equipo_id=v.respuesta_equipo_id
        WHERE r.equipo_id=:e AND r.mision_id=:m"""),{"e":e,"m":M}).scalar_one()
    tablas={"progreso":"progreso_equipo_misiones","respuestas":"respuestas_equipo_mision",
            "fichas":"fichas_equipo_mision","eventos":"eventos_aprendizaje"}
    return s.execute(text(f"SELECT COUNT(*) FROM {tablas[t]} WHERE equipo_id=:e AND mision_id=:m"),
                     {"e":e,"m":M}).scalar_one()

def preparar(s,c):
    iniciar_mision_equipo_en_sesion(s,c["alumno_id"],c["equipo_id"],M,"OBSERVAR")
    guardar_borrador_equipo_en_sesion(s,c["alumno_id"],c["equipo_id"],M,"OBSERVAR","campo_a","TEXTO","A")
    guardar_borrador_equipo_en_sesion(s,c["alumno_id"],c["equipo_id"],M,"FORMULAR","campo_b","TEXTO_LARGO","B")

def main():
    print("="*76); print("CSC LAB · PRUEBA ENTREGA ATÓMICA POR EQUIPO · ROLLBACK FINAL"); print("="*76)
    cx=obtener_conexion()
    with cx.session as s:
        c=s.execute(text("""SELECT a.alumno_id,a.curso,e.equipo_id FROM alumnos a
        JOIN miembros_equipo m ON m.alumno_id=a.alumno_id AND m.activo=TRUE
        JOIN equipos e ON e.equipo_id=m.equipo_id AND e.activo=TRUE
        WHERE a.activo=TRUE ORDER BY a.alumno_id LIMIT 1""")).mappings().first()
        if not c: raise RuntimeError("No hay candidato activo.")
        if contar(s,"progreso",c["equipo_id"]): raise RuntimeError("Hay residuos previos.")
        try:
            preparar(s,c)
            r=entregar_mision_equipo_en_sesion(s,c["alumno_id"],c["equipo_id"],M,REQ)
            assert r["version_entrega"]==1 and r["progreso"]["estado"]=="PENDIENTE_REVISION"
            assert contar(s,"versiones",c["equipo_id"])==2
            assert contar(s,"fichas",c["equipo_id"])==1
            assert contar(s,"eventos",c["equipo_id"])==1
            assert s.execute(text("SELECT COUNT(*) FROM respuestas_equipo_mision WHERE equipo_id=:e AND mision_id=:m AND version_actual=1"),
                             {"e":c["equipo_id"],"m":M}).scalar_one()==2
            print("✓ V1 consolidó respuestas, versiones, Ficha, progreso y evento.")
        finally: s.rollback()

    with cx.session as s:
        preparar(s,c)
        original=entregas_modulo.registrar_evento_en_sesion
        def fallo(*args,**kwargs): raise RuntimeError("Falla deliberada al final.")
        entregas_modulo.registrar_evento_en_sesion=fallo
        try:
            try:
                entregar_mision_equipo_en_sesion(s,c["alumno_id"],c["equipo_id"],M,REQ)
            except RuntimeError as exc:
                assert "Falla deliberada" in str(exc); s.rollback()
                print("✓ Falla deliberada provocada después de Ficha y cambio de estado.")
            else: raise AssertionError("La falla deliberada no se propagó.")
        finally: entregas_modulo.registrar_evento_en_sesion=original

    with cx.session as s:
        for t in ("progreso","respuestas","versiones","fichas","eventos"):
            assert contar(s,t,c["equipo_id"])==0
    print("✓ ROLLBACK eliminó versiones, Ficha, progreso, borradores y evento.")
    print("✓ Atomicidad demostrada: la entrega completa existe o no existe.")
    print("✓ Prueba finalizada correctamente.")

if __name__=="__main__": main()
