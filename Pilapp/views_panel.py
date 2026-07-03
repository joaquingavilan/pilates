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
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from django.db import connection



#imports del proyecto

from .models import (
    Alumno, Persona, Clase, Turno, AlumnoClase, AlumnoClaseOcasional,
    AlumnoPaquete, Paquete, Pago, PagoAlumno, ClienteProspecto,
    AlumnoPaqueteTurno, PagoInstructor, Instructor
)

with connection.cursor() as cursor:
    try:
        # Intentamos agregar la columna. Si ya existe, el 'try' fallará y pasará al 'except'.
        cursor.execute('ALTER TABLE "Pilapp_alumnopaquete" ADD COLUMN "clases_usadas" INTEGER DEFAULT 0;')
        print("¡Columna 'clases_usadas' creada con éxito!")
    except Exception as e:
        # Si la columna ya existe, simplemente no hace nada
        print(f"Aviso de DB: {e}")


from django.db import connection
with connection.cursor() as cursor:
    try:
        # Intentamos agregar la columna. Si ya existe, el 'try' fallará y pasará al 'except'.
        cursor.execute('ALTER TABLE "Pilapp_alumnopaquete" ADD COLUMN "clases_usadas" INTEGER DEFAULT 0;')
        print("¡Columna 'clases_usadas' creada con éxito!")
    except Exception as e:
        # Si la columna ya existe, simplemente no hace nada
        print(f"Aviso de DB: {e}")



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

def panel_alumno_crear(request):
    """Vista para crear manualmente un alumno nuevo (y su persona asociada)."""
    from .models import Paquete, Turno, Persona, Alumno
    from .views import registrar_alumno_datos
    from django.db import transaction
    
    paquetes = Paquete.objects.all().order_by('cantidad_clases')
    turnos = Turno.objects.all().order_by('dia', 'horario')
    
    dias_orden = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    turnos_por_dia = {dia: [] for dia in dias_orden}
    for t in turnos:
        if t.dia in turnos_por_dia:
            turnos_por_dia[t.dia].append(t)
    turnos_por_dia = {k: v for k, v in turnos_por_dia.items() if v}

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        apellido = request.POST.get("apellido", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        canal = request.POST.get("canal_captacion", "").strip()
        
        paquete_val = request.POST.get("paquete")
        turnos_seleccionados = request.POST.getlist("turnos")
        fecha_inicio = request.POST.get("fecha_inicio", "").strip()
        
        if not nombre or not apellido:
            messages.error(request, "Nombre y apellido son obligatorios.")
            return render(request, "admin_panel/alumnos/crear.html", {"paquetes": paquetes, "turnos_por_dia": turnos_por_dia})
            
        try:
            if paquete_val == "ocasional" or not paquete_val:
                with transaction.atomic():
                    persona = Persona.objects.create(
                        nombre=nombre,
                        apellido=apellido,
                        telefono=telefono
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
        "turnos_por_dia": turnos_por_dia
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
        estado = request.POST.get("estado", "ocasional")
        canal = request.POST.get("canal_captacion", "").strip()
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

def panel_alumno_paquete_editar(request, id_alumno, id_alumno_paquete):
    """Vista para editar el paquete, estado y pago."""
    from .models import AlumnoPaquete, Paquete
    if request.method == "POST":
        paquete = get_object_or_404(AlumnoPaquete, id_alumno_paquete=id_alumno_paquete, id_alumno_id=id_alumno)
        nuevo_estado = request.POST.get("estado")
        nuevo_estado_pago = request.POST.get("estado_pago")
        nuevo_id_paquete = request.POST.get("id_paquete")
        
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
                
                # Validar cupo
                if clase_destino.total_inscriptos >= 4:
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
                clase_destino.total_inscriptos = F('total_inscriptos') + 1
                clase_destino.save()
                
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
                Clase.objects.filter(pk=id_clase, total_inscriptos__gt=0).update(total_inscriptos=F('total_inscriptos') - 1)
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
    turnos_por_dia = {dia: [] for dia in dias_orden}
    for t in turnos:
        if t.dia in turnos_por_dia:
            turnos_por_dia[t.dia].append(t)
    turnos_por_dia = {k: v for k, v in turnos_por_dia.items() if v}
    
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
        'turnos_por_dia': turnos_por_dia,
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
    alumnos_regulares = AlumnoClase.objects.filter(id_clase=clase).select_related(
        'id_alumno_paquete__id_alumno__id_persona'
    )
    
    # Alumnos ocasionales (para la lista de abajo)
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
    Elimina un alumno y todos sus vínculos operativos:
    - AlumnoPaquete, AlumnoPaqueteTurno, AlumnoClase, AlumnoClaseOcasional, PagoAlumno.
    Además, elimina los Pagos (Pago) asociados si no están vinculados a otros objetos.
    También elimina Persona si ya no está usada por Alumno/Instructor.
    Opcional: elimina ClienteProspecto por teléfono (aquí lo hago).
    """
    alumno = get_object_or_404(Alumno.objects.select_related("id_persona"), id_alumno=id_alumno)
    persona = alumno.id_persona
    telefono = (persona.telefono or "").strip() if persona else ""

    # Capturar IDs antes del delete para poder limpiar "Pago"
    paquete_ids = list(
        AlumnoPaquete.objects.filter(id_alumno=alumno).values_list("id_alumno_paquete", flat=True)
    )

    pago_ids = list(
        PagoAlumno.objects.filter(id_alumno_paquete_id__in=paquete_ids)
        .values_list("id_pago_id", flat=True)
        .distinct()
    )

    with transaction.atomic():
        # 1) Borrado principal (cascade elimina: AlumnoPaquete*, AlumnoClase*, AlumnoClaseOcasional, PagoAlumno, etc.)
        alumno.delete()

        # 2) Borrar pagos (Pago) si ya no están usados por otros vínculos
        #    (Evita borrar pagos que por algún motivo estén compartidos con otra entidad)
        for pid in pago_ids:
            existe_otro_pago_alumno = PagoAlumno.objects.filter(id_pago_id=pid).exists()
            existe_pago_instructor = PagoInstructor.objects.filter(id_pago_id=pid).exists()

            if (not existe_otro_pago_alumno) and (not existe_pago_instructor):
                Pago.objects.filter(id_pago=pid).delete()

        # 3) Borrar persona si no quedó referenciada por nadie
        #    (Protege el caso raro de que Persona sea también Instructor)
        if persona:
            persona_sigue_en_alumno = Alumno.objects.filter(id_persona=persona).exists()
            persona_sigue_en_instructor = Instructor.objects.filter(id_persona=persona).exists()
            if (not persona_sigue_en_alumno) and (not persona_sigue_en_instructor):
                persona.delete()

        # 4) (Opcional) Borrar prospecto por teléfono para evitar residuos de registros erróneos
        #    Si preferís conservar prospectos históricos, se puede quitar esto.
        if telefono:
            ClienteProspecto.objects.filter(telefono=telefono).delete()

    # Volver a la lista (si querés volver al referer, también se puede)
    return redirect("panel_alumnos")

##registrar pago de paquete para alumno desde su detalle


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
def panel_registrar_pago_alumno(request, id_alumno, id_alumno_paquete):
    alumno = get_object_or_404(Alumno, id_alumno=id_alumno)
    alumno_paquete = get_object_or_404(
        AlumnoPaquete,
        id_alumno_paquete=id_alumno_paquete,
        id_alumno=alumno
    )

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
        # Si no usas messages, puedes devolver un HttpResponse o guardar en session.
        # Por simplicidad, redirigimos al detalle.
        return redirect("panel_alumno_detalle", id_alumno=alumno.id_alumno)

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

    pago = Pago.objects.create(
        fecha=timezone.localdate(),
        monto=monto,
        nro_pago=nro_pago,
        estado=estado_pago_creado,
        metodo_pago=metodo_pago,
        comprobante=comprobante or None,
        id_factura=None
    )

    PagoAlumno.objects.create(
        id_pago=pago,
        id_alumno_paquete=alumno_paquete,
        observaciones=observaciones or None
    )

    # Actualizar estado_pago del paquete según acumulado total
    total_pagado_despues = total_pagado_antes + monto
    if costo > 0 and total_pagado_despues >= costo:
        alumno_paquete.estado_pago = "pagado"
    elif total_pagado_despues > 0:
        alumno_paquete.estado_pago = "parcial"
    else:
        alumno_paquete.estado_pago = "pendiente"

    alumno_paquete.save()
    # CAMBIO AQUÍ: Usar el parámetro next
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

# --- VISTAS PARA PROFES (ACCESO DIRECTO MAGICO) ---

def profes_clases_hoy(request, token):
    # Hardcoded token de seguridad simple
    if token != "acceso-profes":
        return HttpResponse("Acceso denegado. Token inválido.", status=403)
        
    # Obtener fecha
    from django.utils import timezone
    from datetime import datetime
    
    fecha_str = request.GET.get("fecha")
    if fecha_str:
        try:
            hoy = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            hoy = timezone.now().date()
    else:
        hoy = timezone.now().date()
    
    # Buscar todas las clases de hoy ordenadas por horario del turno
    clases_hoy = Clase.objects.filter(fecha=hoy).select_related('id_turno').order_by('id_turno__horario')
    
    clases_data = []
    
    for clase in clases_hoy:
        alumnos_lista = []
        
        # Alumnos regulares
        alumnos_regulares = AlumnoClase.objects.filter(id_clase=clase).select_related(
            'id_alumno_paquete__id_alumno__id_persona'
        )
        for ac in alumnos_regulares:
            persona = ac.id_alumno_paquete.id_alumno.id_persona
            alumnos_lista.append({
                'id_relacion': ac.id_alumno_clase,
                'nombre_completo': f"{persona.nombre} {persona.apellido}",
                'estado': ac.estado,
                'tipo': 'regular'
            })
            
        # Alumnos ocasionales
        alumnos_ocasionales = AlumnoClaseOcasional.objects.filter(id_clase=clase).select_related(
            'id_alumno__id_persona'
        )
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
            'alumnos': alumnos_lista
        })
        
    context = {
        'fecha_hoy': hoy,
        'clases_data': clases_data,
        'token': token
    }
    
    return render(request, "admin_panel/profes/clases_hoy.html", context)

def profes_marcar_asistencia(request, token):
    if token != "acceso-profes":
        return HttpResponse("Acceso denegado.", status=403)
        
    if request.method == "POST":
        fecha_str = request.POST.get("fecha", "")
        tipo = request.POST.get("tipo")
        id_relacion = request.POST.get("id_relacion")
        nuevo_estado = request.POST.get("estado")
        
        try:
            if tipo == 'regular':
                rel = AlumnoClase.objects.get(pk=id_relacion)
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
    if token != "acceso-profes":
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
    if token != "acceso-profes":
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
            PagoAlumno.objects.create(
                id_pago=nuevo_pago,
                id_alumno_paquete=paquete_actual,
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
    
    from django.db.models import Q
    pagos = Pago.objects.filter(
        fecha__gte=mes_actual,
        fecha__lte=fin_mes,
        estado__in=["pagado", "parcial"]
    )
    
    falta_facturar = request.GET.get('falta_facturar')
    if falta_facturar == '1':
        pagos = pagos.filter(
            Q(nro_pago__isnull=True) | 
            Q(nro_pago__exact="") | 
            Q(nro_pago__startswith="MANUAL-") | 
            Q(nro_pago__startswith="APQ-")
        )
        
    pagos = pagos.order_by("-fecha")
    
    # Calcular totales
    total_efectivo = pagos.filter(metodo_pago="efectivo").aggregate(total=Sum("monto"))["total"] or Decimal("0")
    total_transferencia = pagos.filter(metodo_pago="transferencia").aggregate(total=Sum("monto"))["total"] or Decimal("0")
    total_general = total_efectivo + total_transferencia
    
    context = {
        "mes_actual": mes_actual,
        "pagos": pagos,
        "total_efectivo": total_efectivo,
        "total_transferencia": total_transferencia,
        "total_general": total_general,
    }
    return render(request, "admin_panel/pagos/resumen.html", context)

