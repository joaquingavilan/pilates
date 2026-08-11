import os

file_path = r'C:\Users\jesus\Documents\pilates\Pilapp\views_panel.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """        resumen[nombre_prof]['dias'][fecha_str]['detalle'].append(f"{h.turno}: {h.cantidad_clases}c ({h.monto_total} Gs)")"""
replacement = """        resumen[nombre_prof]['dias'][fecha_str]['detalle'].append({
            'id': h.id_honorario,
            'texto': f"{h.turno}: {h.cantidad_clases}c ({h.monto_total} Gs)"
        })"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched views_panel.py detalle structure")
else:
    print("Target not found")
