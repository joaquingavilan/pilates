from django.shortcuts import render, redirect
from .models import *
import json
from django.views.decorators.csrf import csrf_exempt
from .forms import *
from django.http import JsonResponse
from datetime import date, timedelta
from django.db.models import Q

DAY_INDEX = {
    "Lunes": 0,
    "Martes": 1,
    "Miércoles": 2,
    "Jueves": 3,
    "Viernes": 4,
}


@csrf_exempt  # Para permitir pruebas sin autenticación
def registrar_alumno(request):
    if request.method == "POST":
        try:
            # 📌 1. Obtener los datos de la solicitud
            data = json.loads(request.body)

            # 📌 2. Crear la Persona
            persona = Persona.objects.create(
                nombre=data["nombre"],
                apellido=data["apellido"],
                telefono=data.get("telefono"),
                ruc=data.get("ruc"),
                observaciones=data.get("observaciones")
            )

            # 📌 3. Crear el Alumno asociado a la Persona
            alumno = Alumno.objects.create(
                id_persona=persona,
                canal_captacion=data.get("canal_captacion")
            )

            # 📌 4. Verificar que el paquete exista
            try:
                paquete = Paquete.objects.get(cantidad_clases=data["paquete"])
            except Paquete.DoesNotExist:
                return JsonResponse({"error": "Paquete no encontrado"}, status=400)

            # 📌 5. Asignar el paquete al alumno
            alumno_paquete = AlumnoPaquete.objects.create(
                id_alumno=alumno,
                id_paquete=paquete,
                estado="activo",
                fecha_inicio=data["fecha_inicio"]
            )

            # 📌 6. Buscar el turno basado en "Lunes 18:00"
            turnos_recibidos = data["turnos"]  # Se espera una lista ["Lunes 18:00", "Miércoles 19:00"]
            if not isinstance(turnos_recibidos, list) or len(turnos_recibidos) > 4:
                return JsonResponse({"error": "Se pueden registrar hasta 4 turnos"}, status=400)

            turnos_asignados = []
            for turno_str in turnos_recibidos:
                try:
                    dia, horario = turno_str.split()
                    turno = Turno.objects.get(dia=dia, horario=horario)
                except Turno.DoesNotExist:
                    return JsonResponse({"error": f"Turno {turno_str} no encontrado"}, status=400)

                # 📌 7. Verificar si el turno está lleno antes de continuar
                if turno.estado == "Ocupado":
                    return JsonResponse({"error": f"El turno {turno_str} está lleno"}, status=400)

                turnos_asignados.append(turno)
            # 📌 8. Distribuir clases en los turnos y actualizar `lugares_ocupados`
            cantidad_clases = paquete.cantidad_clases  # Número total de clases del paquete
            cantidad_turnos = len(turnos_asignados)    # Número de turnos seleccionados
            clases_por_turno = cantidad_clases // cantidad_turnos  # Clases que tocan a cada turno

            # 📌 9. Asignar turnos y generar clases para cada turno
            for turno in turnos_asignados:
                AlumnoPaqueteTurno.objects.create(
                    id_alumno_paquete=alumno_paquete,
                    id_turno=turno
                )

                # Obtener las fechas de clase para este turno
                fechas_clases = obtener_fechas_turno(turno.id_turno, data["fecha_inicio"], clases_por_turno)["fechas"]

                for fecha in fechas_clases:
                    # Buscar si ya existe una clase en esa fecha para ese turno
                    clase, created = Clase.objects.get_or_create(
                        id_instructor=1,  # Asignar instructor si lo deseas
                        id_turno=turno,
                        fecha=fecha
                    )

                    # Registrar la asistencia del alumno en esa clase
                    AlumnoClase.objects.create(
                        id_alumno_paquete=alumno_paquete,
                        id_clase=clase,
                        estado="pendiente"
                    )

                # 📌 10. Actualizar `lugares_ocupados` y cambiar estado si es necesario
                turno.lugares_ocupados += 1
                if turno.lugares_ocupados >= 4:
                    turno.estado = "Ocupado"
                turno.save()

            return JsonResponse({
                "message": "Alumno registrado exitosamente",
                "id_alumno": alumno.id_alumno
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Método no permitido"}, status=405)


def obtener_fechas_turno(id_turno, fecha_inicio, n):
    try:
        # 📌 1. Obtener el turno
        turno = Turno.objects.get(id_turno=id_turno)
    except Turno.DoesNotExist:
        return {"error": "Turno no encontrado"}
    
    # 📌 2. Mapear el día del turno a un índice de la semana (0 = Lunes, ..., 6 = Domingo)
    dias_map = {
        "Lunes": 0,
        "Martes": 1,
        "Miércoles": 2,
        "Jueves": 3,
        "Viernes": 4
    }
    
    if turno.dia not in dias_map:
        return {"error": "Día del turno inválido"}

    dia_turno_idx = dias_map[turno.dia]

    # 📌 3. Convertir `fecha_inicio` a objeto `datetime.date`
    fecha_actual = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()

    # 📌 4. Buscar las próximas `n` fechas en las que cae el turno
    fechas = []
    while len(fechas) < n:
        if fecha_actual.weekday() == dia_turno_idx:
            fechas.append(fecha_actual.strftime("%Y-%m-%d"))
        fecha_actual += timedelta(days=1)

    return {"fechas": fechas}


def get_next_dates_for_days(weekdays, count=8, start_date=None):
    """
    Devuelve las próximas `count` fechas (tipo date) a partir de `start_date`
    cuyo weekday() esté dentro de `weekdays`.

    - weekdays: coleccion (set, list, etc.) con índices de día (lunes=0, martes=1, etc.)
    - count: cuántas fechas en total quieres
    - start_date: fecha inicial (por defecto, hoy)
    """
    if start_date is None:
        start_date = date.today()

    results = []
    current = start_date
    while len(results) < count:
        if current.weekday() in weekdays:
            results.append(current)
        current += timedelta(days=1)

    return results


def build_clases_programadas(turnos_ids, fecha_inicio, total_clases):
    """
    Genera una lista de (turno_id, fecha_date) para las 'total_clases' 
    a partir de 'fecha_inicio', considerando los días y horarios de 'turnos_ids'.
    """

    # Mapeo de días a índices de Python (0=Lunes, ..., 6=Domingo)
    DAY_INDEX = {
        'Lunes': 0,
        'Martes': 1,
        'Miércoles': 2,
        'Jueves': 3,
        'Viernes': 4,
    }
    
    # Obtener información de los turnos (día y horario)
    turnos_data = []
    print(turnos_ids)
    for t_id in turnos_ids:
        if not t_id:
            continue
        try:
            turno = Turno.objects.get(pk=t_id)
            day_idx = DAY_INDEX.get(turno.dia)  # Obtener índice del día
            if day_idx is not None:
                turnos_data.append((turno.id_turno, day_idx, turno.horario))
        except Turno.DoesNotExist:
            pass

    # Si no hay turnos válidos, evitamos el bucle infinito
    if not turnos_data:
        print("Error: No hay turnos válidos en turnos_data. Revisa los turnos_ids.")
        return []

    # Variables de control
    clases_programadas = []
    current_date = fecha_inicio
    count = 0

    print("---- Debug build_clases_programadas ----")
    print("turnos_data=", turnos_data)
    print("fecha_inicio=", fecha_inicio, "total_clases=", total_clases)

    # Avanzamos día a día hasta recopilar todas las clases necesarias
    while count < total_clases:
        weekday = current_date.weekday()
        
        for (t_id, d_idx, h) in turnos_data:
            if weekday == d_idx:
                fecha_clase = date(current_date.year, current_date.month, current_date.day)
                clases_programadas.append((t_id, fecha_clase))
                count += 1
                print(f"   => Clase agregada: turno={t_id}, fecha={fecha_clase}, count={count}")

        # Si después de iterar todos los turnos aún no se completó la cantidad requerida, avanzamos
        current_date += timedelta(days=1)

        # Failsafe adicional para evitar un bucle infinito
        if count > total_clases * 2:
            print("Error: Se generaron demasiadas clases. Algo está mal en la lógica.")
            break

    print("Result:", clases_programadas)
    return clases_programadas


def registrar_paquete_view(request):
    context = {}
    
    if request.method == 'POST':
        # Botón 1: "Obtener Cantidad de Turnos" (elige alumno + paquete)
        if 'btn_paquete' in request.POST:
            form = RegistrarPaqueteForm(request.POST)
            if form.is_valid():
                alumno = form.cleaned_data['alumno']
                paquete = form.cleaned_data['paquete']
                
                cant_clases = paquete.cantidad_clases if paquete else 0
                combos = (cant_clases // 4) if cant_clases > 1 else 1
                # (si tu regla es 4=1 turno, 8=2, etc.; 1 clase => 1 turno
                
                # Pasamos datos a la plantilla
                context['combos'] = combos
                context['alumno'] = alumno
                context['paquete'] = paquete
                context['turnos_libres'] = Turno.objects.filter(estado='Libre')
                context['range_combos'] = range(combos)

                # Preparamos placeholders
                context['seleccion_turnos'] = [None]*combos
                
                # Renderizamos el mismo template
                return render(request, 'registrar_paquete.html', context)

        # PASO 2: "Obtener Fechas"
        elif 'btn_turnos' in request.POST:
            alumno_id = request.POST.get('alumno_id')
            paquete_id = request.POST.get('paquete_id')
            combos = int(request.POST.get('combos', '0'))

            alumno = Alumno.objects.get(pk=alumno_id) if alumno_id else None
            paquete = Paquete.objects.get(pk=paquete_id) if paquete_id else None

            # Reunimos los días de la semana que el usuario seleccionó
            day_indexes = set()
            turnos_ids = []

            for i in range(combos):
                t_id = request.POST.get(f'turno_{i}')
                turnos_ids.append(t_id)
                if t_id:
                    try:
                        turno = Turno.objects.get(pk=t_id)
                        weekday_index = DAY_INDEX.get(turno.dia)
                        if weekday_index is not None:
                            day_indexes.add(weekday_index)
                    except Turno.DoesNotExist:
                        pass

            # Ahora generamos EXACTAMENTE 8 fechas a partir de HOY
            # que coincidan con cualquiera de los day_indexes que el alumno eligió
            fechas_posibles = get_next_dates_for_days(day_indexes, count=8)

            context['combos'] = combos
            context['alumno'] = alumno
            context['paquete'] = paquete
            context['turnos_libres'] = Turno.objects.filter(estado='Libre')
            context['seleccion_turnos'] = turnos_ids
            context['fechas_posibles'] = sorted(fechas_posibles)

            return render(request, 'registrar_paquete.html', context)

        # Botón 3: "Registrar"
        elif 'btn_registrar' in request.POST:
            alumno_id = request.POST.get('alumno_id')
            paquete_id = request.POST.get('paquete_id')
            combos = int(request.POST.get('combos', '0'))
            print(f"Registrando alumno id: {alumno_id} paquete_id {paquete_id} combos: {combos}")
            alumno = Alumno.objects.get(pk=alumno_id) if alumno_id else None
            paquete = Paquete.objects.get(pk=paquete_id) if paquete_id else None

            fecha_inicio_str = request.POST.get('fecha_inicio')
            if fecha_inicio_str:
                from datetime import datetime
                fecha_inicio_date = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
            else:
                fecha_inicio_date = date.today()

            # 1) Creamos el AlumnoPaquete
            alumno_paquete = AlumnoPaquete.objects.create(
                id_alumno=alumno,
                id_paquete=paquete,
                estado="activo",
                fecha_inicio=fecha_inicio_date
            )

            # 2) Guardamos los turnos seleccionados
            turnos_ids = []
            for i in range(combos):
                t_id = request.POST.get(f'turno_{i}')
                print(f"turno_id: {t_id}")
                turnos_ids.append(t_id)
                if t_id:
                    # Incrementar lugares ocupados, etc.
                    try:
                        turno_obj = Turno.objects.get(pk=t_id, estado='Libre')
                        AlumnoPaqueteTurno.objects.create(
                            id_alumno_paquete=alumno_paquete,
                            id_turno=turno_obj
                        )
                        turno_obj.lugares_ocupados += 1
                        if turno_obj.lugares_ocupados >= 4:
                            turno_obj.estado = 'Ocupado'
                        turno_obj.save()
                    except Turno.DoesNotExist:
                        pass

            # 3) Generamos la secuencia (turno_id, fecha_date)
            total_clases = paquete.cantidad_clases
            clases_programadas = build_clases_programadas(
                turnos_ids, fecha_inicio_date, total_clases
            )

            # 4) Por cada (turno_id, fecha_date), buscamos la Clase y creamos AlumnoClase
            from datetime import datetime, time

            for (turno_id, fecha_date) in clases_programadas:
                try:
                    turno_obj = Turno.objects.get(pk=turno_id)
                except Turno.DoesNotExist:
                    continue

                fecha_clase_dt = datetime.combine(fecha_date, turno_obj.horario)  
                try:
                    la_clase = Clase.objects.get(
                        fecha=fecha_clase_dt,
                        id_turno=turno_obj
                    )
                except Clase.DoesNotExist:
                    # Si no hay Clase programada para esa fecha/hora,
                    # podrías crearla en ese momento:
                    # la_clase = Clase.objects.create(
                    #     id_instructor=..., 
                    #     id_turno=turno_obj, 
                    #     fecha=fecha_clase_dt
                    # )
                    continue

                # Creamos AlumnoClase
                AlumnoClase.objects.create(
                    id_alumno_paquete=alumno_paquete,
                    id_clase=la_clase,
                    estado="pendiente"
                )

            return redirect('paquete_registro_exitoso')
    else:
        # GET inicial
        form = RegistrarPaqueteForm()
        context['form'] = form
        return render(request, 'registrar_paquete.html', context)


def paquete_registro_exitoso(request):
    return render(request, 'registro_exitoso.html')
