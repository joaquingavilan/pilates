import os

file_path = r'C:\Users\jesus\Documents\pilates\Pilapp\views_panel.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_view = """
@require_POST
def profes_registrar_honorario(request, token):
    from django.utils import timezone
    from datetime import datetime
    from .models import Instructor, HonorarioInstructor
    
    # Validar token
    if token not in ["acceso-profes", "acceso-profes-mat"]:
        return HttpResponse("Acceso denegado. Token inválido.", status=403)
        
    fecha_str = request.POST.get("fecha")
    id_instructor = request.POST.get("id_instructor")
    turno = request.POST.get("turno")
    cantidad_clases = request.POST.get("cantidad_clases", 1)
    monto_total = request.POST.get("monto_total", 0)
    
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        instructor = Instructor.objects.get(pk=id_instructor)
        
        HonorarioInstructor.objects.create(
            id_instructor=instructor,
            fecha=fecha,
            turno=turno,
            cantidad_clases=int(cantidad_clases),
            monto_total=float(monto_total)
        )
        messages.success(request, f"¡Honorario de {monto_total} Gs. guardado correctamente para el turno {turno}!")
    except Exception as e:
        messages.error(request, f"Error al guardar honorario: {e}")
        
    # Redirigir de vuelta a la página actual manteniendo la fecha
    url = redirect("profes_clases_hoy", token=token)
    if fecha_str:
        url['Location'] += f"?fecha={fecha_str}"
    return url

"""

if "def profes_registrar_honorario" not in content:
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(new_view)
    print("profes_registrar_honorario added to views_panel.py")
else:
    print("View already exists")
