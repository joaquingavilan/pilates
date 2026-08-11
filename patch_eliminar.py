import re

with open('Pilapp/views_panel.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = """        # Revert AlumnoPaquete status if it exists
        pago_alumnos = PagoAlumno.objects.filter(id_pago=pago)
        for pa in pago_alumnos:
            paquete = pa.id_alumno_paquete
            paquete.estado_pago = 'pendiente'
            paquete.save()"""

new_logic = """        # Revert AlumnoPaquete status if it exists
        pago_alumnos = PagoAlumno.objects.filter(id_pago=pago)
        for pa in pago_alumnos:
            paquete = pa.id_alumno_paquete
            if paquete:
                paquete.estado_pago = 'pendiente'
                paquete.save()"""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    with open('Pilapp/views_panel.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched panel_pago_eliminar successfully.")
else:
    print("Could not find old logic in views_panel.py")
