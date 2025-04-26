from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import *
import json
import logging
from datetime import datetime, timedelta

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
def registrar_alumno(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            response = registrar_alumno_datos(data)
            if "error" in response:
                return JsonResponse(response, status=400)
            return JsonResponse(response)
        except Exception as e:
            logging.error(f"Error en registrar_alumno: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Método no permitido"}, status=405)

def registrar_alumno_datos(data):
    try:
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

        paquete = Paquete.objects.get(cantidad_clases=data["paquete"])

        alumno_paquete = AlumnoPaquete.objects.create(
            id_alumno=alumno,
            id_paquete=paquete,
            estado="activo",
            fecha_inicio=data["fecha_inicio"]
        )

        turnos_asignados = []
        for turno_str in data["turnos"]:
            dia, horario = turno_str.split()
            turno = Turno.objects.get(dia=dia, horario=horario)
            if turno.estado == "Ocupado":
                return {"error": f"El turno {turno_str} está lleno"}
            turnos_asignados.append(turno)

        cantidad_clases = paquete.cantidad_clases
        cantidad_turnos = len(turnos_asignados)
        clases_por_turno = cantidad_clases // cantidad_turnos

        fecha_inicio_obj = datetime.strptime(data["fecha_inicio"], "%Y-%m-%d").date()

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

    except Exception as e:
        logging.error(f"Error en registrar_alumno_datos: {str(e)}")
        return {"error": str(e)}

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
