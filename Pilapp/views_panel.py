from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from collections import defaultdict
from django.db.models import Q, Count
from datetime import date, timedelta, datetime
from .models import (
    Alumno, Persona, Clase, Turno, AlumnoClase, AlumnoClaseOcasional,
    AlumnoPaquete, Paquete, Pago, PagoAlumno, ClienteProspecto
)
import time 
from django.http import HttpResponse
from django.template import loader


def panel_dashboard(request):
    """Vista principal del dashboard con estadísticas."""
    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    
    # Estadísticas básicas
    stats = {
        'alumnos_regulares': Alumno.objects.filter(estado='regular').count(),
        'alumnos_ocasionales': Alumno.objects.filter(estado='ocasional').count(),
        'clases_hoy': Clase.objects.filter(fecha=hoy).count(),
        'pagos_pendientes': AlumnoPaquete.objects.filter(estado_pago='pendiente').count(),
        'clases_semana': Clase.objects.filter(fecha__gte=inicio_semana, fecha__lte=fin_semana).count(),
        'asistencias_semana': AlumnoClase.objects.filter(
            id_clase__fecha__gte=inicio_semana,
            id_clase__fecha__lte=fin_semana,
            estado='asistió'
        ).count(),
        'inasistencias_semana': AlumnoClase.objects.filter(
            id_clase__fecha__gte=inicio_semana,
            id_clase__fecha__lte=fin_semana,
            estado='faltó'
        ).count(),
        'prospectos_nuevos': ClienteProspecto.objects.filter(
            fecha_contacto__gte=inicio_semana
        ).count(),
    }
    
    # Clases de hoy
    clases_hoy = Clase.objects.filter(fecha=hoy).select_related('id_turno').order_by('id_turno__horario')
    
    # Últimos alumnos registrados
    ultimos_alumnos = Alumno.objects.select_related('id_persona').order_by('-id_alumno')[:5]
    
    return render(request, 'admin_panel/dashboard.html', {
        'stats': stats,
        'clases_hoy': clases_hoy,
        'ultimos_alumnos': ultimos_alumnos,
        'fecha_hoy': hoy,
    })


def panel_calendario(request):

    semana_param = request.GET.get("semana")

    if semana_param:
        try:
            fecha_ref = datetime.strptime(semana_param, "%Y-%m-%d").date()
        except ValueError:
            fecha_ref = date.today()
    else:
        fecha_ref = date.today()

    # Calcular lunes de esa semana
    inicio_semana = fecha_ref - timedelta(days=fecha_ref.weekday())
    fin_semana = inicio_semana + timedelta(days=5)  # lunes a sábado

    semana_anterior = (inicio_semana - timedelta(days=7)).strftime("%Y-%m-%d")
    semana_siguiente = (inicio_semana + timedelta(days=7)).strftime("%Y-%m-%d")

    hoy = date.today()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    es_semana_actual = (inicio_semana == lunes_actual)

    return render(
        request,
        "admin_panel/calendario.html",
        {
            "semana_anterior": semana_anterior,
            "semana_siguiente": semana_siguiente,
            "fecha_inicio": inicio_semana,
            "fecha_fin": fin_semana,
            "es_semana_actual": es_semana_actual,
        },
    )


def api_calendario(request):
    semana_param = request.GET.get("semana")

    if semana_param:
        try:
            fecha_ref = datetime.strptime(semana_param, "%Y-%m-%d").date()
        except ValueError:
            fecha_ref = date.today()
    else:
        fecha_ref = date.today()

    inicio_semana = fecha_ref - timedelta(days=fecha_ref.weekday())
    fin_semana = inicio_semana + timedelta(days=5)

    # Días
    dias = [
        (inicio_semana + timedelta(days=i)).isoformat()
        for i in range(6)
    ]

    # Horarios
    horarios = list(
        Turno.objects.values_list("horario", flat=True)
        .distinct()
        .order_by("horario")
    )

    # Clases
    clases_semana = (
        Clase.objects.filter(
            fecha__gte=inicio_semana,
            fecha__lte=fin_semana,
        )
        .select_related("id_turno")
    )

    conteo = defaultdict(lambda: {"reg": 0, "ocas": 0})

    reg = (
        AlumnoClase.objects
        .filter(id_clase__fecha__gte=inicio_semana,
                id_clase__fecha__lte=fin_semana)
        .values("id_clase")
        .annotate(c=Count("id_clase"))
    )
    for r in reg:
        conteo[r["id_clase"]]["reg"] = r["c"]

    ocas = (
        AlumnoClaseOcasional.objects
        .filter(id_clase__fecha__gte=inicio_semana,
                id_clase__fecha__lte=fin_semana)
        .values("id_clase")
        .annotate(c=Count("id_clase"))
    )
    for o in ocas:
        conteo[o["id_clase"]]["ocas"] = o["c"]

    # Construir estructura
    clases_dict = defaultdict(dict)

    for clase in clases_semana:
        h = clase.id_turno.horario.isoformat()
        f = clase.fecha.isoformat()
        total = conteo[clase.id_clase]["reg"] + conteo[clase.id_clase]["ocas"]

        if total >= 4:
            color = "lleno"
        elif total >= 2:
            color = "parcial"
        else:
            color = "disponible"

        clases_dict[h][f] = {
            "id": clase.id_clase,
            "total": total,
            "color": color,
        }

    result = {
        "dias": dias,
        "horarios": horarios,
        "clases": clases_dict,
    }

    return JsonResponse(result)

def panel_alumnos(request):
    """Lista de alumnos con filtros."""
    from .models import AlumnoPaqueteTurno
    
    alumnos = Alumno.objects.select_related('id_persona').all()
    
    filtros = {
        'q': request.GET.get('q', ''),
        'estado': request.GET.get('estado', ''),
        'orden': request.GET.get('orden', 'nombre'),
    }
    
    # Filtro de búsqueda
    if filtros['q']:
        alumnos = alumnos.filter(
            Q(id_persona__nombre__icontains=filtros['q']) |
            Q(id_persona__apellido__icontains=filtros['q']) |
            Q(id_persona__telefono__icontains=filtros['q'])
        )
    
    # Filtro de estado
    if filtros['estado']:
        alumnos = alumnos.filter(estado=filtros['estado'])
    
    # Ordenamiento
    if filtros['orden'] == 'nombre':
        alumnos = alumnos.order_by('id_persona__nombre', 'id_persona__apellido')
    elif filtros['orden'] == '-id_alumno':
        alumnos = alumnos.order_by('-id_alumno')
    elif filtros['orden'] == 'ultima_clase':
        alumnos = alumnos.order_by('-ultima_clase')
    
    # Obtener turnos por alumno (solo paquetes activos)
    turnos_por_alumno = {}
    asignaciones = AlumnoPaqueteTurno.objects.filter(
        id_alumno_paquete__estado='activo'
    ).select_related('id_turno', 'id_alumno_paquete__id_alumno')
    
    for asig in asignaciones:
        alumno_id = asig.id_alumno_paquete.id_alumno.id_alumno
        turno = asig.id_turno
        if alumno_id not in turnos_por_alumno:
            turnos_por_alumno[alumno_id] = []
        turnos_por_alumno[alumno_id].append({
            'dia': turno.dia,
            'horario': turno.horario.strftime('%H:%M')
        })
    
    # Agregar paquete activo y turnos a cada alumno
    for alumno in alumnos:
        alumno.paquete_activo = AlumnoPaquete.objects.filter(
            id_alumno=alumno, estado='activo'
        ).select_related('id_paquete').first()
        alumno.turnos = turnos_por_alumno.get(alumno.id_alumno, [])
    
    return render(request, 'admin_panel/alumnos/lista.html', {
        'alumnos': alumnos,
        'filtros': filtros,
    })


def panel_alumno_detalle(request, id_alumno):
    """Detalle de un alumno específico."""
    from .models import AlumnoPaqueteTurno
    
    alumno = get_object_or_404(Alumno.objects.select_related('id_persona'), id_alumno=id_alumno)
    
    # Paquetes del alumno
    paquetes = AlumnoPaquete.objects.filter(id_alumno=alumno).select_related('id_paquete')
    for paquete in paquetes:
        paquete.clases_usadas = AlumnoClase.objects.filter(
            id_alumno_paquete=paquete,
            estado__in=['asistió', 'faltó']
        ).count()
        total = paquete.id_paquete.cantidad_clases
        paquete.porcentaje_uso = (paquete.clases_usadas / total * 100) if total > 0 else 0
    
    # Turnos asignados (solo paquetes activos)
    turnos = AlumnoPaqueteTurno.objects.filter(
        id_alumno_paquete__id_alumno=alumno,
        id_alumno_paquete__estado='activo'
    ).select_related('id_turno')
    
    # Historial de clases (regulares + ocasionales)
    historial_clases = []
    
    # Clases regulares
    clases_regulares = AlumnoClase.objects.filter(
        id_alumno_paquete__id_alumno=alumno
    ).select_related('id_clase', 'id_clase__id_turno').order_by('-id_clase__fecha')
    
    for ac in clases_regulares:
        historial_clases.append({
            'fecha': ac.id_clase.fecha,
            'horario': ac.id_clase.id_turno.horario.strftime('%H:%M'),
            'tipo': 'regular',
            'estado': ac.estado,
        })
    
    # Clases ocasionales
    clases_ocasionales = AlumnoClaseOcasional.objects.filter(
        id_alumno=alumno
    ).select_related('id_clase', 'id_clase__id_turno').order_by('-id_clase__fecha')
    
    for ao in clases_ocasionales:
        historial_clases.append({
            'fecha': ao.id_clase.fecha,
            'horario': ao.id_clase.id_turno.horario.strftime('%H:%M'),
            'tipo': 'ocasional',
            'estado': ao.estado,
        })
    
    # Ordenar por fecha descendente
    historial_clases.sort(key=lambda x: x['fecha'], reverse=True)
    
    # Pagos
    pagos = PagoAlumno.objects.filter(
        id_alumno_paquete__id_alumno=alumno
    ).select_related('id_pago', 'id_alumno_paquete__id_paquete').order_by('-id_pago__fecha')
    
    return render(request, 'admin_panel/alumnos/detalle.html', {
        'alumno': alumno,
        'paquetes': paquetes,
        'turnos': turnos,
        'historial_clases': historial_clases,
        'pagos': pagos,
    })


def panel_clases(request):
    """Lista de clases con filtros."""
    fecha_desde = request.GET.get('desde')
    fecha_hasta = request.GET.get('hasta')
    
    hoy = date.today()
    
    if not fecha_desde:
        fecha_desde = hoy - timedelta(days=7)
    else:
        fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
    
    if not fecha_hasta:
        fecha_hasta = hoy + timedelta(days=7)
    else:
        fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()

    clases = Clase.objects.filter(
        fecha__gte=fecha_desde,
        fecha__lte=fecha_hasta
    ).select_related('id_turno').annotate(
        total_regulares=Count('alumnoclase'),
        total_ocasionales=Count('alumnoclaseocasional')
    ).order_by('fecha', 'id_turno__horario')

    # Agregar atributo sin pelear con Django
    for c in clases:
        c.total = c.total_regulares + c.total_ocasionales


    return render(request, "admin_panel/clases/lista.html", {
        "clases": clases,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
    })

def panel_clase_detalle(request, id_clase):
    """Detalle de una clase específica."""
    clase = get_object_or_404(Clase.objects.select_related('id_turno', 'id_instructor__id_persona'), id_clase=id_clase)
    
    # Alumnos regulares
    alumnos_regulares = AlumnoClase.objects.filter(id_clase=clase).select_related(
        'id_alumno_paquete__id_alumno__id_persona'
    )
    
    # Alumnos ocasionales
    alumnos_ocasionales = AlumnoClaseOcasional.objects.filter(id_clase=clase).select_related(
        'id_alumno__id_persona'
    )
    
    return render(request, 'admin_panel/clases/detalle.html', {
        'clase': clase,
        'alumnos_regulares': alumnos_regulares,
        'alumnos_ocasionales': alumnos_ocasionales,
    })



def panel_turnos(request):
    """Vista de todos los turnos."""
    from .models import AlumnoPaqueteTurno
    
    turnos = Turno.objects.all().order_by('dia', 'horario')
    
    # Contar alumnos por turno (solo paquetes activos)
    conteo = {}
    asignaciones = AlumnoPaqueteTurno.objects.filter(
        id_alumno_paquete__estado='activo'
    ).values('id_turno').annotate(total=Count('id_turno'))
    
    for a in asignaciones:
        conteo[a['id_turno']] = a['total']
    
    # Agregar conteo a cada turno
    for turno in turnos:
        turno.ocupados = conteo.get(turno.id_turno, 0)
        # Colores: 0=rojo, 1-3=amarillo, 4=verde
        if turno.ocupados == 0:
            turno.estado_color = 'danger'  # rojo
        elif turno.ocupados >= 4:
            turno.estado_color = 'success'  # verde
        else:
            turno.estado_color = 'warning'  # amarillo
    
    # Agrupar por día
    turnos_por_dia = {}
    orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
    
    for turno in turnos:
        turnos_por_dia.setdefault(turno.dia, []).append(turno)
    
    turnos_ordenados = [(dia, turnos_por_dia.get(dia, [])) for dia in orden_dias]
    
    return render(request, 'admin_panel/turnos.html', {
        'turnos_por_dia': turnos_ordenados,
    })


def panel_pagos(request):
    """Lista de paquetes y su estado de pago."""
    estado_pago = request.GET.get('estado', '')
    
    paquetes = AlumnoPaquete.objects.select_related(
        'id_alumno__id_persona', 'id_paquete'
    ).order_by('-fecha_inicio')
    
    if estado_pago:
        paquetes = paquetes.filter(estado_pago=estado_pago)
    
    return render(request, 'admin_panel/pagos.html', {
        'paquetes': paquetes,
        'estado_pago': estado_pago,
    })


def panel_prospectos(request):
    """Lista de prospectos."""
    estado = request.GET.get('estado', '')
    
    prospectos = ClienteProspecto.objects.all().order_by('-fecha_contacto')
    
    if estado:
        prospectos = prospectos.filter(estado=estado)
    
    return render(request, 'admin_panel/prospectos.html', {
        'prospectos': prospectos,
        'estado_filtro': estado,
    })


# API endpoints para AJAX
def api_clase_alumnos(request, id_clase):
    """API para obtener alumnos de una clase (usado en modal del calendario)."""
    clase = get_object_or_404(Clase, id_clase=id_clase)
    
    alumnos = []
    
    # Regulares
    for ac in AlumnoClase.objects.filter(id_clase=clase).select_related('id_alumno_paquete__id_alumno__id_persona'):
        persona = ac.id_alumno_paquete.id_alumno.id_persona
        alumnos.append({
            'nombre': persona.nombre,
            'apellido': persona.apellido,
            'tipo': 'regular',
            'estado': ac.estado,
        })
    
    # Ocasionales
    for ao in AlumnoClaseOcasional.objects.filter(id_clase=clase).select_related('id_alumno__id_persona'):
        persona = ao.id_alumno.id_persona
        alumnos.append({
            'nombre': persona.nombre,
            'apellido': persona.apellido,
            'tipo': 'ocasional',
            'estado': ao.estado,
        })
    
    return JsonResponse({'alumnos': alumnos})


def api_turno_alumnos(request, id_turno):
    """API para obtener alumnos asignados a un turno (regulares con paquete activo)."""
    turno = get_object_or_404(Turno, id_turno=id_turno)
    
    alumnos = []
    
    # Obtener alumnos que tienen este turno asignado en su paquete
    from .models import AlumnoPaqueteTurno
    
    asignaciones = AlumnoPaqueteTurno.objects.filter(
        id_turno=turno
    ).select_related(
        'id_alumno_paquete__id_alumno__id_persona',
        'id_alumno_paquete'
    )
    
    for asig in asignaciones:
        alumno_paquete = asig.id_alumno_paquete
        persona = alumno_paquete.id_alumno.id_persona
        alumnos.append({
            'nombre': persona.nombre,
            'apellido': persona.apellido,
            'telefono': persona.telefono,
            'estado_paquete': alumno_paquete.estado,
        })
    
    return JsonResponse({'alumnos': alumnos})