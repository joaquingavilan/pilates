import re
import sys

def patch_views(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. buscar_turnos_disponibles
    content = re.sub(
        r'def buscar_turnos_disponibles\(dia, operador_hora=None, hora_referencia=None\):',
        r'def buscar_turnos_disponibles(dia, operador_hora=None, hora_referencia=None, disciplina="Reformer"):',
        content
    )
    
    # Inside buscar_turnos_disponibles, add disciplina to filtros and the result append
    content = re.sub(
        r'(filtros = \{"dia": dia\})',
        r'\1\n    if disciplina:\n        filtros["disciplina"] = disciplina',
        content
    )
    content = re.sub(
        r'("lugares_disponibles": lugares_disponibles)',
        r'\1,\n                "disciplina": turno.disciplina',
        content
    )

    # 2. verificar_turno_a_partir_de
    content = re.sub(
        r'(hora_minima = data\.get\("hora_minima"\))',
        r'\1\n            disciplina = data.get("disciplina", "Reformer")',
        content
    )
    content = re.sub(
        r'(turnos_disponibles = buscar_turnos_disponibles\(dia_actual, operador_hora="gte", hora_referencia=hora_minima)\)',
        r'\1, disciplina=disciplina)',
        content
    )

    # 3. verificar_turno_antes_de
    content = re.sub(
        r'(hora_maxima = data\.get\("hora_maxima"\))',
        r'\1\n            disciplina = data.get("disciplina", "Reformer")',
        content
    )
    content = re.sub(
        r'(turnos_disponibles = buscar_turnos_disponibles\(dia_actual, operador_hora="lt", hora_referencia=hora_maxima)\)',
        r'\1, disciplina=disciplina)',
        content
    )

    # 4. verificar_turno_manana
    content = re.sub(
        r'(dia = data\.get\("dia"\)  # Opcional ahora)',
        r'\1\n            disciplina = data.get("disciplina", "Reformer")',
        content
    )
    content = re.sub(
        r'(turnos_disponibles = buscar_turnos_disponibles\(dia_actual, operador_hora="lt", hora_referencia="12:00"\))',
        r'turnos_disponibles = buscar_turnos_disponibles(dia_actual, operador_hora="lt", hora_referencia="12:00", disciplina=disciplina)',
        content
    )
    
    # 5. obtener_alumnos_turno
    content = re.sub(
        r'(horario = data\.get\("horario"\).*?)',
        r'\1\n            disciplina = data.get("disciplina", "Reformer")',
        content
    )
    content = re.sub(
        r'turno = Turno\.objects\.get\(dia=dia, horario=horario\)',
        r'turno = Turno.objects.get(dia=dia, horario=horario, disciplina=disciplina)',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched successfully!")

if __name__ == "__main__":
    patch_views("C:/Users/jesus/Documents/pilates/Pilapp/views.py")
