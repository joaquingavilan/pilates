with open('Pilapp/views_panel.py', 'r', encoding='utf-8') as f:
    content = f.read()

view_code = """
@admin_required
def panel_ex_alumnos(request):
    query = request.GET.get('q', '').strip()
    dia = request.GET.get('dia', '').strip()
    
    ex_alumnos = ExAlumno.objects.all().order_by('-fecha_baja')
    
    if query:
        ex_alumnos = ex_alumnos.filter(
            Q(nombre__icontains=query) |
            Q(apellido__icontains=query) |
            Q(telefono__icontains=query) |
            Q(horarios__icontains=query)
        )
    
    if dia:
        ex_alumnos = ex_alumnos.filter(horarios__icontains=dia)
        
    return render(request, "admin_panel/ex_alumnos.html", {
        "ex_alumnos": ex_alumnos,
        "query": query,
        "dia": dia,
    })
"""

# Append the view at the end of the file
if 'def panel_ex_alumnos' not in content:
    with open('Pilapp/views_panel.py', 'a', encoding='utf-8') as f:
        f.write(view_code)
        
print("Patched Pilapp/views_panel.py successfully.")
