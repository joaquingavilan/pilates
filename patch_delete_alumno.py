import re

with open('Pilapp/views_panel.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add ExAlumno to imports from models
if 'ExAlumno' not in content:
    content = content.replace('from .models import (', 'from .models import (\n    ExAlumno,')

# Find the block in delete_alumno
old = """    pago_ids = list(
        PagoAlumno.objects.filter(id_alumno_paquete_id__in=paquete_ids)
        .values_list("id_pago_id", flat=True)
        .distinct()
    )

    with transaction.atomic():
        # 1) Borrado principal (cascade elimina: AlumnoPaquete*, AlumnoClase*, AlumnoClaseOcasional, PagoAlumno, etc.)"""

new = """    pago_ids = list(
        PagoAlumno.objects.filter(id_alumno_paquete_id__in=paquete_ids)
        .values_list("id_pago_id", flat=True)
        .distinct()
    )

    # Capturar info para ExAlumno
    turnos_str_list = []
    paquetes_activos = AlumnoPaquete.objects.filter(id_alumno=alumno, estado='activo')
    for paq in paquetes_activos:
        for apt in paq.alumnopaqueteturno_set.all():
            turnos_str_list.append(f"{apt.id_turno.dia} {apt.id_turno.horario.strftime('%H:%M')} {apt.id_turno.disciplina}")
    
    horarios_str = ", ".join(turnos_str_list) if turnos_str_list else "Sin turnos"

    with transaction.atomic():
        ExAlumno.objects.create(
            nombre=persona.nombre if persona else "Desconocido",
            apellido=persona.apellido if persona else "Desconocido",
            telefono=telefono,
            horarios=horarios_str
        )

        # 1) Borrado principal (cascade elimina: AlumnoPaquete*, AlumnoClase*, AlumnoClaseOcasional, PagoAlumno, etc.)"""

content = content.replace(old, new)

with open('Pilapp/views_panel.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched Pilapp/views_panel.py successfully.")
