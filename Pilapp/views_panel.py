import json
#imports de python
import time 
from decimal import Decimal, InvalidOperation
from collections import defaultdict
from datetime import date, timedelta, datetime


#imports de django
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.template import loader
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.db import transaction
from django.contrib import messages
from django.utils import timezone



#imports del proyecto

from .models import (
    ExAlumno,
    Alumno, Persona, Clase, Turno, AlumnoClase, AlumnoClaseOcasional,
    AlumnoPaquete, Paquete, Pago, PagoAlumno, ClienteProspecto,
    AlumnoPaqueteTurno, PagoInstructor, Instructor,
    Producto, MovimientoProducto, Gasto, HonorarioInstructor
)






def panel_dashboard(request):
    """Vista principal del dashboard con estadísticas."""
    hoy = timezone.localdate()
    ahora = timezone.localtime()
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
        'hora_actual': ahora,
    })


def panel_calendario(request):
    semana_param = request.GET.get("semana")

    if semana_param:
        try:
            fecha_ref = datetime.strptime(semana_param, "%Y-%m-%d").date()
        except ValueError:
            fecha_ref = timezone.localdate()
    else:
        fecha_ref = timezone.localdate()

    # Si es domingo, usar el lunes de la PRÓXIMA semana
    dia_semana = fecha_ref.weekday()
    if dia_semana == 6:  # Domingo
        inicio_semana = fecha_ref + timedelta(days=1)  # Próximo lunes
    else:
        inicio_semana = fecha_ref - timedelta(days=dia_semana)
    
    fin_semana = inicio_semana + timedelta(days=5)  # Sábado

    semana_anterior = (inicio_semana - timedelta(days=7)).strftime("%Y-%m-%d")
    semana_siguiente = (inicio_semana + timedelta(days=7)).strftime("%Y-%m-%d")

    hoy = timezone.localdate()
    if hoy.weekday() == 6:
        lunes_actual = hoy + timedelta(days=1)
    else:
        lunes_actual = hoy - timedelta(days=hoy.weekday())
    
    es_semana_actual = (inicio_semana == lunes_actual)

    return render(request, "admin_panel/calendario.html", {
        "semana_anterior": semana_anterior,
        "semana_siguiente": semana_siguiente,
        "fecha_inicio": inicio_semana,
        "fecha_fin": fin_semana,
        "es_semana_actual": es_semana_actual,
    })

def api_calendario(request):
    semana_param = request.GET.get("semana")

    if semana_param:
        try:
            fecha_ref = datetime.strptime(semana_param, "%Y-%m-%d").date()
        except ValueError:
            fecha_ref = timezone.localdate()
    else:
        fecha_ref = timezone.localdate()

    # Si es domingo, usar el lunes de la PRÓXIMA semana
    dia_semana = fecha_ref.weekday()
    if dia_semana == 6:  # Domingo
        inicio_semana = fecha_ref + timedelta(days=1)
    else:
        inicio_semana = fecha_ref - timedelta(days=dia_semana)
    
    fin_semana = inicio_semana + timedelta(days=5)  # Sábado

    # Días (lunes a sábado = 6 días)
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
        .filter(id_clase__fecha__gte=inicio_semana, id_clase__fecha__lte=fin_semana)
        .exclude(estado__in={"canceló", "reprogramó"})
        .values("id_clase")
        .annotate(c=Count("id_clase"))
    )
    for r in reg:
        conteo[r["id_clase"]]["reg"] = r["c"]

    ocas = (
        AlumnoClaseOcasional.objects
        .filter(id_clase__fecha__gte=inicio_semana, id_clase__fecha__lte=fin_semana)
        .exclude(estado="canceló")
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
            "disciplina": clase.id_turno.disciplina,
        }

    result = {
        "dias": dias,
        "horarios": horarios,
        "clases": clases_dict,
    }

    return JsonResponse(result)


@require_GET
def panel_vencimientos(request):
    """Vista para ver vencimientos de paquetes activos y clases restantes."""
    from .models import AlumnoPaquete, AlumnoClase
    from datetime import timedelta
    from django.utils import timezone
    
    vencimientos = []
    hoy = timezone.now().date()
    
    filtro_dias = request.GET.get('filtro_dias')
    filtro_restantes = request.GET.get('filtro_restantes')
    filtro_estado = request.GET.get('filtro_estado', 'activo')
    
    paquetes_activos = AlumnoPaquete.objects.filter(estado='activo').select_related('id_alumno__id_persona', 'id_paquete')
    
    for paquete in paquetes_activos:
        clases_usadas = AlumnoClase.objects.filter(
            id_alumno_paquete=paquete,
            estado__in=['asistió', 'faltó', 'recuperó']
        ).count()
        
        paquete_total = paquete.id_paquete.cantidad_clases
        clases_restantes = paquete_total - clases_usadas
        if clases_restantes < 0:
            clases_restantes = 0
            
        fecha_venc = None
        dias_vencer = 9999
        if paquete.fecha_inicio:
            fecha_venc = paquete.fecha_inicio + timedelta(days=30)
            dias_vencer = (fecha_venc - hoy).days
            
        # Filtro estado (vencidos reales vs al día)
        if filtro_estado == 'vencido':
            # Solo mostrar los que tienen 0 clases o días < 0
            if clases_restantes > 0 and dias_vencer >= 0:
                continue
        elif filtro_estado == 'activo':
            # Solo mostrar los que NO están vencidos
            if clases_restantes == 0 or dias_vencer < 0:
                continue
                
        # Filtros adicionales
        if filtro_dias:
            if dias_vencer > int(filtro_dias):
                continue
                
        if filtro_restantes:
            if filtro_restantes == '2':
                if clases_restantes > 2:
                    continue
            else:
                if clases_restantes != int(filtro_restantes):
                    continue
                    
        vencimientos.append({
            'alumno': paquete.id_alumno,
            'fecha_inicio': paquete.fecha_inicio,
            'fecha_venc': fecha_venc,
            'dias_vencer': dias_vencer,
            'paquete_total': paquete_total,
            'clases_restantes': clases_restantes
        })
        
    # Ordenar por clases restantes ascendente y dias_vencer ascendente
    vencimientos.sort(key=lambda x: (x['clases_restantes'], x['dias_vencer']))
    
    return render(request, "admin_panel/alumnos/vencimientos.html", {
        "vencimientos": vencimientos
    })

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

def panel_alumno_crear(request):
    """Vista para crear manualmente un alumno nuevo (y su persona asociada)."""
    from .models import Paquete, Turno, Persona, Alumno
    from .views import registrar_alumno_datos
    from django.db import transaction
    
    paquetes = Paquete.objects.all().order_by('cantidad_clases')
    turnos = Turno.objects.all().order_by('dia', 'horario')
    
    dias_orden = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    turnos_reformer = {dia: [] for dia in dias_orden}
    turnos_mat = {dia: [] for dia in dias_orden}
    for t in turnos:
        if t.disciplina == 'MAT':
            if t.dia in turnos_mat:
                turnos_mat[t.dia].append(t)
        else:
            if t.dia in turnos_reformer:
                turnos_reformer[t.dia].append(t)
                
    turnos_reformer = {k: v for k, v in turnos_reformer.items() if v}
    turnos_mat = {k: v for k, v in turnos_mat.items() if v}

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        apellido = request.POST.get("apellido", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        canal = request.POST.get("canal_captacion", "").strip()
        ruc = request.POST.get("ruc", "").strip()
        razon_social = request.POST.get("razon_social", "").strip()
        razon_social = request.POST.get("razon_social", "").strip()
        
        paquete_val = request.POST.get("paquete")
        turnos_seleccionados = request.POST.getlist("turnos")
        fecha_inicio = request.POST.get("fecha_inicio", "").strip()
        
        if not nombre or not apellido:
            messages.error(request, "Nombre y apellido son obligatorios.")
            return render(request, "admin_panel/alumnos/crear.html", {"paquetes": paquetes, "turnos_reformer": turnos_reformer, "turnos_mat": turnos_mat})
            
        try:
            if paquete_val == "ocasional" or not paquete_val:
                with transaction.atomic():
                    persona = Persona.objects.create(
                        nombre=nombre,
                        apellido=apellido,
                        telefono=telefono,
                        ruc=ruc,
                        razon_social=razon_social
                    )
                    alumno = Alumno.objects.create(
                        id_persona=persona,
                        estado="ocasional",
                        canal_captacion=canal
                    )
                messages.success(request, f"Alumna {nombre} {apellido} registrada como ocasional (sin paquete asignado).")
                return redirect("panel_alumno_detalle", id_alumno=alumno.id_alumno)
            else:
                data = {
                    "nombre": nombre,
                    "apellido": apellido,
                    "telefono": telefono,
                    "canal_captacion": canal,
                    "paquete": int(paquete_val),
                    "turnos": turnos_seleccionados,
                    "fecha_inicio": fecha_inicio
                }
                
                registrar_alumno_datos(data)
                
                persona_creada = Persona.objects.filter(nombre=nombre, apellido=apellido, telefono=telefono).order_by('-id_persona').first()
                if not persona_creada:
                    persona_creada = Persona.objects.filter(nombre=nombre, apellido=apellido).order_by('-id_persona').first()
                
                alumno_creado = Alumno.objects.filter(id_persona=persona_creada).first()
                
                messages.success(request, f"Alumna {nombre} {apellido} registrada exitosamente con paquete de {paquete_val} clases.")
                return redirect("panel_alumno_detalle", id_alumno=alumno_creado.id_alumno)
                
        except Exception as e:
            messages.error(request, f"Ocurrió un error al crear la alumna: {str(e)}")
            
    return render(request, "admin_panel/alumnos/crear.html", {
        "paquetes": paquetes,
        "turnos_reformer": turnos_reformer,
        "turnos_mat": turnos_mat
    })

def panel_alumno_editar(request, id_alumno):
    """Vista para editar los datos personales de un alumno."""
    alumno = get_object_or_404(Alumno, id_alumno=id_alumno)
    persona = alumno.id_persona
    
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        apellido = request.POST.get("apellido", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        ruc = request.POST.get("ruc", "").strip()
        razon_social = request.POST.get("razon_social", "").strip()
        estado = request.POST.get("estado", "ocasional")
        canal = request.POST.get("canal_captacion", "").strip()
        ruc = request.POST.get("ruc", "").strip()
        razon_social = request.POST.get("razon_social", "").strip()
        razon_social = request.POST.get("razon_social", "").strip()
        observaciones = request.POST.get("observaciones", "").strip()
        
        if not nombre or not apellido:
            messages.error(request, "Nombre y apellido son obligatorios.")
        else:
            try:
                with transaction.atomic():
                    persona.nombre = nombre
                    persona.apellido = apellido
                    persona.telefono = telefono
                    persona.ruc = ruc
                    persona.razon_social = razon_social
                    persona.observaciones = observaciones
                    persona.save()
                    
                    alumno.estado = estado
                    alumno.canal_captacion = canal
                    alumno.save()
                    
                messages.success(request, f"Datos de {nombre} {apellido} actualizados correctamente.")
                return redirect("panel_alumno_detalle", id_alumno=alumno.id_alumno)
            except Exception as e:
                messages.error(request, f"Ocurrió un error al actualizar: {str(e)}")
                
    context = {
        'alumno': alumno,
        'persona': persona
    }
    return render(request, "admin_panel/alumnos/editar.html", context)

@require_POST
def panel_alumno_paquete_eliminar(request, id_alumno, id_alumno_paquete):
    """Vista para eliminar un paquete."""
    from .models import AlumnoPaquete
    paquete_alumno = get_object_or_404(AlumnoPaquete, id_alumno_paquete=id_alumno_paquete, id_alumno_id=id_alumno)
    
    with transaction.atomic():
        # Al eliminar el paquete (on_delete=CASCADE suele estar en las dependencias, pero lo hacemos explícito por las dudas)
        # Se borran turnos asignados
        paquete_alumno.alumnopaqueteturno_set.all().delete()
        # Se borran clases
        paquete_alumno.alumnoclase_set.all().delete()
        # Se borran pagos 
        paquete_alumno.pagoalumno_set.all().delete()
        # Borrar el paquete del alumno
        paquete_alumno.delete()
        
    messages.success(request, "Paquete eliminado exitosamente.")
    return redirect("panel_alumno_detalle", id_alumno=id_alumno)

def panel_alumno_paquete_editar(request, id_alumno, id_alumno_paquete):
    """Vista para editar el paquete, estado y pago."""
    from .models import AlumnoPaquete, Paquete
    if request.method == "POST":
        paquete = get_object_or_404(AlumnoPaquete, id_alumno_paquete=id_alumno_paquete, id_alumno_id=id_alumno)
        nuevo_estado = request.POST.get("estado")
        nuevo_estado_pago = request.POST.get("estado_pago")
        nuevo_id_paquete = request.POST.get("id_paquete")
        nueva_fecha_inicio = request.POST.get("fecha_inicio")
        
        # Actualizar fecha de inicio
        if nueva_fecha_inicio:
            try:
                from datetime import datetime
                paquete.fecha_inicio = datetime.strptime(nueva_fecha_inicio, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Actualizar tipo de paquete si se envió
        if nuevo_id_paquete and str(nuevo_id_paquete).isdigit():
            try:
                paquete_obj = Paquete.objects.get(id_paquete=nuevo_id_paquete)
                paquete.id_paquete = paquete_obj
            except Paquete.DoesNotExist:
                pass

        # Validar
        if nuevo_estado in ["activo", "expirado"]:
            # Si se marca como expirado y antes era activo
            if nuevo_estado == "expirado" and paquete.estado == "activo":
                paquete.expirar_y_liberar()
            else:
                paquete.estado = nuevo_estado
                
        if nuevo_estado_pago in ["pendiente", "pagado", "parcial"]:
            paquete.estado_pago = nuevo_estado_pago
            
        paquete.save()
        messages.success(request, "Paquete actualizado correctamente.")
        
    return redirect("panel_alumno_detalle", id_alumno=id_alumno)

def panel_alumno_paquete_renovar(request, id_alumno):
    """Vista para renovar el paquete (expirar el actual y crear uno nuevo con los mismos turnos)."""
    from .views import renovar_paquete_datos
    if request.method == "POST":
        tipo_paquete = request.POST.get("tipo_paquete")
        fecha_inicio_str = request.POST.get("fecha_inicio")
        
        if not tipo_paquete:
            messages.error(request, "Debes seleccionar un tipo de paquete.")
            return redirect("panel_alumno_detalle", id_alumno=id_alumno)
            
        data = {
            "id_alumno": id_alumno,
            "tipo_paquete": tipo_paquete,
            "fecha_inicio": fecha_inicio_str,
            "turnos_nuevos": [] # No se agregan turnos nuevos desde acá, solo se mantienen los que tiene
        }
        
        resultado = renovar_paquete_datos(data)
        
        if "errores" in resultado:
            for error in resultado["errores"]:
                messages.error(request, error)
        else:
            messages.success(request, resultado.get("message", "Paquete renovado exitosamente."))
            
    return redirect("panel_alumno_detalle", id_alumno=id_alumno)

def panel_alumno_pago_editar(request, id_alumno, id_pago):
    """Vista para editar la fecha de un pago."""
    from .models import Pago
    from datetime import datetime
    
    if request.method == "POST":
        fecha_str = request.POST.get("fecha")
        if fecha_str:
            try:
                pago = get_object_or_404(Pago, id_pago=id_pago)
                fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                pago.fecha = fecha_obj
                pago.save()
                messages.success(request, "Fecha de pago actualizada correctamente.")
            except Exception as e:
                messages.error(request, f"Error al actualizar la fecha del pago: {str(e)}")
        else:
            messages.error(request, "La fecha no puede estar vacía.")
            
    return redirect("panel_alumno_detalle", id_alumno=id_alumno)

def panel_alumno_clase_editar(request, id_alumno, tipo, id_relacion):
    """Vista para editar el estado de asistencia de una clase."""
    from .models import AlumnoClase, AlumnoClaseOcasional
    if request.method == "POST":
        nuevo_estado = request.POST.get("estado")
        estados_permitidos = ["asistió", "faltó", "canceló", "recuperó", "reprogramó", "pendiente", "reservado", "feriado"]
        
        if nuevo_estado in estados_permitidos:
            if tipo == "regular":
                clase_rel = get_object_or_404(AlumnoClase, id_alumno_clase=id_relacion)
                clase_rel.estado = nuevo_estado
                clase_rel.save()
            elif tipo == "ocasional":
                clase_rel = get_object_or_404(AlumnoClaseOcasional, id_alumno_clase_ocasional=id_relacion, id_alumno_id=id_alumno)
                clase_rel.estado = nuevo_estado
                clase_rel.save()
                
            messages.success(request, "Estado de la clase actualizado.")
        else:
            messages.error(request, "Estado no válido.")
            
    return redirect("panel_alumno_detalle", id_alumno=id_alumno)

def panel_alumno_clase_crear(request, id_alumno):
    """Vista para crear (agendar) manualmente una clase para un alumno."""
    from .models import Turno, Clase, AlumnoPaquete, AlumnoClase, Instructor, AlumnoClaseOcasional
    from django.db.models import F
    from django.utils import timezone
    from datetime import datetime
    
    if request.method == "POST":
        fecha_str = request.POST.get("fecha")
        horario = request.POST.get("horario")
        
        if not fecha_str or not horario:
            messages.error(request, "Falta fecha u horario para crear la clase.")
            return redirect("panel_alumno_detalle", id_alumno=id_alumno)
            
        try:
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            # Mapear día de la semana (0=Lunes, 6=Domingo)
            dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            nombre_dia = dias[fecha_obj.weekday()]
            
            # Buscar el turno correspondiente
            try:
                turno_obj = Turno.objects.get(dia=nombre_dia, horario=horario)
            except Turno.DoesNotExist:
                messages.error(request, f"No existe un turno habilitado los {nombre_dia} a las {horario}.")
                return redirect("panel_alumno_detalle", id_alumno=id_alumno)
                
            with transaction.atomic():
                # Obtener o crear la clase
                clase_destino, _ = Clase.objects.get_or_create(
                    id_turno=turno_obj,
                    fecha=fecha_obj,
                    defaults={
                        "id_instructor": Instructor.objects.first()
                    }
                )
                
                # Validar cupo usando el cálculo dinámico (ignora cancelados y feriados)
                if clase_destino.obtener_total_inscriptos >= 4:
                    messages.error(request, f"No hay cupo disponible para el {fecha_str} a las {horario}.")
                    return redirect("panel_alumno_detalle", id_alumno=id_alumno)
                    
                # Buscar el paquete activo más reciente para asociarlo (o crearlo como ocasional si no hay)
                paquete_activo = AlumnoPaquete.objects.filter(id_alumno_id=id_alumno, estado='activo').order_by('-id_alumno_paquete').first()
                
                if paquete_activo:
                    # Verificar duplicado
                    if AlumnoClase.objects.filter(id_alumno_paquete=paquete_activo, id_clase=clase_destino).exists():
                        messages.error(request, "El alumno ya está inscripto en esta clase.")
                        return redirect("panel_alumno_detalle", id_alumno=id_alumno)
                        
                    AlumnoClase.objects.create(
                        id_alumno_paquete=paquete_activo,
                        id_clase=clase_destino,
                        estado="reservado"
                    )
                else:
                    if AlumnoClaseOcasional.objects.filter(id_alumno_id=id_alumno, id_clase=clase_destino).exists():
                        messages.error(request, "El alumno ya está inscripto ocasionalmente en esta clase.")
                        return redirect("panel_alumno_detalle", id_alumno=id_alumno)
                        
                    AlumnoClaseOcasional.objects.create(
                        id_alumno_id=id_alumno,
                        id_clase=clase_destino,
                        estado="reservado"
                    )
                
                # Incrementar inscriptos
                # The signals will handle updating total_inscriptos
                
                messages.success(request, f"Clase agendada exitosamente para el {fecha_str} a las {horario}.")
        except Exception as e:
            messages.error(request, f"Error al agendar la clase: {str(e)}")
            
    return redirect("panel_alumno_detalle", id_alumno=id_alumno)

def panel_alumno_clase_reprogramar(request, id_alumno, id_clase_origen):
    """Vista para reprogramar una clase hacia una nueva fecha y horario."""
    from .views import reprogramar_clase_datos
    if request.method == "POST":
        fecha_destino_str = request.POST.get("fecha_destino")
        hora_destino = request.POST.get("hora_destino")
        
        if not fecha_destino_str or not hora_destino:
            messages.error(request, "Debes seleccionar fecha y hora de destino.")
            return redirect("panel_alumno_detalle", id_alumno=id_alumno)
            
        try:
            fecha_dt = datetime.strptime(fecha_destino_str, "%Y-%m-%d")
            # Determinar el día de la semana (0=Lunes, ..., 6=Domingo)
            dias_map = {
                0: "Lunes", 1: "Martes", 2: "Miércoles",
                3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"
            }
            dia_destino = dias_map[fecha_dt.weekday()]
            
            data = {
                "id_alumno": id_alumno,
                "id_clase_origen": id_clase_origen,
                "dia_destino": dia_destino,
                "hora_destino": hora_destino,
                "fecha_destino": fecha_destino_str
            }
            
            resultado = reprogramar_clase_datos(data)
            
            if "errores" in resultado:
                for error in resultado["errores"]:
                    messages.error(request, error)
            else:
                messages.success(request, resultado.get("message", "Clase reprogramada."))
                
        except ValueError:
            messages.error(request, "Formato de fecha inválido.")
            
    return redirect("panel_alumno_detalle", id_alumno=id_alumno)

def panel_alumno_clase_eliminar(request, id_alumno, tipo, id_relacion):
    """Vista para eliminar permanentemente una clase de una alumna."""
    from .models import AlumnoClase, AlumnoClaseOcasional, Clase
    from django.db.models import F
    
    if request.method == "POST":
        try:
            with transaction.atomic():
                if tipo == "regular":
                    clase_rel = get_object_or_404(AlumnoClase, id_alumno_clase=id_relacion)
                    id_clase = clase_rel.id_clase_id
                    clase_rel.delete()
                elif tipo == "ocasional":
                    clase_rel = get_object_or_404(AlumnoClaseOcasional, id_alumno_clase_ocasional=id_relacion, id_alumno_id=id_alumno)
                    id_clase = clase_rel.id_clase_id
                    clase_rel.delete()
                else:
                    messages.error(request, "Tipo de clase no válido.")
                    return redirect("panel_alumno_detalle", id_alumno=id_alumno)

                # Descontar el cupo si corresponde
                # The signals will handle updating total_inscriptos
                messages.success(request, "Clase eliminada correctamente.")
                
        except Exception as e:
            messages.error(request, f"Error al eliminar clase: {str(e)}")
            
    return redirect("panel_alumno_detalle", id_alumno=id_alumno)

def panel_alumno_editar_turnos(request, id_alumno):
    """Vista para editar los turnos de un paquete activo."""
    from .models import Alumno, AlumnoPaquete, Turno, AlumnoPaqueteTurno
    from .views import cambiar_turnos_paquete_datos
    
    alumno = get_object_or_404(Alumno, id_alumno=id_alumno)
    alumno_paquete = AlumnoPaquete.objects.filter(id_alumno=alumno, estado='activo').order_by('-id_alumno_paquete').first()
    
    if not alumno_paquete:
        messages.error(request, "La alumna no tiene un paquete activo al cual editarle los turnos.")
        return redirect("panel_alumno_detalle", id_alumno=id_alumno)
        
    turnos = Turno.objects.all().order_by('dia', 'horario')
    
    dias_orden = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    turnos_reformer = {dia: [] for dia in dias_orden}
    turnos_mat = {dia: [] for dia in dias_orden}
    for t in turnos:
        if t.disciplina == 'MAT':
            if t.dia in turnos_mat:
                turnos_mat[t.dia].append(t)
        else:
            if t.dia in turnos_reformer:
                turnos_reformer[t.dia].append(t)
                
    turnos_reformer = {k: v for k, v in turnos_reformer.items() if v}
    turnos_mat = {k: v for k, v in turnos_mat.items() if v}
    
    turnos_asignados_ids = AlumnoPaqueteTurno.objects.filter(id_alumno_paquete=alumno_paquete).values_list('id_turno_id', flat=True)
    
    if request.method == "POST":
        turnos_seleccionados = request.POST.getlist("turnos")
        if not turnos_seleccionados:
            messages.error(request, "Debes seleccionar al menos un turno.")
        else:
            data = {
                "id_alumno": id_alumno,
                "id_paquete": alumno_paquete.id_paquete_id,
                "turnos_nuevos": turnos_seleccionados
            }
            
            resultado = cambiar_turnos_paquete_datos(data)
            
            if "errores" in resultado:
                for error in resultado["errores"]:
                    messages.error(request, error)
            else:
                messages.success(request, "Turnos actualizados correctamente.")
                return redirect("panel_alumno_detalle", id_alumno=id_alumno)
            
    context = {
        'alumno': alumno,
        'alumno_paquete': alumno_paquete,
        'turnos_reformer': turnos_reformer,
        'turnos_mat': turnos_mat,
        'turnos_asignados_ids': list(turnos_asignados_ids)
    }
    return render(request, "admin_panel/alumnos/editar_turnos.html", context)

def panel_alumno_detalle(request, id_alumno):
    """Detalle de un alumno específico."""
    from .models import AlumnoPaqueteTurno

    alumno = get_object_or_404(
        Alumno.objects.select_related('id_persona'),
        id_alumno=id_alumno
    )

    # Paquetes del alumno (ordenados por "más reciente" usando el PK)
    paquetes = (
        AlumnoPaquete.objects
        .filter(id_alumno=alumno)
        .select_related('id_paquete')
        .order_by('-id_alumno_paquete')
    )

    # Definir último paquete (si existe)
    ultimo_paquete = paquetes.first()
    ultimo_paquete_id = ultimo_paquete.id_alumno_paquete if ultimo_paquete else None

    # Calcular pagado/restante solo para el último paquete
    total_pagado_ultimo = None
    restante_ultimo = None
    if ultimo_paquete:
        total_pagado_ultimo = (
            PagoAlumno.objects
            .filter(id_alumno_paquete=ultimo_paquete, id_pago__estado__in=['pagado', 'parcial'])
            .aggregate(total=Sum('id_pago__monto'))
            .get('total') or Decimal('0')
        )
        costo = ultimo_paquete.id_paquete.costo or Decimal('0')
        restante_ultimo = max(Decimal('0'), costo - total_pagado_ultimo)

    # Enriquecer cada paquete con clases usadas + porcentaje
    for paquete in paquetes:
        paquete.clases_usadas = AlumnoClase.objects.filter(
            id_alumno_paquete=paquete,
            estado__in=['asistió', 'faltó', 'recuperó']
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

    clases_regulares = AlumnoClase.objects.filter(
        id_alumno_paquete__id_alumno=alumno
    ).select_related('id_clase', 'id_clase__id_turno').order_by('-id_clase__fecha')

    for ac in clases_regulares:
        historial_clases.append({
            'id_relacion': ac.id_alumno_clase,
            'id_clase': ac.id_clase.id_clase,
            'fecha': ac.id_clase.fecha,
            'horario': ac.id_clase.id_turno.horario.strftime('%H:%M'),
            'disciplina': ac.id_clase.id_turno.disciplina,
            'tipo': 'regular',
            'estado': ac.estado,
        })

    clases_ocasionales = AlumnoClaseOcasional.objects.filter(
        id_alumno=alumno
    ).select_related('id_clase', 'id_clase__id_turno').order_by('-id_clase__fecha')

    for ao in clases_ocasionales:
        historial_clases.append({
            'id_relacion': ao.id_alumno_clase_ocasional,
            'id_clase': ao.id_clase.id_clase,
            'fecha': ao.id_clase.fecha,
            'horario': ao.id_clase.id_turno.horario.strftime('%H:%M'),
            'disciplina': ao.id_clase.id_turno.disciplina,
            'tipo': 'ocasional',
            'estado': ao.estado,
        })

    historial_clases.sort(key=lambda x: x['fecha'], reverse=True)

    # Pagos (ya lo tenías bien)
    pagos = PagoAlumno.objects.filter(
        id_alumno_paquete__id_alumno=alumno
    ).select_related('id_pago', 'id_alumno_paquete__id_paquete').order_by('-id_pago__fecha')

    # Horarios únicos disponibles para el dropdown de reprogramar
    from .models import Turno, Paquete
    horarios_disponibles = sorted(list(set(t.horario.strftime('%H:%M') for t in Turno.objects.all())))
    
    # Todos los paquetes disponibles para actualizar
    lista_paquetes = Paquete.objects.all().order_by('cantidad_clases')

    return render(request, 'admin_panel/alumnos/detalle.html', {
        'alumno': alumno,
        'paquetes': paquetes,
        'turnos': turnos,
        'historial_clases': historial_clases,
        'pagos': pagos,
        'horarios_disponibles': horarios_disponibles,
        'lista_paquetes': lista_paquetes,

        # NUEVO
        'ultimo_paquete_id': ultimo_paquete_id,
        'total_pagado_ultimo': total_pagado_ultimo,
        'restante_ultimo': restante_ultimo,
    })

def panel_clases(request):
    """Lista de clases con filtros."""
    fecha_desde = request.GET.get('desde')
    fecha_hasta = request.GET.get('hasta')
    
    hoy = timezone.localdate()
    
    if not fecha_desde:
        fecha_desde = hoy  # ← Cambiar a HOY
    else:
        fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
    
    if not fecha_hasta:
        fecha_hasta = hoy + timedelta(days=14)  # ← Mostrar 2 semanas futuras
    else:
        fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()

    clases = Clase.objects.filter(
        fecha__gte=fecha_desde,
        fecha__lte=fecha_hasta
    ).select_related('id_turno').annotate(
        total_regulares=Count('alumnoclase', filter=Q(alumnoclase__estado__in=['reservado', 'pendiente', 'recuperó', 'asistió', 'faltó'])),
        total_ocasionales=Count('alumnoclaseocasional', filter=Q(alumnoclaseocasional__estado__in=['reservado', 'asistió', 'faltó']))
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
    """Detalle de una clase específica con conteo forzado de inscriptos."""
    from django.db.models import Q, Count

    # 1. Obtenemos la clase pero anotamos los totales filtrando por los estados que "suman"
    clase = get_object_or_404(
        Clase.objects.filter(id_clase=id_clase).select_related(
            'id_turno', 
            'id_instructor__id_persona'
        ).annotate(
            total_reg = Count(
                'alumnoclase', 
                filter=Q(alumnoclase__estado__in=['reservado', 'pendiente', 'recuperó', 'asistió', 'faltó'])
            ),
            total_ocas = Count(
                'alumnoclaseocasional', 
                filter=Q(alumnoclaseocasional__estado__in=['reservado', 'asistió', 'faltó'])
            )
        )
    )
    
    # 2. Creamos la variable 'total' que el HTML necesita para mostrar "X/4"
    clase.total = clase.total_reg + clase.total_ocas

    # Alumnos regulares (para la lista de abajo)
    alumnos_regulares = list(AlumnoClase.objects.filter(
        id_clase=clase,
        estado__in=['reservado', 'pendiente', 'recuperó', 'asistió', 'faltó']
    ).select_related(
        'id_alumno_paquete__id_alumno__id_persona'
    ))
    
    # Identificar alumnos nuevos (primer paquete y primera clase)
    from .models import AlumnoPaquete
    for ac in alumnos_regulares:
        ac.es_nuevo = False
        num_paquetes = AlumnoPaquete.objects.filter(id_alumno=ac.id_alumno_paquete.id_alumno).count()
        if num_paquetes == 1:
            primera_clase = AlumnoClase.objects.filter(
                id_alumno_paquete=ac.id_alumno_paquete
            ).exclude(estado__in=['canceló', 'reprogramó']).order_by('id_clase__fecha', 'id_clase__id_turno__horario').first()
            
            if primera_clase and primera_clase.id_clase == clase:
                ac.es_nuevo = True
    
    # Alumnos ocasionales (para la lista de abajo)
    alumnos_ocasionales = AlumnoClaseOcasional.objects.filter(
        id_clase=clase,
        estado__in=['reservado', 'asistió', 'faltó']
    ).select_related(
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
    
    disciplina_activa = request.GET.get('disciplina', 'Reformer')
    turnos = Turno.objects.filter(disciplina=disciplina_activa).order_by('dia', 'horario')
    
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
        'disciplina_activa': disciplina_activa,
    })


def panel_pagos(request):
    """Lista de paquetes y su estado de pago."""
    estado_pago = request.GET.get('estado', '')
    estado_paquete = request.GET.get('estado_paquete', '')
    
    paquetes = AlumnoPaquete.objects.select_related(
        'id_alumno__id_persona', 'id_paquete'
    ).order_by('-fecha_inicio')
    
    if estado_pago:
        paquetes = paquetes.filter(estado_pago=estado_pago)
    if estado_paquete:
        paquetes = paquetes.filter(estado=estado_paquete)
    
    # Calcular restante y total_pagado para cada paquete
    paquetes_con_info = []
    for paquete in paquetes:
        costo = paquete.id_paquete.costo or Decimal("0")
        
        # Calcular total pagado
        total_pagado = (
            PagoAlumno.objects
            .filter(id_alumno_paquete=paquete, id_pago__estado__in=["pagado", "parcial"])
            .aggregate(total=Sum("id_pago__monto"))
            .get("total") or Decimal("0")
        )
        
        # Calcular restante
        restante = max(Decimal("0"), costo - total_pagado)
        
        # Agregar los campos calculados al objeto paquete
        paquete.restante = restante
        paquete.total_pagado = total_pagado
        paquetes_con_info.append(paquete)
    
    return render(request, 'admin_panel/pagos.html', {
        'paquetes': paquetes_con_info,
        'estado_pago': estado_pago,
        'estado_paquete': estado_paquete,
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
    for ac in (
        AlumnoClase.objects
        .filter(id_clase=clase)
        .select_related('id_alumno_paquete__id_alumno__id_persona')
    ):
        alumno = ac.id_alumno_paquete.id_alumno
        persona = alumno.id_persona

        alumnos.append({
            'id_alumno': alumno.id_alumno,   # 👈 CLAVE
            'nombre': persona.nombre,
            'apellido': persona.apellido,
            'tipo': 'regular',
            'estado': ac.estado,
        })

    # Ocasionales
    for ao in (
        AlumnoClaseOcasional.objects
        .filter(id_clase=clase)
        .select_related('id_alumno__id_persona')
    ):
        alumno = ao.id_alumno
        persona = alumno.id_persona

        alumnos.append({
            'id_alumno': alumno.id_alumno,   # 👈 CLAVE
            'nombre': persona.nombre,
            'apellido': persona.apellido,
            'tipo': 'ocasional',
            'estado': ao.estado,
        })

    return JsonResponse({'alumnos': alumnos})



@require_POST
def panel_turno_eliminar(request, id_turno):
    """Vista para eliminar un turno. Solo si no tiene alumnos activos."""
    turno = get_object_or_404(Turno, id_turno=id_turno)
    
    if turno.lugares_ocupados > 0:
        messages.error(request, "No puedes eliminar un turno que tiene alumnos activos asignados.")
        return redirect('panel_turnos')
        
    turno.delete()
    messages.success(request, "Turno eliminado correctamente.")
    return redirect('panel_turnos')


def api_turno_alumnos(request, id_turno):
    """API para obtener alumnos asignados a un turno (regulares con paquete activo)."""
    turno = get_object_or_404(Turno, id_turno=id_turno)
    
    alumnos = []
    
    # Obtener alumnos que tienen este turno asignado en su paquete
    from .models import AlumnoPaqueteTurno
    
    asignaciones = AlumnoPaqueteTurno.objects.filter(
        id_turno=turno,
        id_alumno_paquete__estado='activo'
    ).select_related(
        'id_alumno_paquete__id_alumno__id_persona',
        'id_alumno_paquete'
    )
    
    for asig in asignaciones:
        alumno_paquete = asig.id_alumno_paquete
        persona = alumno_paquete.id_alumno.id_persona
        alumnos.append({
            'id_alumno': alumno_paquete.id_alumno.id_alumno,
            'nombre': persona.nombre,
            'apellido': persona.apellido,
            'telefono': persona.telefono,
            'estado_paquete': alumno_paquete.estado,
        })
    
    return JsonResponse({'alumnos': alumnos})



## Eliminar alumno
@require_POST
def panel_alumno_eliminar(request, id_alumno):
    """
    Elimina un alumno y sus vínculos operativos, pero CONSERVA todos los datos
    de pagos y facturación (Pago y PagoAlumno) con nombre y datos fiscales
    para mantener la constancia en Facturación.
    """
    alumno = get_object_or_404(Alumno.objects.select_related("id_persona"), id_alumno=id_alumno)
    persona = alumno.id_persona
    telefono = (persona.telefono or "").strip() if persona else ""
    nombre_completo = f"{persona.nombre} {persona.apellido}".strip() if persona else "Alumno"
    ruc_val = (persona.ruc or "").strip() if persona else ""
    razon_social_val = (persona.razon_social or "").strip() if persona else ""

    paquete_ids = list(
        AlumnoPaquete.objects.filter(id_alumno=alumno).values_list("id_alumno_paquete", flat=True)
    )

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

        # 1) PRESERVAR FACTURACIÓN: Guardar nombre, ruc y razón social en los registros de PagoAlumno
        # y desvincular de Alumno y AlumnoPaquete para que queden guardados como constancia contable.
        pagos_alumno = PagoAlumno.objects.filter(
            Q(id_alumno=alumno) | Q(id_alumno_paquete_id__in=paquete_ids)
        )
        for pa in pagos_alumno:
            if not pa.nombre_alumno:
                pa.nombre_alumno = nombre_completo
            if not pa.ruc and ruc_val:
                pa.ruc = ruc_val
            if not pa.razon_social and razon_social_val:
                pa.razon_social = razon_social_val
            pa.id_alumno = None
            pa.id_alumno_paquete = None
            pa.save()

        # 2) Borrado del Alumno (libera turnos y clases operativas)
        alumno.delete()

        # 3) Limpiar Persona solo si ya no está usada por nadie
        if persona:
            persona_sigue_en_alumno = Alumno.objects.filter(id_persona=persona).exists()
            persona_sigue_en_instructor = Instructor.objects.filter(id_persona=persona).exists()
            if (not persona_sigue_en_alumno) and (not persona_sigue_en_instructor):
                persona.delete()

        # 4) Limpiar prospecto por teléfono
        if telefono:
            ClienteProspecto.objects.filter(telefono=telefono).delete()

    messages.success(request, f"Alumno '{nombre_completo}' eliminado. Sus datos de facturación se conservan como constancia.")
    return redirect("panel_alumnos")


def _generar_nro_pago(alumno_paquete: AlumnoPaquete) -> str:
    # Obligatorio en tu modelo. Lo hacemos único y trazable.
    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
  # ej: APQ-123-20260111-193010
    return f"APQ-{alumno_paquete.id_alumno_paquete}-{ts}"


def _total_pagado_paquete(alumno_paquete: AlumnoPaquete) -> Decimal:
    # Suma de pagos asociados al paquete.
    # Tomamos pagos 'pagado' y 'parcial'. Si tuvieras 'pendiente' en pagos reales, podrías excluirlo.
    qs = PagoAlumno.objects.filter(id_alumno_paquete=alumno_paquete).select_related("id_pago")
    total = Decimal("0")
    for pa in qs:
        if pa.id_pago and pa.id_pago.estado in ("pagado", "parcial"):
            total += (pa.id_pago.monto or Decimal("0"))
    return total

@require_POST
@transaction.atomic
def panel_renovar_paquete_alumno(request, id_alumno, id_alumno_paquete):
    # 1. Importamos el servicio y el paquete base
    from .models import Alumno, Paquete, RenovadorPaqueteService
    
    alumno = get_object_or_404(Alumno, id_alumno=id_alumno)
    id_paquete_nuevo = request.POST.get("id_paquete_nuevo")
    paquete_base = get_object_or_404(Paquete, id_paquete=id_paquete_nuevo)

    try:
        # 2. Usamos el Service que ya tienes definido en models.py
        # Le pasamos monto 0 y efectivo por defecto para la renovación rápida
        service = RenovadorPaqueteService(
            alumno_obj=alumno,
            paquete_base_obj=paquete_base,
            monto_pago=Decimal("0"), 
            metodo_pago="efectivo"
        )
        
        # 3. Ejecutamos la lógica (esto creará el paquete, los turnos y el pago)
        nuevo_paquete = service.ejecutar()
        
        # 4. REFUERZO: Creamos las inscripciones a clases para que aparezca el 4/4
        # Buscamos los turnos que el Service acaba de asignar
        turnos_ids = nuevo_paquete.alumnopaqueteturno_set.values_list('id_turno_id', flat=True)
        
        clases_futuras = Clase.objects.filter(
            id_turno_id__in=turnos_ids,
            fecha__gte=timezone.now().date()
        ).order_by('fecha')[:paquete_base.cantidad_clases]

        for clase in clases_futuras:
            AlumnoClase.objects.get_or_create(
                id_alumno_paquete=nuevo_paquete,
                id_clase=clase,
                defaults={'estado': 'pendiente'}
            )
            # Forzamos refresco del contador en la clase
            clase.save()

        messages.success(request, f"Paquete de {paquete_base.cantidad_clases} clases renovado y cupos reservados.")
        
    except Exception as e:
        messages.error(request, f"Error al renovar: {str(e)}")

    return redirect("panel_alumno_detalle", id_alumno=id_alumno)


@require_POST
@transaction.atomic
def panel_registrar_pago_alumno(request, id_alumno):
    alumno = get_object_or_404(Alumno, id_alumno=id_alumno)
    id_alumno_paquete = request.POST.get("id_alumno_paquete")
    
    if id_alumno_paquete:
        alumno_paquete = get_object_or_404(
            AlumnoPaquete,
            id_alumno_paquete=id_alumno_paquete,
            id_alumno=alumno
        )
    else:
        alumno_paquete = None

    monto_raw = (request.POST.get("monto") or "").strip()
    metodo_pago = (request.POST.get("metodo_pago") or "").strip()
    comprobante = (request.POST.get("comprobante") or "").strip()
    observaciones = (request.POST.get("observaciones") or "").strip()

    errores = []

    if not monto_raw:
        errores.append("Debes ingresar un monto.")
    if metodo_pago not in ("efectivo", "tarjeta", "transferencia"):
        errores.append("Debes seleccionar un método de pago válido.")

    try:
        monto = Decimal(monto_raw)
        if monto <= 0:
            errores.append("El monto debe ser mayor que 0.")
    except (InvalidOperation, ValueError):
        errores.append("El monto no tiene un formato válido.")

    if errores:
        for error in errores:
            messages.error(request, error)
        return redirect("panel_alumno_detalle", id_alumno=alumno.id_alumno)

    if alumno_paquete:
        # Costo del paquete y acumulado anterior
        costo = alumno_paquete.id_paquete.costo or Decimal("0")

        total_pagado_antes = (
            PagoAlumno.objects
            .filter(id_alumno_paquete=alumno_paquete, id_pago__estado__in=["pagado", "parcial"])
            .aggregate(total=Sum("id_pago__monto"))
            .get("total") or Decimal("0")
        )

        restante_antes = max(Decimal("0"), costo - total_pagado_antes)

        # Estado del pago creado (según lo que faltaba en ese momento)
        estado_pago_creado = "pagado" if monto >= restante_antes else "parcial"
        nro_pago = f"APQ-{alumno_paquete.id_alumno_paquete}-{timezone.now().strftime('%Y%m%d-%H%M%S')}"
    else:
        estado_pago_creado = "pagado"
        nro_pago = f"ADV-{alumno.id_alumno}-{timezone.now().strftime('%Y%m%d-%H%M%S')}"

    pago = Pago.objects.create(
        fecha=timezone.localdate(),
        monto=monto,
        metodo_pago=metodo_pago,
        comprobante=comprobante,
        estado=estado_pago_creado,
        nro_pago=nro_pago,
    )

    nombre_al = f"{alumno.id_persona.nombre} {alumno.id_persona.apellido}".strip() if alumno and alumno.id_persona else "Alumno"
    ruc_al = alumno.id_persona.ruc if alumno and alumno.id_persona else None
    rs_al = alumno.id_persona.razon_social if alumno and alumno.id_persona else None

    PagoAlumno.objects.create(
        id_pago=pago,
        id_alumno=alumno,
        id_alumno_paquete=alumno_paquete,
        nombre_alumno=nombre_al,
        ruc=ruc_al,
        razon_social=rs_al,
        observaciones=observaciones
    )

    if alumno_paquete:
        # Volvemos a calcular el total pagado (incluyendo el actual)
        total_nuevo = (
            PagoAlumno.objects
            .filter(id_alumno_paquete=alumno_paquete, id_pago__estado__in=["pagado", "parcial"])
            .aggregate(total=Sum("id_pago__monto"))
            .get("total") or Decimal("0")
        )

        # Actualizar estado de pago del paquete
        if total_nuevo >= costo:
            alumno_paquete.estado_pago = "pagado"
        else:
            alumno_paquete.estado_pago = "parcial"
            
        alumno_paquete.save()
    
    messages.success(request, "Pago registrado correctamente.")
    
    next_page = request.GET.get('next', 'detalle')
    if next_page == 'pagos':
        return redirect("panel_pagos")
    else:
        return redirect("panel_alumno_detalle", id_alumno=alumno.id_alumno)

def panel_feriados(request):
    from .models import Feriado
    from datetime import datetime
    
    if request.method == "POST":
        fecha_str = request.POST.get("fecha")
        descripcion = request.POST.get("descripcion", "")
        if fecha_str:
            try:
                fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                Feriado.objects.get_or_create(fecha=fecha_obj, defaults={"descripcion": descripcion})
                messages.success(request, "Feriado agregado correctamente.")
            except Exception as e:
                messages.error(request, f"Error al agregar feriado: {e}")
        return redirect("panel_feriados")
        
    feriados = Feriado.objects.all().order_by("-fecha")
    return render(request, "admin_panel/feriados/lista.html", {"feriados": feriados})

def panel_feriados_eliminar(request, fecha_str):
    from .models import Feriado
    from datetime import datetime
    
    if request.method == "POST":
        try:
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            feriado = get_object_or_404(Feriado, fecha=fecha_obj)
            feriado.delete()
            messages.success(request, "Feriado eliminado correctamente.")
        except Exception as e:
            messages.error(request, f"Error al eliminar feriado: {e}")
            
    return redirect("panel_feriados")


@require_http_methods(["GET", "POST"])
def panel_reemplazos(request):
    from .models import ReemplazoDia
    from datetime import datetime
    
    if request.method == "POST":
        fecha_str = request.POST.get("fecha")
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                ReemplazoDia.objects.get_or_create(fecha=fecha)
                messages.success(request, f"Día de reemplazo agregado para el {fecha.strftime('%d/%m/%Y')}.")
            except ValueError:
                messages.error(request, "Fecha inválida.")
            except Exception as e:
                messages.error(request, f"Error: {e}")
        return redirect("panel_reemplazos")
        
    reemplazos = ReemplazoDia.objects.all().order_by("-fecha")
    return render(request, "admin_panel/reemplazos.html", {"reemplazos": reemplazos})

@require_POST
def panel_reemplazos_eliminar(request, fecha_str):
    from .models import ReemplazoDia
    from datetime import datetime
    
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        ReemplazoDia.objects.filter(fecha=fecha).delete()
        messages.success(request, f"Día de reemplazo ({fecha.strftime('%d/%m/%Y')}) eliminado.")
    except ValueError:
        messages.error(request, "Fecha inválida.")
    except Exception as e:
        messages.error(request, f"Error al eliminar: {e}")
        
    return redirect("panel_reemplazos")

# --- VISTAS PARA PROFES (ACCESO DIRECTO MAGICO) ---


def profes_clases_hoy(request, token):
    from django.utils import timezone
    from datetime import datetime
    from .models import ReemplazoDia
    
    # Validar token (ambos tokens ahora muestran ambas disciplinas)
    es_reemplazo = False
    if token == "reemplazo":
        # Check if today is a ReemplazoDia
        if not ReemplazoDia.objects.filter(fecha=timezone.now().date()).exists():
            return HttpResponse("El acceso para reemplazantes no está habilitado hoy.", status=403)
        es_reemplazo = True
    elif token not in ["acceso-profes", "acceso-profes-mat"]:
        return HttpResponse("Acceso denegado. Token inválido.", status=403)
        
    # Obtener fecha
    fecha_str = request.GET.get("fecha")
    if fecha_str and not es_reemplazo:
        try:
            hoy = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            hoy = timezone.now().date()
    else:
        hoy = timezone.now().date()
    
    # Obtener nombre del día
    dias_semana = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
    nombre_dia = dias_semana[hoy.weekday()]
    
    # Buscar turnos de hoy
    from .models import Turno
    turnos_hoy = Turno.objects.filter(dia__iexact=nombre_dia).order_by('horario')
    
    # Buscar todas las clases de hoy (SIN FILTRAR DISCIPLINA)
    clases_hoy = Clase.objects.filter(fecha=hoy).select_related('id_turno')
    
    clases_data = []
    turnos_procesados = set()
    
    for clase in clases_hoy:
        if clase.id_turno:
            turnos_procesados.add(clase.id_turno_id)
            
        alumnos_lista = []
        
        # Alumnos regulares (excluimos canceló y reprogramó)
        alumnos_regulares = AlumnoClase.objects.filter(
            id_clase=clase
        ).exclude(
            estado__in=['canceló', 'reprogramó', 'feriado']
        ).select_related('id_alumno_paquete__id_alumno__id_persona')
        
        for ac in alumnos_regulares:
            persona = ac.id_alumno_paquete.id_alumno.id_persona
            alumnos_lista.append({
                'id_relacion': ac.id_alumno_clase,
                'nombre_completo': f"{persona.nombre} {persona.apellido}",
                'estado': ac.estado,
                'tipo': 'regular'
            })
            
        # Alumnos ocasionales (excluimos canceló)
        alumnos_ocasionales = AlumnoClaseOcasional.objects.filter(
            id_clase=clase
        ).exclude(
            estado='canceló'
        ).select_related('id_alumno__id_persona')
        
        for ao in alumnos_ocasionales:
            persona = ao.id_alumno.id_persona
            alumnos_lista.append({
                'id_relacion': ao.id_alumno_clase_ocasional,
                'nombre_completo': f"{persona.nombre} {persona.apellido} (Ocasional)",
                'estado': ao.estado,
                'tipo': 'ocasional'
            })
            
        clases_data.append({
            'clase': clase,
            'horario': clase.id_turno.horario.strftime('%H:%M') if clase.id_turno else 'S/H',
            'disciplina': clase.id_turno.disciplina if clase.id_turno else 'Reformer',
            'alumnos': alumnos_lista,
            'orden': clase.id_turno.horario.strftime('%H:%M') if clase.id_turno else '23:59'
        })
        
    # Agregar turnos sin clases
    for turno in turnos_hoy:
        if turno.id_turno not in turnos_procesados:
            clases_data.append({
                'clase': None,
                'horario': turno.horario.strftime('%H:%M'),
                'disciplina': turno.disciplina,
                'alumnos': [],
                'orden': turno.horario.strftime('%H:%M')
            })
            
    # Ordenar por horario
    clases_data.sort(key=lambda x: x['orden'])
        
    # -----------------------------------------------------
    # ALERTAS DE ASISTENCIA PENDIENTE (SOLO PARA PROFES REGULARES)
    # -----------------------------------------------------
    fechas_alertas = set()
    if not es_reemplazo:
        # Últimos 7 días (excluyendo domingos y hoy)
        from datetime import timedelta
        
        for i in range(1, 8):
            fecha_check = hoy - timedelta(days=i)
            # Solo verificamos si no es domingo (weekday() == 6)
            if fecha_check.weekday() != 6: 
                nombre_d = dias_semana[fecha_check.weekday()]
                hay_clases_ese_dia = Turno.objects.filter(dia__iexact=nombre_d).exists()
                
                if hay_clases_ese_dia:
                    # ¿Hay algún AlumnoClase en estado 'reservado' en esa fecha?
                    hay_pendientes = AlumnoClase.objects.filter(
                        id_clase__fecha=fecha_check,
                        estado='reservado'
                    ).exists()
                    
                    if hay_pendientes:
                        fechas_alertas.add(fecha_check)

    from .models import HonorarioInstructor
    
    honorarios_hoy = HonorarioInstructor.objects.filter(fecha=hoy)
    
    return render(request, "admin_panel/profes/clases_hoy.html", {
        "honorarios_hoy": honorarios_hoy,

        "clases_data": clases_data,
        "fecha_hoy": hoy,
        "token": token,
        "fechas_alertas": sorted(list(fechas_alertas)),
        "es_reemplazo": es_reemplazo,
    })

def profes_marcar_asistencia(request, token):
    from django.utils import timezone
    from .models import ReemplazoDia
    if token == "reemplazo":
        if not ReemplazoDia.objects.filter(fecha=timezone.now().date()).exists():
            return HttpResponse("Acceso denegado. Enlace no habilitado hoy.", status=403)
    elif token not in ["acceso-profes", "acceso-profes-mat"]:
        return HttpResponse("Acceso denegado.", status=403)
        
    if request.method == "POST":
        fecha_str = request.POST.get("fecha", "")
        tipo = request.POST.get("tipo")
        id_relacion = request.POST.get("id_relacion")
        nuevo_estado = request.POST.get("estado")
        if nuevo_estado:
            nuevo_estado = nuevo_estado.lower()
        
        try:
            if tipo == 'regular':
                rel = AlumnoClase.objects.select_related('id_alumno_paquete__id_alumno').get(pk=id_relacion)
                
                # REASIGNACIÓN AUTOMÁTICA SI EL PAQUETE ESTÁ EXPIRADO
                if rel.id_alumno_paquete.estado == 'expirado':
                    paquete_activo = AlumnoPaquete.objects.filter(
                        id_alumno=rel.id_alumno_paquete.id_alumno,
                        estado='activo'
                    ).first()
                    
                    if paquete_activo:
                        # Verificar si el paquete activo ya tiene esta misma clase registrada
                        existente = AlumnoClase.objects.filter(
                            id_alumno_paquete=paquete_activo,
                            id_clase=rel.id_clase
                        ).first()
                        
                        if existente:
                            # Si ya existe, actualizamos el del paquete activo y eliminamos el duplicado viejo
                            existente.estado = nuevo_estado
                            existente.save()
                            rel.delete()
                        else:
                            # Si no existe en el paquete activo, se lo transferimos
                            rel.id_alumno_paquete = paquete_activo
                            rel.estado = nuevo_estado
                            rel.save()
                    else:
                        # Si no hay paquete activo, igual guardamos el estado (quedará en el expirado)
                        rel.estado = nuevo_estado
                        rel.save()
                else:
                    rel.estado = nuevo_estado
                    rel.save()
                    
            elif tipo == 'ocasional':
                rel = AlumnoClaseOcasional.objects.get(pk=id_relacion)
                rel.estado = nuevo_estado
                rel.save()
                
            messages.success(request, "Asistencia actualizada.")
        except Exception as e:
            messages.error(request, f"Error al actualizar: {e}")
            
    url = redirect("profes_clases_hoy", token=token)
    if fecha_str:
        url['Location'] += f"?fecha={fecha_str}"
    return url


def profes_pagos(request, token):
    if token == "reemplazo":
        return HttpResponse("Acceso denegado para reemplazos.", status=403)
    if token not in ["acceso-profes", "acceso-profes-mat"]:
        return HttpResponse("Acceso denegado.", status=403)
        
    # All active packages to show in datalist
    paquetes = AlumnoPaquete.objects.filter(
        estado='activo'
    ).select_related('id_alumno__id_persona', 'id_paquete')
    
    # All instructores for datalist
    instructoras = Instructor.objects.select_related('id_persona').all()
    
    context = {
        'token': token,
        'paquetes': paquetes,
        'instructoras': instructoras,
    }
    return render(request, "admin_panel/profes/pagos.html", context)


@require_POST
@transaction.atomic
def profes_registrar_pago(request, token):
    if token == "reemplazo":
        return HttpResponse("Acceso denegado para reemplazos.", status=403)
    if token not in ["acceso-profes", "acceso-profes-mat"]:
        return HttpResponse("Acceso denegado.", status=403)
        
    id_alumno_paquete = request.POST.get("id_alumno_paquete")
    alumna_nombre = request.POST.get("alumna_nombre")
    monto_raw = request.POST.get("monto")
    metodo_pago = request.POST.get("metodo_pago")
    profe_nombre = request.POST.get("profe_nombre")
    concepto = request.POST.get("concepto")
    fecha_str = request.POST.get("fecha")
    
    try:
        monto = Decimal(monto_raw) if monto_raw else Decimal(0)
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else timezone.now().date()
        
        observaciones_pago = f"Cobrado por: {profe_nombre}"
        
        if id_alumno_paquete:
            # Pago asociado a un paquete real
            paquete_actual = AlumnoPaquete.objects.get(pk=id_alumno_paquete)
            
            # Asumimos que salda la deuda (si el frontend no maneja renovar por ahora)
            nuevo_pago = Pago.objects.create(
                fecha=fecha,
                monto=monto,
                metodo_pago=metodo_pago,
                estado="pagado",
                nro_pago=f"SALDO-{paquete_actual.id_alumno_paquete}"
            )
            p_alumno = paquete_actual.id_alumno
            nombre_al = f"{p_alumno.id_persona.nombre} {p_alumno.id_persona.apellido}".strip() if p_alumno and p_alumno.id_persona else "Alumna"
            ruc_al = p_alumno.id_persona.ruc if p_alumno and p_alumno.id_persona else None
            rs_al = p_alumno.id_persona.razon_social if p_alumno and p_alumno.id_persona else None

            PagoAlumno.objects.create(
                id_pago=nuevo_pago,
                id_alumno=p_alumno,
                id_alumno_paquete=paquete_actual,
                nombre_alumno=nombre_al,
                ruc=ruc_al,
                razon_social=rs_al,
                observaciones=observaciones_pago
            )
            paquete_actual.estado_pago = "pagado"
            paquete_actual.save()
            messages.success(request, f"Pago registrado con éxito a {paquete_actual.id_alumno.id_persona.nombre}.")
        else:
            # Pago genérico/manual sin paquete asociado
            # Creamos un pago genérico con comprobante/notas
            observaciones_completas = f"Alumna (manual): {alumna_nombre} | Concepto: {concepto} | {observaciones_pago}"
            nuevo_pago = Pago.objects.create(
                fecha=fecha,
                monto=monto,
                metodo_pago=metodo_pago,
                estado="pagado",
                nro_pago=f"MANUAL-{int(timezone.now().timestamp())}",
                comprobante=observaciones_completas
            )
            # No creamos PagoAlumno porque no hay paquete
            messages.success(request, f"Pago manual registrado con éxito para {alumna_nombre}.")
            
    except Exception as e:
        messages.error(request, f"Error al procesar el pago: {e}")
        
    return redirect("profes_pagos", token=token)



@require_POST
def panel_pago_actualizar_factura(request, id_pago):
    try:
        pago = get_object_or_404(Pago, pk=id_pago)
        nro_factura = request.POST.get("nro_factura", "").strip()
        
        if nro_factura:
            pago.nro_pago = nro_factura
            pago.save()
            messages.success(request, "Número de factura actualizado correctamente.")
        else:
            messages.warning(request, "El número de factura no puede estar vacío.")
            
    except Exception as e:
        messages.error(request, f"Error al actualizar factura: {e}")
        
    return redirect(request.META.get('HTTP_REFERER', 'panel_resumen_pagos'))

@require_POST
def panel_pago_eliminar(request, id_pago):
    try:
        pago = get_object_or_404(Pago, pk=id_pago)
        
        # Revert AlumnoPaquete status if it exists
        pago_alumnos = PagoAlumno.objects.filter(id_pago=pago)
        for pa in pago_alumnos:
            paquete = pa.id_alumno_paquete
            if paquete:
                paquete.estado_pago = 'pendiente'
                paquete.save()
            
        pago.delete()
        messages.success(request, "Pago eliminado correctamente.")
    except Exception as e:
        messages.error(request, f"Error al eliminar pago: {e}")
        
    return redirect(request.META.get('HTTP_REFERER', 'panel_resumen_pagos'))

def panel_resumen_pagos(request):
    mes_str = request.GET.get("mes")
    if mes_str:
        try:
            mes_actual = datetime.strptime(mes_str, "%Y-%m").date()
        except ValueError:
            mes_actual = timezone.now().date().replace(day=1)
    else:
        mes_actual = timezone.now().date().replace(day=1)
        
    # Obtener el primer y último día del mes
    import calendar
    _, last_day = calendar.monthrange(mes_actual.year, mes_actual.month)
    fin_mes = mes_actual.replace(day=last_day)
    
    pagos = Pago.objects.filter(
        fecha__gte=mes_actual,
        fecha__lte=fin_mes,
        estado__in=["pagado", "parcial"]
    )
    
    estado_factura = request.GET.get('estado_factura')
    if estado_factura == 'falta':
        pagos = pagos.filter(
            Q(nro_pago__isnull=True) | 
            Q(nro_pago__exact="") | 
            Q(nro_pago__startswith="MANUAL-") | 
            Q(nro_pago__startswith="APQ-")
        )
    elif estado_factura == 'facturado':
        pagos = pagos.exclude(
            Q(nro_pago__isnull=True) | 
            Q(nro_pago__exact="") | 
            Q(nro_pago__startswith="MANUAL-") | 
            Q(nro_pago__startswith="APQ-")
        )
        
    pagos = pagos.order_by("-fecha")
    
    # Calcular totales del mes
    total_efectivo = pagos.filter(metodo_pago="efectivo").aggregate(total=Sum("monto"))["total"] or Decimal("0")
    total_transferencia = pagos.filter(metodo_pago="transferencia").aggregate(total=Sum("monto"))["total"] or Decimal("0")
    total_general = total_efectivo + total_transferencia
    
    # Ventas de productos del mes
    ventas_mes = MovimientoProducto.objects.filter(
        tipo='venta',
        fecha__gte=mes_actual,
        fecha__lte=fin_mes
    ).aggregate(total=Sum("monto_total"))["total"] or Decimal("0")
    
    # Gastos operativos del mes
    gastos_mes = Gasto.objects.filter(
        fecha__gte=mes_actual,
        fecha__lte=fin_mes
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0")
    
    # Honorarios de profes del mes
    honorarios_mes = HonorarioInstructor.objects.filter(
        fecha__gte=mes_actual,
        fecha__lte=fin_mes
    ).aggregate(total=Sum("monto_total"))["total"] or Decimal("0")
    
    egresos_totales_mes = gastos_mes + honorarios_mes
    ingresos_totales_mes = total_general + ventas_mes
    balance_neto_mes = ingresos_totales_mes - egresos_totales_mes
    
    # DATOS PARA GRÁFICOS: Últimos 6 meses
    meses_historial = []
    base_date = mes_actual
    for i in range(5, -1, -1):
        year = base_date.year
        month = base_date.month - i
        while month <= 0:
            month += 12
            year -= 1
        m_start = date(year, month, 1)
        _, m_last_day = calendar.monthrange(year, month)
        m_end = date(year, month, m_last_day)
        
        m_ing_clases = Pago.objects.filter(
            fecha__gte=m_start, fecha__lte=m_end, estado__in=["pagado", "parcial"]
        ).aggregate(total=Sum("monto"))["total"] or Decimal("0")
        
        m_ing_ventas = MovimientoProducto.objects.filter(
            tipo='venta', fecha__gte=m_start, fecha__lte=m_end
        ).aggregate(total=Sum("monto_total"))["total"] or Decimal("0")
        
        m_total_ing = m_ing_clases + m_ing_ventas
        
        m_gastos = Gasto.objects.filter(
            fecha__gte=m_start, fecha__lte=m_end
        ).aggregate(total=Sum("monto"))["total"] or Decimal("0")
        
        m_honorarios = HonorarioInstructor.objects.filter(
            fecha__gte=m_start, fecha__lte=m_end
        ).aggregate(total=Sum("monto_total"))["total"] or Decimal("0")
        
        m_total_egresos = m_gastos + m_honorarios
        m_neto = m_total_ing - m_total_egresos
        
        nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        mes_nombre = f"{nombres_meses[month - 1]} {year}"
        
        meses_historial.append({
            "label": mes_nombre,
            "ingresos_clases": float(m_ing_clases),
            "ingresos_ventas": float(m_ing_ventas),
            "ingresos_totales": float(m_total_ing),
            "gastos": float(m_total_egresos),
            "neto": float(m_neto)
        })
        
    chart_labels = [m["label"] for m in meses_historial]
    chart_ingresos = [m["ingresos_totales"] for m in meses_historial]
    chart_gastos = [m["gastos"] for m in meses_historial]
    chart_neto = [m["neto"] for m in meses_historial]
    
    # Desglose de Gastos por categoría para el mes actual
    gastos_por_cat = Gasto.objects.filter(
        fecha__gte=mes_actual, fecha__lte=fin_mes
    ).values("categoria").annotate(total=Sum("monto")).order_by("-total")
    
    cat_nombres_dict = dict(Gasto.CATEGORIA_CHOICES)
    chart_gastos_cat_labels = [cat_nombres_dict.get(g["categoria"], g["categoria"]) for g in gastos_por_cat]
    chart_gastos_cat_data = [float(g["total"]) for g in gastos_por_cat]
    
    if honorarios_mes > 0:
        chart_gastos_cat_labels.append("Honorarios Profes")
        chart_gastos_cat_data.append(float(honorarios_mes))

    context = {
        "mes_actual": mes_actual,
        "pagos": pagos,
        "total_efectivo": total_efectivo,
        "total_transferencia": total_transferencia,
        "total_general": total_general,
        "ventas_mes": ventas_mes,
        "gastos_mes": gastos_mes,
        "honorarios_mes": honorarios_mes,
        "egresos_totales_mes": egresos_totales_mes,
        "ingresos_totales_mes": ingresos_totales_mes,
        "balance_neto_mes": balance_neto_mes,
        
        # Para Chart.js
        "chart_labels_json": json.dumps(chart_labels),
        "chart_ingresos_json": json.dumps(chart_ingresos),
        "chart_gastos_json": json.dumps(chart_gastos),
        "chart_neto_json": json.dumps(chart_neto),
        "chart_gastos_cat_labels_json": json.dumps(chart_gastos_cat_labels),
        "chart_gastos_cat_data_json": json.dumps(chart_gastos_cat_data),
    }
    return render(request, "admin_panel/pagos/resumen.html", context)



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

@require_POST
def profes_registrar_honorario(request, token):
    from django.utils import timezone
    from datetime import datetime
    from .models import Instructor, HonorarioInstructor
    
    # Validar token
    if token not in ["acceso-profes", "acceso-profes-mat"]:
        return HttpResponse("Acceso denegado. Token inválido.", status=403)
        
    fecha_str = request.POST.get("fecha")
    nombre_profesora = request.POST.get("nombre_profesora", "").strip()
    turno = request.POST.get("turno")
    cantidad_clases = request.POST.get("cantidad_clases", 1)
    monto_total = request.POST.get("monto_total", 0)
    
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        
        HonorarioInstructor.objects.create(
            nombre_profesora=nombre_profesora,
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


def panel_honorarios_resumen(request):
    from .models import HonorarioInstructor, Instructor, Clase
    from django.db.models import Sum
    from datetime import datetime, timedelta, time
    from django.utils import timezone
    
    filtro_mes = request.GET.get('mes', timezone.now().strftime('%Y-%m'))
    
    try:
        año, mes = map(int, filtro_mes.split('-'))
    except ValueError:
        año, mes = timezone.now().year, timezone.now().month
        
    # 1. Obtener honorarios del mes seleccionado
    honorarios = HonorarioInstructor.objects.filter(
        fecha__year=año,
        fecha__month=mes
    ).order_by('fecha')
    
    resumen = {}
    for h in honorarios:
        nombre_prof = h.nombre_profesora
        if nombre_prof not in resumen:
            resumen[nombre_prof] = {
                'nombre': nombre_prof,
                'dias': {},
                'total_clases': 0,
                'total_monto': 0
            }
            
        fecha_str = h.fecha.strftime('%d/%m')
        if fecha_str not in resumen[nombre_prof]['dias']:
            resumen[nombre_prof]['dias'][fecha_str] = {'clases': 0, 'monto': 0, 'detalle': []}
            
        resumen[nombre_prof]['dias'][fecha_str]['clases'] += h.cantidad_clases
        resumen[nombre_prof]['dias'][fecha_str]['monto'] += h.monto_total
        resumen[nombre_prof]['dias'][fecha_str]['detalle'].append({
            'id': h.id_honorario,
            'texto': f"{h.turno}: {h.cantidad_clases}c ({h.monto_total} Gs)"
        })
        
        resumen[nombre_prof]['total_clases'] += h.cantidad_clases
        resumen[nombre_prof]['total_monto'] += h.monto_total

    # 2. Obtener cruce automático de clases
    clases_impartidas = Clase.objects.filter(
        fecha__year=año,
        fecha__month=mes
    ).select_related('id_instructor__id_persona', 'id_turno').order_by('fecha')
    
    cruce_clases = {}
    for c in clases_impartidas:
        nombre_prof = f"{c.id_instructor.id_persona.nombre} {c.id_instructor.id_persona.apellido}"
        if nombre_prof not in cruce_clases:
            cruce_clases[nombre_prof] = {
                'nombre': nombre_prof,
                'semanas': {},
                'total_clases': 0
            }
            
        iso_week = c.fecha.isocalendar()[1]
        if iso_week not in cruce_clases[nombre_prof]['semanas']:
            cruce_clases[nombre_prof]['semanas'][iso_week] = {
                'dias': {},
                'total_semana': 0,
                'inicio': c.fecha,
                'fin': c.fecha,
                'numero': 0
            }
            
        semana = cruce_clases[nombre_prof]['semanas'][iso_week]
        if c.fecha < semana['inicio']: semana['inicio'] = c.fecha
        if c.fecha > semana['fin']: semana['fin'] = c.fecha
        
        fecha_str = c.fecha.strftime('%d/%m')
        if fecha_str not in semana['dias']:
            semana['dias'][fecha_str] = {'mañana': 0, 'tarde': 0, 'mat_mj': 0, 'total': 0, 'fecha_obj': c.fecha}
            
        is_tarde = c.id_turno.horario >= time(12, 0)
        is_mj = c.id_turno.dia in ['Martes', 'Jueves']
        is_1830_1930 = c.id_turno.horario in [time(18, 30), time(19, 30)]
        is_mat = c.id_turno.disciplina.lower() == 'mat'
        
        if is_mj and is_1830_1930 and is_mat:
            semana['dias'][fecha_str]['mat_mj'] += 1
        elif is_tarde:
            semana['dias'][fecha_str]['tarde'] += 1
        else:
            semana['dias'][fecha_str]['mañana'] += 1
            
        semana['dias'][fecha_str]['total'] += 1
        semana['total_semana'] += 1
        cruce_clases[nombre_prof]['total_clases'] += 1

    # Format weeks dictionary and assign sequence number
    for nombre_prof, datos in cruce_clases.items():
        sorted_weeks = sorted(datos['semanas'].keys())
        semanas_dict = {}
        for idx, w in enumerate(sorted_weeks):
            semanas_dict[w] = datos['semanas'][w]
            semanas_dict[w]['numero'] = idx + 1
        datos['semanas'] = semanas_dict

    context = {
        'filtro_mes': filtro_mes,
        'resumen': resumen,
        'cruce_clases': cruce_clases,
    }
    return render(request, "admin_panel/honorarios/resumen.html", context)


@require_POST
def panel_registrar_honorario(request):
    from django.utils import timezone
    from datetime import datetime
    from .models import Instructor, HonorarioInstructor
    
    fecha_str = request.POST.get("fecha")
    nombre_profesora = request.POST.get("nombre_profesora", "").strip()
    turno = request.POST.get("turno")
    cantidad_clases = request.POST.get("cantidad_clases", 1)
    monto_total = request.POST.get("monto_total", 0)
    
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        
        HonorarioInstructor.objects.create(
            nombre_profesora=nombre_profesora,
            fecha=fecha,
            turno=turno,
            cantidad_clases=int(cantidad_clases),
            monto_total=float(monto_total)
        )
        messages.success(request, f"Honorario de {monto_total} Gs. guardado correctamente.")
    except Exception as e:
        messages.error(request, f"Error al guardar honorario: {e}")
        
    return redirect("panel_honorarios_resumen")

def profes_honorarios(request, token):
    from django.utils import timezone
    from datetime import datetime
    from .models import ReemplazoDia, HonorarioInstructor
    
    if token == "reemplazo":
        if not ReemplazoDia.objects.filter(fecha=timezone.now().date()).exists():
            return HttpResponse("El acceso para reemplazantes no está habilitado hoy.", status=403)
    elif token not in ["acceso-profes", "acceso-profes-mat"]:
        return HttpResponse("Acceso denegado. Token inválido.", status=403)
        
    fecha_str = request.GET.get("fecha")
    if fecha_str and token != "reemplazo":
        try:
            hoy = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            hoy = timezone.now().date()
    else:
        hoy = timezone.now().date()
        
    honorarios_hoy = HonorarioInstructor.objects.filter(fecha=hoy)
    
    return render(request, "admin_panel/profes/honorarios.html", {
        "honorarios_hoy": honorarios_hoy,
        "fecha_hoy": hoy,
        "token": token,
    })

@require_POST
def panel_eliminar_honorario(request):
    from .models import HonorarioInstructor
    id_honorario = request.POST.get("id_honorario")
    try:
        h = HonorarioInstructor.objects.get(pk=id_honorario)
        h.delete()
        messages.success(request, "Honorario eliminado correctamente.")
    except Exception as e:
        messages.error(request, f"Error al eliminar honorario: {e}")
        
    # Redirigir de vuelta al panel de resumen conservando el mes filtrado
    url = redirect("panel_honorarios_resumen")
    referer = request.META.get('HTTP_REFERER')
    if referer and 'mes=' in referer:
        import urllib.parse
        parsed_url = urllib.parse.urlparse(referer)
        url['Location'] += '?' + parsed_url.query
    return url

@require_POST
def profes_eliminar_honorario(request, token):
    from .models import HonorarioInstructor
    
    if token not in ["acceso-profes", "acceso-profes-mat"]:
        return HttpResponse("Acceso denegado. Token inválido.", status=403)
        
    id_honorario = request.POST.get("id_honorario")
    try:
        h = HonorarioInstructor.objects.get(pk=id_honorario)
        h.delete()
        messages.success(request, "Honorario eliminado correctamente.")
    except Exception as e:
        messages.error(request, f"Error al eliminar honorario: {e}")
        
    url = redirect("profes_clases_hoy", token=token)
    fecha_str = request.POST.get("fecha")
    if fecha_str:
        url['Location'] += f"?fecha={fecha_str}"
    return url


# ==========================================
# MÓDULO DE INVENTARIO ("EL ESTANTE")
# ==========================================

def panel_inventario(request):
    """
    Vista del estante de inventario: productos, stock disponible, ventas y movimientos.
    """
    if not Producto.objects.exists():
        p1 = Producto.objects.create(
            nombre="Medias Antideslizantes",
            descripcion="Medias especiales antideslizantes para pilates",
            precio_venta=Decimal("40000"),
            stock_actual=12
        )
        MovimientoProducto.objects.create(
            producto=p1,
            tipo='entrada',
            cantidad=12,
            monto_total=Decimal("0"),
            observaciones="Carga inicial de stock"
        )
        p2 = Producto.objects.create(
            nombre="Yoga Mat",
            descripcion="Mat / Colchoneta para ejercicios de suelo y mat",
            precio_venta=Decimal("120000"),
            stock_actual=5
        )
        MovimientoProducto.objects.create(
            producto=p2,
            tipo='entrada',
            cantidad=5,
            monto_total=Decimal("0"),
            observaciones="Carga inicial de stock"
        )

    productos = Producto.objects.filter(activo=True).order_by("nombre")
    
    total_productos = productos.count()
    total_unidades = sum(p.stock_actual for p in productos)
    productos_bajo_stock = productos.filter(stock_actual__lte=3)
    
    hoy = timezone.localdate()
    mes_inicio = hoy.replace(day=1)
    import calendar
    _, last_day = calendar.monthrange(hoy.year, hoy.month)
    mes_fin = hoy.replace(day=last_day)
    
    ventas_mes = MovimientoProducto.objects.filter(
        tipo='venta',
        fecha__gte=mes_inicio,
        fecha__lte=mes_fin
    ).aggregate(total=Sum("monto_total"))["total"] or Decimal("0")
    
    movimientos = MovimientoProducto.objects.select_related(
        'producto', 'id_alumno__id_persona'
    ).order_by("-fecha", "-id_movimiento")[:50]
    
    alumnos = Alumno.objects.filter(estado="regular").select_related("id_persona").order_by("id_persona__nombre")

    context = {
        "productos": productos,
        "total_productos": total_productos,
        "total_unidades": total_unidades,
        "productos_bajo_stock": productos_bajo_stock,
        "ventas_mes": ventas_mes,
        "movimientos": movimientos,
        "alumnos": alumnos,
        "hoy": hoy,
    }
    return render(request, "admin_panel/inventario/lista.html", context)


@require_POST
def panel_producto_crear(request):
    nombre = request.POST.get("nombre", "").strip()
    descripcion = request.POST.get("descripcion", "").strip()
    precio_str = request.POST.get("precio_venta", "0").replace(".", "").replace(",", "").strip()
    stock_str = request.POST.get("stock_actual", "0").strip()
    
    if not nombre:
        messages.error(request, "El nombre del producto es obligatorio.")
        return redirect("panel_inventario")
        
    try:
        precio = Decimal(precio_str)
    except (InvalidOperation, ValueError):
        precio = Decimal("0")
        
    try:
        stock = int(stock_str)
    except ValueError:
        stock = 0
        
    producto = Producto.objects.create(
        nombre=nombre,
        descripcion=descripcion if descripcion else None,
        precio_venta=precio,
        stock_actual=stock
    )
    
    if stock > 0:
        MovimientoProducto.objects.create(
            producto=producto,
            tipo='entrada',
            cantidad=stock,
            precio_unitario=Decimal("0"),
            monto_total=Decimal("0"),
            observaciones="Stock inicial al crear el producto"
        )
        
    messages.success(request, f"Producto '{nombre}' agregado al estante exitosamente.")
    return redirect("panel_inventario")


@require_POST
def panel_producto_editar(request, id_producto):
    producto = get_object_or_404(Producto, id_producto=id_producto)
    nombre = request.POST.get("nombre", "").strip()
    descripcion = request.POST.get("descripcion", "").strip()
    precio_str = request.POST.get("precio_venta", "0").replace(".", "").replace(",", "").strip()
    stock_str = request.POST.get("stock_actual", "").strip()
    
    if nombre:
        producto.nombre = nombre
    producto.descripcion = descripcion if descripcion else None
    
    try:
        producto.precio_venta = Decimal(precio_str)
    except (InvalidOperation, ValueError):
        pass
        
    if stock_str != "":
        try:
            nuevo_stock = int(stock_str)
            diferencia = nuevo_stock - producto.stock_actual
            if diferencia != 0:
                MovimientoProducto.objects.create(
                    producto=producto,
                    tipo='entrada' if diferencia > 0 else 'venta',
                    cantidad=abs(diferencia),
                    monto_total=Decimal("0"),
                    observaciones=f"Ajuste manual de stock ({producto.stock_actual} -> {nuevo_stock})"
                )
                producto.stock_actual = nuevo_stock
        except ValueError:
            pass
            
    producto.save()
    messages.success(request, f"Producto '{producto.nombre}' actualizado.")
    return redirect("panel_inventario")


@require_POST
def panel_producto_eliminar(request, id_producto):
    producto = get_object_or_404(Producto, id_producto=id_producto)
    producto.activo = False
    producto.save()
    messages.success(request, f"Producto '{producto.nombre}' quitado del estante.")
    return redirect("panel_inventario")


@require_POST
def panel_producto_agregar_stock(request):
    """
    Registra una entrada / reposición de mercadería (ej. 'pusimos 12 medias').
    """
    id_producto = request.POST.get("id_producto")
    cantidad_str = request.POST.get("cantidad", "0").strip()
    costo_str = request.POST.get("monto_total", "0").replace(".", "").replace(",", "").strip()
    observaciones = request.POST.get("observaciones", "").strip()
    fecha_str = request.POST.get("fecha")
    
    producto = get_object_or_404(Producto, id_producto=id_producto)
    
    try:
        cantidad = int(cantidad_str)
    except ValueError:
        cantidad = 0
        
    if cantidad <= 0:
        messages.error(request, "La cantidad a agregar debe ser mayor a 0.")
        return redirect("panel_inventario")
        
    try:
        costo_total = Decimal(costo_str)
    except (InvalidOperation, ValueError):
        costo_total = Decimal("0")
        
    fecha = timezone.localdate()
    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            pass
            
    producto.stock_actual += cantidad
    producto.save()
    
    MovimientoProducto.objects.create(
        producto=producto,
        tipo='entrada',
        cantidad=cantidad,
        precio_unitario=Decimal("0"),
        monto_total=costo_total,
        fecha=fecha,
        observaciones=observaciones or "Reposición de stock"
    )
    
    if costo_total > 0:
        Gasto.objects.create(
            fecha=fecha,
            categoria='compra_stock',
            descripcion=f"Compra/Reposición de {cantidad}x {producto.nombre}",
            monto=costo_total,
            metodo_pago='efectivo',
            observaciones=observaciones
        )
        
    messages.success(request, f"Se agregaron {cantidad} unidades a '{producto.nombre}'. Stock actual: {producto.stock_actual}.")
    return redirect("panel_inventario")


@require_POST
def panel_producto_registrar_venta(request):
    """
    Registra la venta de un producto (descuenta stock e ingresa monto).
    """
    id_producto = request.POST.get("id_producto")
    cantidad_str = request.POST.get("cantidad", "1").strip()
    precio_str = request.POST.get("precio_unitario", "0").replace(".", "").replace(",", "").strip()
    metodo_pago = request.POST.get("metodo_pago", "efectivo")
    id_alumno = request.POST.get("id_alumno")
    cliente_nombre = request.POST.get("cliente_nombre", "").strip()
    fecha_str = request.POST.get("fecha")
    observaciones = request.POST.get("observaciones", "").strip()
    
    producto = get_object_or_404(Producto, id_producto=id_producto)
    
    try:
        cantidad = int(cantidad_str)
    except ValueError:
        cantidad = 1
        
    if cantidad <= 0:
        messages.error(request, "La cantidad a vender debe ser mayor a 0.")
        return redirect("panel_inventario")
        
    if producto.stock_actual < cantidad:
        messages.error(request, f"Stock insuficiente para '{producto.nombre}'. Solo quedan {producto.stock_actual} disponibles.")
        return redirect("panel_inventario")
        
    try:
        precio_unitario = Decimal(precio_str)
    except (InvalidOperation, ValueError):
        precio_unitario = producto.precio_venta
        
    monto_total = precio_unitario * cantidad
    
    fecha = timezone.localdate()
    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            pass
            
    alumno = None
    if id_alumno:
        alumno = Alumno.objects.filter(id_alumno=id_alumno).first()
        if alumno and not cliente_nombre:
            cliente_nombre = f"{alumno.id_persona.nombre} {alumno.id_persona.apellido}"
            
    producto.stock_actual -= cantidad
    producto.save()
    
    MovimientoProducto.objects.create(
        producto=producto,
        tipo='venta',
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        monto_total=monto_total,
        metodo_pago=metodo_pago,
        id_alumno=alumno,
        cliente_nombre=cliente_nombre or "Cliente General",
        fecha=fecha,
        observaciones=observaciones
    )
    
    messages.success(request, f"Venta registrada: {cantidad}x {producto.nombre} por Gs. {int(monto_total):,}. Quedan {producto.stock_actual} en stock.".replace(",", "."))
    return redirect("panel_inventario")


@require_POST
def panel_producto_movimiento_eliminar(request, id_movimiento):
    mov = get_object_or_404(MovimientoProducto, id_movimiento=id_movimiento)
    if mov.tipo == 'entrada':
        mov.producto.stock_actual = max(0, mov.producto.stock_actual - mov.cantidad)
    elif mov.tipo == 'venta':
        mov.producto.stock_actual += mov.cantidad
    mov.producto.save()
    
    mov.delete()
    messages.success(request, "Movimiento eliminado y stock reajustado.")
    return redirect("panel_inventario")


# ==========================================
# MÓDULO DE GASTOS Y SERVICIOS
# ==========================================

def panel_gastos(request):
    """
    Control de gastos operativos del estudio: servicios básicos, mantenimientos, insumos, etc.
    """
    mes_str = request.GET.get("mes")
    if mes_str:
        try:
            mes_actual = datetime.strptime(mes_str, "%Y-%m").date()
        except ValueError:
            mes_actual = timezone.now().date().replace(day=1)
    else:
        mes_actual = timezone.now().date().replace(day=1)
        
    import calendar
    _, last_day = calendar.monthrange(mes_actual.year, mes_actual.month)
    fin_mes = mes_actual.replace(day=last_day)
    
    gastos = Gasto.objects.filter(fecha__gte=mes_actual, fecha__lte=fin_mes)
    
    categoria_filtro = request.GET.get("categoria", "")
    if categoria_filtro:
        gastos = gastos.filter(categoria=categoria_filtro)
        
    gastos = gastos.order_by("-fecha", "-id_gasto")
    
    total_gastos = gastos.aggregate(total=Sum("monto"))["total"] or Decimal("0")
    
    gastos_mes_completo = Gasto.objects.filter(fecha__gte=mes_actual, fecha__lte=fin_mes)
    total_servicios = gastos_mes_completo.filter(categoria="servicios").aggregate(total=Sum("monto"))["total"] or Decimal("0")
    total_mantenimiento = gastos_mes_completo.filter(categoria="mantenimiento").aggregate(total=Sum("monto"))["total"] or Decimal("0")
    total_insumos = gastos_mes_completo.filter(categoria="insumos").aggregate(total=Sum("monto"))["total"] or Decimal("0")
    total_otros = gastos_mes_completo.exclude(categoria__in=["servicios", "mantenimiento", "insumos"]).aggregate(total=Sum("monto"))["total"] or Decimal("0")
    
    desglose_cat = gastos_mes_completo.values("categoria").annotate(total=Sum("monto")).order_by("-total")
    cat_dict = dict(Gasto.CATEGORIA_CHOICES)
    chart_cat_labels = [cat_dict.get(d["categoria"], d["categoria"]) for d in desglose_cat]
    chart_cat_data = [float(d["total"]) for d in desglose_cat]
    
    context = {
        "mes_actual": mes_actual,
        "gastos": gastos,
        "categoria_filtro": categoria_filtro,
        "categorias": Gasto.CATEGORIA_CHOICES,
        "metodos_pago": Gasto.METODO_PAGO_CHOICES,
        "total_gastos": total_gastos,
        "total_servicios": total_servicios,
        "total_mantenimiento": total_mantenimiento,
        "total_insumos": total_insumos,
        "total_otros": total_otros,
        "chart_cat_labels_json": json.dumps(chart_cat_labels),
        "chart_cat_data_json": json.dumps(chart_cat_data),
        "hoy": timezone.localdate(),
    }
    return render(request, "admin_panel/gastos/lista.html", context)


@require_POST
def panel_gasto_registrar(request):
    fecha_str = request.POST.get("fecha")
    categoria = request.POST.get("categoria", "servicios")
    descripcion = request.POST.get("descripcion", "").strip()
    monto_str = request.POST.get("monto", "0").replace(".", "").replace(",", "").strip()
    metodo_pago = request.POST.get("metodo_pago", "transferencia")
    nro_comprobante = request.POST.get("nro_comprobante", "").strip()
    observaciones = request.POST.get("observaciones", "").strip()
    
    if not descripcion:
        messages.error(request, "Debes ingresar una descripción del gasto.")
        return redirect("panel_gastos")
        
    try:
        monto = Decimal(monto_str)
    except (InvalidOperation, ValueError):
        monto = Decimal("0")
        
    if monto <= 0:
        messages.error(request, "El monto del gasto debe ser mayor a 0.")
        return redirect("panel_gastos")
        
    fecha = timezone.localdate()
    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            pass
            
    Gasto.objects.create(
        fecha=fecha,
        categoria=categoria,
        descripcion=descripcion,
        monto=monto,
        metodo_pago=metodo_pago,
        nro_comprobante=nro_comprobante if nro_comprobante else None,
        observaciones=observaciones if observaciones else None
    )
    
    messages.success(request, f"Gasto registrado: '{descripcion}' por Gs. {int(monto):,}.".replace(",", "."))
    mes_redirect = fecha.strftime("%Y-%m")
    return redirect(f"/panel/gastos/?mes={mes_redirect}")


@require_POST
def panel_gasto_editar(request, id_gasto):
    gasto = get_object_or_404(Gasto, id_gasto=id_gasto)
    
    fecha_str = request.POST.get("fecha")
    categoria = request.POST.get("categoria")
    descripcion = request.POST.get("descripcion", "").strip()
    monto_str = request.POST.get("monto", "0").replace(".", "").replace(",", "").strip()
    metodo_pago = request.POST.get("metodo_pago")
    nro_comprobante = request.POST.get("nro_comprobante", "").strip()
    observaciones = request.POST.get("observaciones", "").strip()
    
    if descripcion:
        gasto.descripcion = descripcion
    if categoria:
        gasto.categoria = categoria
    if metodo_pago:
        gasto.metodo_pago = metodo_pago
        
    try:
        gasto.monto = Decimal(monto_str)
    except (InvalidOperation, ValueError):
        pass
        
    if fecha_str:
        try:
            gasto.fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            pass
            
    gasto.nro_comprobante = nro_comprobante if nro_comprobante else None
    gasto.observaciones = observaciones if observaciones else None
    gasto.save()
    
    messages.success(request, "Gasto actualizado correctamente.")
    mes_redirect = gasto.fecha.strftime("%Y-%m")
    return redirect(f"/panel/gastos/?mes={mes_redirect}")


@require_POST
def panel_gasto_eliminar(request, id_gasto):
    gasto = get_object_or_404(Gasto, id_gasto=id_gasto)
    mes_redirect = gasto.fecha.strftime("%Y-%m")
    gasto.delete()
    messages.success(request, "Gasto eliminado.")
    return redirect(f"/panel/gastos/?mes={mes_redirect}")
