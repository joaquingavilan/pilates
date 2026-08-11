import os

file_path = r'C:\Users\jesus\Documents\pilates\Pilapp\views_panel.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_view = """
def panel_honorarios_resumen(request):
    from .models import HonorarioInstructor, Instructor
    from django.db.models import Sum
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    filtro_mes = request.GET.get('mes', timezone.now().strftime('%Y-%m'))
    
    try:
        año, mes = map(int, filtro_mes.split('-'))
    except ValueError:
        año, mes = timezone.now().year, timezone.now().month
        
    # Obtener honorarios del mes seleccionado
    honorarios = HonorarioInstructor.objects.filter(
        fecha__year=año,
        fecha__month=mes
    ).select_related('id_instructor__id_persona').order_by('fecha')
    
    # Agrupar por instructora y fecha
    # Estructura: { id_instructor: { 'nombre': '...', 'dias': { '2023-10-01': { 'M': x, 'T': y, 'total_monto': z } }, 'total_clases': X, 'total_monto': Y } }
    resumen = {}
    for h in honorarios:
        id_inst = h.id_instructor.id_instructor
        if id_inst not in resumen:
            resumen[id_inst] = {
                'nombre': f"{h.id_instructor.id_persona.nombre} {h.id_instructor.id_persona.apellido}",
                'dias': {},
                'total_clases': 0,
                'total_monto': 0
            }
            
        fecha_str = h.fecha.strftime('%d/%m')
        if fecha_str not in resumen[id_inst]['dias']:
            resumen[id_inst]['dias'][fecha_str] = {'clases': 0, 'monto': 0, 'detalle': []}
            
        resumen[id_inst]['dias'][fecha_str]['clases'] += h.cantidad_clases
        resumen[id_inst]['dias'][fecha_str]['monto'] += h.monto_total
        resumen[id_inst]['dias'][fecha_str]['detalle'].append(f"{h.turno}: {h.cantidad_clases}c ({h.monto_total} Gs)")
        
        resumen[id_inst]['total_clases'] += h.cantidad_clases
        resumen[id_inst]['total_monto'] += h.monto_total

    context = {
        'filtro_mes': filtro_mes,
        'resumen': resumen,
    }
    return render(request, "admin_panel/honorarios/resumen.html", context)
"""

if "def panel_honorarios_resumen" not in content:
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(new_view)
    print("panel_honorarios_resumen added to views_panel.py")
else:
    print("View already exists")
