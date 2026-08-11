import sys

def patch_views(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. buscar_turnos_disponibles definition
    content = content.replace(
        'def buscar_turnos_disponibles(dia, operador_hora=None, hora_referencia=None):',
        'def buscar_turnos_disponibles(dia, operador_hora=None, hora_referencia=None, disciplina="Reformer"):'
    )
    
    # Inside buscar_turnos_disponibles
    content = content.replace(
        '    filtros = {"dia": dia}\n\n    if operador_hora and hora_referencia:',
        '    filtros = {"dia": dia}\n    if disciplina:\n        filtros["disciplina"] = disciplina\n\n    if operador_hora and hora_referencia:'
    )
    content = content.replace(
        '                "lugares_disponibles": lugares_disponibles\n            })',
        '                "lugares_disponibles": lugares_disponibles,\n                "disciplina": turno.disciplina\n            })'
    )

    # 2. verificar_turno_a_partir_de
    content = content.replace(
        '            hora_minima = data.get("hora_minima")\n\n            if not hora_minima:',
        '            hora_minima = data.get("hora_minima")\n            disciplina = data.get("disciplina", "Reformer")\n\n            if not hora_minima:'
    )
    content = content.replace(
        '                turnos_disponibles = buscar_turnos_disponibles(dia_actual, operador_hora="gte", hora_referencia=hora_minima)',
        '                turnos_disponibles = buscar_turnos_disponibles(dia_actual, operador_hora="gte", hora_referencia=hora_minima, disciplina=disciplina)'
    )

    # 3. verificar_turno_antes_de
    content = content.replace(
        '            hora_maxima = data.get("hora_maxima")\n\n            if not dia or not hora_maxima:',
        '            hora_maxima = data.get("hora_maxima")\n            disciplina = data.get("disciplina", "Reformer")\n\n            if not dia or not hora_maxima:'
    )
    content = content.replace(
        '                turnos_disponibles = buscar_turnos_disponibles(dia_actual, operador_hora="lt", hora_referencia=hora_maxima)',
        '                turnos_disponibles = buscar_turnos_disponibles(dia_actual, operador_hora="lt", hora_referencia=hora_maxima, disciplina=disciplina)'
    )

    # 4. verificar_turno_manana
    content = content.replace(
        '            dia = data.get("dia")  # Opcional ahora\n\n            if dia:',
        '            dia = data.get("dia")  # Opcional ahora\n            disciplina = data.get("disciplina", "Reformer")\n\n            if dia:'
    )
    content = content.replace(
        '                turnos_disponibles = buscar_turnos_disponibles(dia_actual, operador_hora="lt", hora_referencia="12:00")',
        '                turnos_disponibles = buscar_turnos_disponibles(dia_actual, operador_hora="lt", hora_referencia="12:00", disciplina=disciplina)'
    )
    
    # 5. obtener_alumnos_turno
    content = content.replace(
        '            dia = data.get("dia")  # Ejemplo: "Martes"\n            horario = data.get("horario")  # Ejemplo: "18:00"\n\n            if not dia or not horario:',
        '            dia = data.get("dia")  # Ejemplo: "Martes"\n            horario = data.get("horario")  # Ejemplo: "18:00"\n            disciplina = data.get("disciplina", "Reformer")\n\n            if not dia or not horario:'
    )
    content = content.replace(
        '                  turno = Turno.objects.get(dia=dia, horario=horario)',
        '                  turno = Turno.objects.get(dia=dia, horario=horario, disciplina=disciplina)'
    )

    # 6. obtener_alumnos_clase
    content = content.replace(
        '            horario = data.get("horario")  # Ejemplo: "18:00"\n            fecha_str = data.get("fecha")\n\n            if not dia or not horario:',
        '            horario = data.get("horario")  # Ejemplo: "18:00"\n            fecha_str = data.get("fecha")\n            disciplina = data.get("disciplina", "Reformer")\n\n            if not dia or not horario:'
    )
    # The previous Turno replacement in #5 might have been unique or not. Let's make this one very specific.
    content = content.replace(
        '                turno = Turno.objects.get(dia=dia, horario=horario)\n            except Turno.DoesNotExist:',
        '                turno = Turno.objects.get(dia=dia, horario=horario, disciplina=disciplina)\n            except Turno.DoesNotExist:'
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched successfully!")

if __name__ == "__main__":
    patch_views("C:/Users/jesus/Documents/pilates/Pilapp/views.py")
