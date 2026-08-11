import os

file_path = r'C:\Users\jesus\Documents\pilates\Pilapp\views_panel.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    return render(request, "admin_panel/profes/clases_hoy.html", {
        "clases_data": clases_data,
        "fecha_hoy": hoy,
        "token": token,
        "fechas_alertas": sorted(list(fechas_alertas)),
        "es_reemplazo": es_reemplazo
    })"""

replacement = """    from .models import Instructor
    instructores_lista = Instructor.objects.select_related('id_persona').all()
    
    return render(request, "admin_panel/profes/clases_hoy.html", {
        "clases_data": clases_data,
        "fecha_hoy": hoy,
        "token": token,
        "fechas_alertas": sorted(list(fechas_alertas)),
        "es_reemplazo": es_reemplazo,
        "instructores_lista": instructores_lista,
    })"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("instructores_lista added to context")
else:
    print("Could not find context definition for clases_hoy.html")
