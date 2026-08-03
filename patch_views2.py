import re

with open('Pilapp/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update line 227 (cambiar_turnos_paquete_datos)
old_1 = """                dia, hora = turno_str.split(' ')
                hora_obj = datetime.strptime(hora, "%H:%M").time()
                turno_obj = Turno.objects.get(dia=dia, horario=hora_obj, disciplina='Reformer')"""
new_1 = """                parts = turno_str.split(' ')
                dia = parts[0]
                hora = parts[1]
                disciplina = parts[2] if len(parts) > 2 else 'Reformer'
                hora_obj = datetime.strptime(hora, "%H:%M").time()
                turno_obj = Turno.objects.get(dia=dia, horario=hora_obj, disciplina=disciplina)"""
content = content.replace(old_1, new_1)

# 2. Update line 1629 (registrar_alumno_datos)
old_2 = """                # Viene desde el bot (string como "Jueves 19:30")
                dia, horario = turno_str.split()
                # Bot solo soporta Reformer por defecto
                turno = Turno.objects.get(dia=dia, horario=horario, disciplina='Reformer')"""
new_2 = """                # Viene desde el bot (string como "Jueves 19:30" o "Jueves 19:30 Mat")
                parts = turno_str.split()
                dia = parts[0]
                horario = parts[1]
                disciplina = parts[2] if len(parts) > 2 else 'Reformer'
                turno = Turno.objects.get(dia=dia, horario=horario, disciplina=disciplina)"""
content = content.replace(old_2, new_2)

# 3. Update verificar_turno
old_3 = """            dia = data.get("dia")  # Ejemplo: "Lunes"
            horario = data.get("horario")  # Ejemplo: "07:00"

            if not dia or not horario:
                return JsonResponse({"error": "Debes enviar 'dia' y 'horario'"}, status=400)

            try:
                turno = Turno.objects.get(dia=dia, horario=horario)"""
new_3 = """            dia = data.get("dia")  # Ejemplo: "Lunes"
            horario = data.get("horario")  # Ejemplo: "07:00"
            disciplina = data.get("disciplina", "Reformer")

            if not dia or not horario:
                return JsonResponse({"error": "Debes enviar 'dia' y 'horario'"}, status=400)

            try:
                turno = Turno.objects.get(dia=dia, horario=horario, disciplina=disciplina)"""
content = content.replace(old_3, new_3)

with open('Pilapp/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched Pilapp/views.py successfully.")
