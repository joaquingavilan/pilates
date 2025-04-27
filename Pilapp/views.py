from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import *
import json
import logging
from datetime import datetime, timedelta
from django.db import transaction


DAY_INDEX = {
    "Lunes": 0,
    "Martes": 1,
    "Miércoles": 2,
    "Jueves": 3,
    "Viernes": 4,
}

@csrf_exempt
def prueba_railway(request):
    return JsonResponse({"message": "Hola"})

@csrf_exempt
@transaction.atomic
def registrar_alumno(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            response = registrar_alumno_datos(data)
            return JsonResponse(response)
        except Exception as e:
            logging.error(f"Error en registrar_alumno: {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Método no permitido"}, status=405)

def registrar_alumno_datos(data):
    errores = []
    turnos_asignados = []

    # 📌 Validar turnos
    for turno_str in data["turnos"]:
        try:
            dia, horario = turno_str.split()
            turno = Turno.objects.get(dia=dia, horario=horario)
            if turno.estado == "Ocupado":
                errores.append(f"El turno {turno_str} está lleno")
            else:
                turnos_asignados.append(turno)
        except Turno.DoesNotExist:
            errores.append(f"El turno {turno_str} no existe")

    # 📌 Validar paquete
    try:
        paquete = Paquete.objects.get(cantidad_clases=data["paquete"])
    except Paquete.DoesNotExist:
        errores.append(f"Paquete con {data['paquete']} clases no existe")

    # 📌 Si hay errores, devolverlos todos juntos
    if errores:
        raise ValueError("Errores encontrados: " + "; ".join(errores))

    # 📌 Si todo está OK, ahora crear los objetos
    persona = Persona.objects.create(
        nombre=data["nombre"],
        apellido=data["apellido"],
        telefono=data.get("telefono"),
        ruc=data.get("ruc"),
        observaciones=data.get("observaciones")
    )

    alumno = Alumno.objects.create(
        id_persona=persona,
        canal_captacion=data.get("canal_captacion")
    )

    alumno_paquete = AlumnoPaquete.objects.create(
        id_alumno=alumno,
        id_paquete=paquete,
        estado="activo",
        fecha_inicio=data["fecha_inicio"]
    )

    cantidad_clases = paquete.cantidad_clases
    cantidad_turnos = len(turnos_asignados)
    clases_por_turno = cantidad_clases // cantidad_turnos

    for turno in turnos_asignados:
        AlumnoPaqueteTurno.objects.create(id_alumno_paquete=alumno_paquete, id_turno=turno)
        fechas_clases = obtener_fechas_turno_normal(turno.id_turno, data["fecha_inicio"], clases_por_turno)["fechas"]

        for fecha in fechas_clases:
            fecha_clase = datetime.strptime(fecha, "%Y-%m-%d").date()
            clase = Clase.objects.get(
                id_instructor=Instructor.objects.get(id_instructor=1),
                id_turno=turno,
                fecha=fecha_clase
            )
            AlumnoClase.objects.create(id_alumno_paquete=alumno_paquete, id_clase=clase, estado="pendiente")

        turno.lugares_ocupados += 1
        if turno.lugares_ocupados >= 4:
            turno.estado = "Ocupado"
        turno.save()

    return {"message": "Alumno registrado exitosamente"}

@csrf_exempt
def verificar_turno(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            dia = data.get("dia")  # Ejemplo: "Lunes"
            horario = data.get("horario")  # Ejemplo: "07:00"

            if not dia or not horario:
                return JsonResponse({"error": "Debes enviar 'dia' y 'horario'"}, status=400)

            try:
                turno = Turno.objects.get(dia=dia, horario=horario)
            except Turno.DoesNotExist:
                return JsonResponse({"message": "No hay turno registrado para ese día y horario."})

            lugares_disponibles = 4 - turno.lugares_ocupados

            if lugares_disponibles > 0:
                return JsonResponse({"message": f"Hay {lugares_disponibles} lugares disponibles."})
            else:
                return JsonResponse({"message": "No hay lugares disponibles."})

        except Exception as e:
            logging.error(f"Error en verificar_turno: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Método no permitido"}, status=405)


from django.utils.timezone import now  # Para fecha de hoy respetando timezone

@csrf_exempt
def verificar_clase_hoy(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            horario = data.get("horario")  # Ejemplo: "19:00"

            if not horario:
                return JsonResponse({"error": "Debes enviar 'horario'."}, status=400)

            # Obtener fecha actual
            fecha_hoy = now().date()

            # Sacar el nombre del día actual en español
            dias_traducidos = {
                0: 'Lunes',
                1: 'Martes',
                2: 'Miércoles',
                3: 'Jueves',
                4: 'Viernes',
                5: 'Sábado',
                6: 'Domingo'
            }
            dia_idx = fecha_hoy.weekday()  # Monday=0, Sunday=6
            dia_hoy = dias_traducidos.get(dia_idx)

            # Si es Domingo no hay clases
            if dia_hoy == 'Domingo':
                return JsonResponse({"message": "Hoy es domingo y no hay clases."})

            # Buscar turno por día y horario
            try:
                turno = Turno.objects.get(dia=dia_hoy, horario=horario)
            except Turno.DoesNotExist:
                return JsonResponse({"message": "No hay turno registrado para hoy a ese horario."})
            except Turno.MultipleObjectsReturned:
                return JsonResponse({"error": "Error: múltiples turnos encontrados para ese horario."}, status=500)

            # Buscar la clase de hoy con ese turno
            try:
                clase = Clase.objects.get(id_turno=turno, fecha=fecha_hoy)
            except Clase.DoesNotExist:
                return JsonResponse({"message": "No hay clase programada hoy a ese horario."})

            # Calcular lugares ocupados
            lugares_ocupados = AlumnoClase.objects.filter(id_clase=clase).count()
            lugares_disponibles = 4 - lugares_ocupados

            if lugares_disponibles > 0:
                return JsonResponse({"message": f"Hay {lugares_disponibles} lugares disponibles para hoy a las {horario}."})
            else:
                return JsonResponse({"message": f"No hay lugares disponibles para hoy a las {horario}."})

        except Exception as e:
            logging.error(f"Error en verificar_clase_hoy: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Método no permitido"}, status=405)


@csrf_exempt
@transaction.atomic
def actualizar_ruc(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            nombre = data.get("nombre")
            apellido = data.get("apellido")
            nuevo_ruc = data.get("ruc")

            errores = []
            if not nombre:
                errores.append("El nombre es obligatorio.")
            if not apellido:
                errores.append("El apellido es obligatorio.")
            if not nuevo_ruc:
                errores.append("El nuevo RUC es obligatorio.")

            if errores:
                return JsonResponse({"error": " ".join(errores)}, status=400)

            try:
                persona = Persona.objects.get(nombre=nombre, apellido=apellido)
            except Persona.DoesNotExist:
                return JsonResponse({"error": "No se encontró la persona con ese nombre y apellido."}, status=404)

            persona.ruc = nuevo_ruc
            persona.save()

            return JsonResponse({"message": f"RUC actualizado correctamente para {nombre} {apellido}"})

        except Exception as e:
            logging.error(f"Error en actualizar_ruc: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Método no permitido"}, status=405)


def obtener_fechas_turno_normal(id_turno, fecha_inicio, n):
    try:
        turno = Turno.objects.get(id_turno=id_turno)
    except Turno.DoesNotExist:
        return {"error": "Turno no encontrado"}

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
    fecha_actual = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()

    while fecha_actual.weekday() != dia_turno_idx:
        fecha_actual += timedelta(days=1)

    fechas = []
    for _ in range(n):
        fechas.append(fecha_actual.strftime("%Y-%m-%d"))
        fecha_actual += timedelta(days=7)

    return {"fechas": fechas}
