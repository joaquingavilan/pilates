import re

with open('Pilapp/views_panel.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_regulares = """    # Alumnos regulares (para la lista de abajo)
    alumnos_regulares = AlumnoClase.objects.filter(
        id_clase=clase,
        estado__in=['reservado', 'pendiente', 'recuperó', 'asistió', 'faltó']
    ).select_related(
        'id_alumno_paquete__id_alumno__id_persona'
    )"""

new_regulares = """    # Alumnos regulares (para la lista de abajo)
    alumnos_regulares = list(AlumnoClase.objects.filter(
        id_clase=clase,
        estado__in=['reservado', 'pendiente', 'recuperó', 'asistió', 'faltó']
    ).select_related(
        'id_alumno_paquete__id_alumno__id_persona'
    ))
    
    # Identificar alumnos nuevos (primer paquete y primera clase)
    from .models import AlumnoPaquete
    for ac in alumnos_regulares:
        ac.es_nuevo = False
        num_paquetes = AlumnoPaquete.objects.filter(id_alumno=ac.id_alumno_paquete.id_alumno).count()
        if num_paquetes == 1:
            primera_clase = AlumnoClase.objects.filter(
                id_alumno_paquete=ac.id_alumno_paquete
            ).exclude(estado__in=['canceló', 'reprogramó']).order_by('id_clase__fecha', 'id_clase__id_turno__horario').first()
            
            if primera_clase and primera_clase.id_clase == clase:
                ac.es_nuevo = True"""

content = content.replace(old_regulares, new_regulares)

with open('Pilapp/views_panel.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched views_panel.py successfully.")
