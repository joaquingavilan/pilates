from django.shortcuts import render, redirect
from .models import *
import json
from django.views.decorators.csrf import csrf_exempt
from .forms import *
from django.http import JsonResponse
from datetime import date, timedelta, datetime
from django.db.models import Q
from twilio.rest import Client
from django.conf import settings


DAY_INDEX = {
    "Lunes": 0,
    "Martes": 1,
    "Miércoles": 2,
    "Jueves": 3,
    "Viernes": 4,
}


def enviar_mensaje_whatsapp(mensaje, destinatario):
    """
    Envía un mensaje de WhatsApp usando Twilio.
    """
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    message = client.messages.create(
        from_=settings.TWILIO_WHATSAPP_NUMBER,
        body=mensaje,
        to=f"whatsapp:{destinatario}"
    )

    return message.sid  # Devuelve el ID del mensaje enviado

from django.http import HttpResponse

@csrf_exempt
def recibir_mensaje_twilio(request):
    """
    Recibe los mensajes de WhatsApp enviados a Twilio y responde según el estado de la conversación.
    """
    if request.method == "POST":
        mensaje = request.POST.get("Body", "").strip()
        numero_remitente = request.POST.get("From", "").replace("whatsapp:", "")

        # 📌 Obtener o crear la conversación
        conversacion = Conversacion.objects.last()

        if not conversacion:
            conversacion = Conversacion.objects.create()

        # 📌 Redirigir según el estado
        if conversacion.estado == "MenuPrincipal":
            respuesta = menu_principal(conversacion, mensaje)
        elif conversacion.estado == "RegistrandoAlumno":
            respuesta = pedir_datos_alumno(conversacion, mensaje)
        else:
            respuesta = {"respuesta": "Error en la conversación."}

        # 📌 Enviar respuesta a WhatsApp
        enviar_mensaje_whatsapp(respuesta["respuesta"], numero_remitente)
        
        return HttpResponse("OK", content_type="text/plain")

    return HttpResponse("Método no permitido", status=405, content_type="text/plain")



def menu_principal(conversacion, mensaje):
    """
    Muestra el menú de opciones y maneja la selección del usuario.
    """
    if mensaje == "1":
        # Actualizar la conversación y pasar a registro de alumno
        conversacion.estado = "RegistrandoAlumno"
        conversacion.paso = 1
        conversacion.datos = {}  # Resetear datos
        conversacion.save()
        return JsonResponse({"respuesta": "Por favor, envíame el nombre del alumno."})
    
    return JsonResponse({"respuesta": "Menú de opciones:\n1. Registrar alumno\nEscribe el número de la opción que deseas elegir."})

def pedir_datos_alumno(conversacion, mensaje):
    """
    Pide los datos uno por uno hasta completar la información del alumno.
    """
    pasos = [
        "nombre",
        "apellido",
        "telefono",
        "ruc",
        "observaciones",
        "canal_captacion",
        "paquete",
        "fecha_inicio",
        "turnos"
    ]

    paso_actual = conversacion.paso
    conversacion.datos[pasos[paso_actual - 1]] = mensaje
    conversacion.save()

    if paso_actual < len(pasos):
        # Pedir el siguiente dato
        siguiente_pregunta = {
            1: "Ahora, envíame el apellido del alumno.",
            2: "Número de teléfono (opcional, puedes enviar 'ninguno').",
            3: "RUC (opcional, puedes enviar 'ninguno').",
            4: "Observaciones (opcional, puedes enviar 'ninguno').",
            5: "¿Cómo se enteró del estudio? (Instagram, Recomendación, etc.)",
            6: "Seleccione un paquete (1, 4, 8, 12, 16 clases).",
            7: "Fecha de inicio en formato YYYY-MM-DD.",
            8: "Ingrese hasta 4 turnos en formato 'Lunes 18:00', separados por comas."
        }
        conversacion.paso += 1
        conversacion.save()
        return JsonResponse({"respuesta": siguiente_pregunta[paso_actual]})

    # 📌 Todos los datos han sido recibidos, llamar a `procesar_registro_alumno`
    return procesar_registro_alumno(conversacion)

def procesar_registro_alumno(conversacion):
    """
    Procesa los datos capturados, los envía a `registrar_alumno` y devuelve una respuesta final.
    """
    datos = conversacion.datos

    # Convertir "ninguno" a None
    for key in ["telefono", "ruc", "observaciones"]:
        if datos[key].lower() == "ninguno":
            datos[key] = None

    # Convertir el paquete a un entero
    datos["paquete"] = int(datos["paquete"])

    # Convertir turnos a lista
    datos["turnos"] = [t.strip() for t in datos["turnos"].split(",")]

    # Llamar a `registrar_alumno`
    response = registrar_alumno_datos(datos)

    # Eliminar la conversación (ya completamos el flujo)
    conversacion.delete()

    return JsonResponse(response)


def registrar_alumno_datos(data):
    """
    Versión interna de `registrar_alumno`, pero sin `request`, para manejar registros internos.
    """
    try:
        # 📌 1. Crear la Persona
        persona = Persona.objects.create(
            nombre=data["nombre"],
            apellido=data["apellido"],
            telefono=data.get("telefono"),
            ruc=data.get("ruc"),
            observaciones=data.get("observaciones")
        )

        # 📌 2. Crear el Alumno asociado a la Persona
        alumno = Alumno.objects.create(
            id_persona=persona,
            canal_captacion=data.get("canal_captacion")
        )

        # 📌 3. Verificar que el paquete exista
        paquete = Paquete.objects.get(cantidad_clases=data["paquete"])

        # 📌 4. Asignar el paquete al alumno
        alumno_paquete = AlumnoPaquete.objects.create(
            id_alumno=alumno,
            id_paquete=paquete,
            estado="activo",
            fecha_inicio=data["fecha_inicio"]
        )

        # 📌 5. Validar y obtener los turnos
        turnos_asignados = []
        for turno_str in data["turnos"]:
            dia, horario = turno_str.split()
            turno = Turno.objects.get(dia=dia, horario=horario)
            if turno.estado == "Ocupado":
                return {"error": f"El turno {turno_str} está lleno"}
            turnos_asignados.append(turno)

        # 📌 6. Distribuir clases en los turnos
        cantidad_clases = paquete.cantidad_clases
        cantidad_turnos = len(turnos_asignados)
        clases_por_turno = cantidad_clases // cantidad_turnos

        for turno in turnos_asignados:
            AlumnoPaqueteTurno.objects.create(id_alumno_paquete=alumno_paquete, id_turno=turno)
            fechas_clases = obtener_fechas_turno(turno.id_turno, data["fecha_inicio"], clases_por_turno)["fechas"]

            for fecha in fechas_clases:
                clase, _ = Clase.objects.get_or_create(id_instructor=None, id_turno=turno, fecha=fecha)
                AlumnoClase.objects.create(id_alumno_paquete=alumno_paquete, id_clase=clase, estado="pendiente")

            turno.lugares_ocupados += 1
            if turno.lugares_ocupados >= 4:
                turno.estado = "Ocupado"
            turno.save()

        return {"message": "Alumno registrado exitosamente"}

    except Exception as e:
        return {"error": str(e)}



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