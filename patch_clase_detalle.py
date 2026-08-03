import re

with open('Pilapp/views_panel.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_regulares = """    # Alumnos regulares (para la lista de abajo)
    alumnos_regulares = AlumnoClase.objects.filter(id_clase=clase).select_related(
        'id_alumno_paquete__id_alumno__id_persona'
    )"""

new_regulares = """    # Alumnos regulares (para la lista de abajo)
    alumnos_regulares = AlumnoClase.objects.filter(
        id_clase=clase,
        estado__in=['reservado', 'pendiente', 'recuperó', 'asistió', 'faltó']
    ).select_related(
        'id_alumno_paquete__id_alumno__id_persona'
    )"""

old_ocasionales = """    # Alumnos ocasionales (para la lista de abajo)
    alumnos_ocasionales = AlumnoClaseOcasional.objects.filter(id_clase=clase).select_related(
        'id_alumno__id_persona'
    )"""

new_ocasionales = """    # Alumnos ocasionales (para la lista de abajo)
    alumnos_ocasionales = AlumnoClaseOcasional.objects.filter(
        id_clase=clase,
        estado__in=['reservado', 'asistió', 'faltó']
    ).select_related(
        'id_alumno__id_persona'
    )"""

content = content.replace(old_regulares, new_regulares)
content = content.replace(old_ocasionales, new_ocasionales)

with open('Pilapp/views_panel.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched Pilapp/views_panel.py successfully.")
