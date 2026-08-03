import re

with open('Pilapp/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update registrar_alumno_ocasional_datos
old = """    if not errores:
        # 🔑 Obtener turno
        try:
            turno = Turno.objects.get(dia=dia_turno, horario=data["hora_turno"])
        except Turno.DoesNotExist:
            errores.append(f"El turno {dia_turno} {data['hora_turno']} no existe.")"""
            
new = """    if not errores:
        # 🔑 Obtener turno
        try:
            disciplina = data.get("disciplina", "Reformer")
            turno = Turno.objects.get(dia=dia_turno, horario=data["hora_turno"], disciplina=disciplina)
        except Turno.DoesNotExist:
            errores.append(f"El turno {dia_turno} {data['hora_turno']} ({disciplina}) no existe.")"""

content = content.replace(old, new)

with open('Pilapp/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched Pilapp/views.py successfully.")
