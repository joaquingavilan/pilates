import sys

def patch_views(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Fix at line 225
    content = content.replace(
        "                disciplina = parts[2] if len(parts) > 2 else 'Reformer'\n                hora_obj = datetime.strptime(hora, \"%H:%M\").time()",
        "                disciplina = parts[2] if len(parts) > 2 else 'Reformer'\n                disciplina = 'MAT' if disciplina.upper() == 'MAT' else disciplina.capitalize()\n                hora_obj = datetime.strptime(hora, \"%H:%M\").time()"
    )

    # 2. Fix at line 391
    content = content.replace(
        '            dia, hora = turno_str.rsplit(" ", 1)\n            turno_obj = Turno.objects.get(dia=dia, horario=hora)',
        '            parts = turno_str.split()\n            dia = parts[0]\n            hora = parts[1]\n            disciplina = parts[2] if len(parts) > 2 else \'Reformer\'\n            disciplina = \'MAT\' if disciplina.upper() == \'MAT\' else disciplina.capitalize()\n            turno_obj = Turno.objects.get(dia=dia, horario=hora, disciplina=disciplina)'
    )

    # 3. Fix at line 1631 (registrar_alumno_datos)
    content = content.replace(
        "                  disciplina = parts[2] if len(parts) > 2 else 'Reformer'\n                  turno = Turno.objects.get(dia=dia, horario=horario, disciplina=disciplina)",
        "                  disciplina = parts[2] if len(parts) > 2 else 'Reformer'\n                  disciplina = 'MAT' if disciplina.upper() == 'MAT' else disciplina.capitalize()\n                  turno = Turno.objects.get(dia=dia, horario=horario, disciplina=disciplina)"
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched successfully!")

if __name__ == "__main__":
    patch_views("C:/Users/jesus/Documents/pilates/Pilapp/views.py")
