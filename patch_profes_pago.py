import re

with open('Pilapp/views_panel.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = """            PagoAlumno.objects.create(
                id_pago=nuevo_pago,
                id_alumno_paquete=paquete_actual,
                observaciones=observaciones_pago
            )"""

new_logic = """            PagoAlumno.objects.create(
                id_pago=nuevo_pago,
                id_alumno=paquete_actual.id_alumno,
                id_alumno_paquete=paquete_actual,
                observaciones=observaciones_pago
            )"""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    with open('Pilapp/views_panel.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched profes_registrar_pago successfully.")
else:
    print("Could not find old logic for profes_registrar_pago.")
