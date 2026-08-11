import re

with open('Pilapp/views_panel.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = """    messages.success(request, "Pago registrado correctamente.")
    return redirect("panel_alumno_detalle", id_alumno=alumno.id_alumno)"""

new_logic = """    messages.success(request, "Pago registrado correctamente.")
    
    next_page = request.GET.get('next', 'detalle')
    if next_page == 'pagos':
        return redirect("panel_pagos")
    else:
        return redirect("panel_alumno_detalle", id_alumno=alumno.id_alumno)"""

content = content.replace(old_logic, new_logic)

with open('Pilapp/views_panel.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched redirect in panel_registrar_pago_alumno.")
