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
from django.http import HttpResponse
from twilio.twiml.messaging_response import MessagingResponse
import logging
from . import utils

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

@csrf_exempt
def recibir_mensaje_twilio(request):
    if request.method == "POST":
        try:
            mensaje = request.POST.get("Body", "").strip()
            numero_remitente = request.POST.get("From", "").replace("whatsapp:", "")

            if not mensaje or not numero_remitente:
                logging.error(f"Error en los datos: Mensaje: {mensaje}, Número remitente: {numero_remitente}")
                return HttpResponse("<Response><Message>Error en los datos</Message></Response>", content_type="text/xml", status=400)

            # 📌 Obtener o crear la conversación
            conversacion, created = Conversacion.objects.get_or_create(id=1)

            # 📌 Redirigir la interacción según el estado de la conversación
            if conversacion.estado == "MenuPrincipal":
                respuesta_data = menu_principal(conversacion, mensaje)
            elif conversacion.estado == "RegistrandoAlumno":
                respuesta_data = pedir_datos_alumno(conversacion, mensaje)
            else:
                respuesta_data = {"respuesta": "No entiendo tu mensaje. Escribe '1' para registrar un alumno."}

            # 📌 Respuesta para Twilio
            respuesta = MessagingResponse()
            respuesta.message(respuesta_data["respuesta"])

            return HttpResponse(str(respuesta), content_type="text/xml", status=200)

        except Exception as e:
            print(f"Error en recibir_mensaje_twilio: {str(e)}")
            return HttpResponse(f"<Response><Message>Error en el servidor</Message></Response>", content_type="text/xml", status=500)

    return HttpResponse("<Response><Message>Método no permitido</Message></Response>", content_type="text/xml", status=405)


def menu_principal(conversacion, mensaje):
    crear_turnos()
    crear_clases()
    """
    Muestra el menú de opciones y maneja la selección del usuario.
    """
    if mensaje == "1":
        # 📌 Actualizar la conversación y pasar a registro de alumno
        conversacion.estado = "RegistrandoAlumno"
        conversacion.paso = 1
        conversacion.datos = {}  # Resetear datos
        conversacion.save()
        return {"respuesta": "Por favor, envíame el nombre del alumno."} 
    elif mensaje == "2":
        conversacion.estado = "Reagendamiento"
        
    return {"respuesta": "Menú de opciones:\n1. Registrar alumno\nEscribe el número de la opción que deseas elegir."}  


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
        return {"respuesta": siguiente_pregunta[paso_actual]} 

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
    # 📌 Devolver un diccionario con la clave `respuesta`
    if "error" in response:
        return {"respuesta": f"Error: {response['error']}"}
    
    return {"respuesta": "Alumno registrado exitosamente."}


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
            logging.info(f"Dia: {dia}, Horario: {horario}")
            turno = Turno.objects.get(dia=dia, horario=horario)
            if turno.estado == "Ocupado":
                return {"error": f"El turno {turno_str} está lleno"}
            turnos_asignados.append(turno)

        # 📌 6. Distribuir clases en los turnos
        cantidad_clases = paquete.cantidad_clases
        logging.info(f"Cantidad de clases: {cantidad_clases}")
        cantidad_turnos = len(turnos_asignados)
        logging.info(f"Cantidad de turnos: {cantidad_turnos}")
        clases_por_turno = cantidad_clases // cantidad_turnos
        logging.info(f"Clases por turno: {clases_por_turno}")

        # Convertir fecha_inicio a objeto date
        fecha_inicio_obj = datetime.strptime(data["fecha_inicio"], "%Y-%m-%d").date()
        logging.info(f"Fecha de inicio: {fecha_inicio_obj}, día de la semana: {fecha_inicio_obj.weekday()}")
        
        # Verificar si la fecha de inicio coincide con algún turno
        fecha_inicio_coincide_con_turno = False
        for turno in turnos_asignados:
            dia_turno_idx = DAY_INDEX[turno.dia]
            if fecha_inicio_obj.weekday() == dia_turno_idx:
                fecha_inicio_coincide_con_turno = True
                logging.info(f"La fecha de inicio coincide con el turno {turno.dia}")
                break
        
        # Procesar los turnos normales
        for turno in turnos_asignados:
            AlumnoPaqueteTurno.objects.create(id_alumno_paquete=alumno_paquete, id_turno=turno)
            
            # Obtener fechas para este turno (siempre usando la lógica normal)
            fechas_clases = obtener_fechas_turno_normal(turno.id_turno, data["fecha_inicio"], clases_por_turno)["fechas"]
            logging.info(f"Fechas para turno {turno.dia} {turno.horario}: {fechas_clases}")
            
            for fecha in fechas_clases:
                fecha_clase = datetime.strptime(fecha, "%Y-%m-%d").date()
                logging.info(f"Fecha de clase: {fecha_clase}, turno: {turno.dia} {turno.horario}")
                clase = Clase.objects.get(id_instructor=Instructor.objects.get(id_instructor=1), id_turno=turno, fecha=fecha_clase)
                AlumnoClase.objects.create(id_alumno_paquete=alumno_paquete, id_clase=clase, estado="pendiente")
                logging.info(f"Clase creada: {clase}")
            
            turno.lugares_ocupados += 1
            logging.info(f"Lugares ocupados: {turno.lugares_ocupados}")
            if turno.lugares_ocupados >= 4:
                turno.estado = "Ocupado"
            turno.save()
            logging.info(f"Turno actualizado: {turno}")
        
        return {"message": "Alumno registrado exitosamente"}

    except Exception as e:
        logging.error(f"Error en registrar_alumno_datos: {str(e)}")
        return {"error": str(e)}


def obtener_fechas_turno_normal(id_turno, fecha_inicio, n):
    """
    Obtiene las fechas para un turno sin considerar la fecha de inicio como una fecha especial.
    Esta función implementa la lógica original donde simplemente se buscan las próximas n fechas
    del turno a partir de la fecha de inicio.
    """
    try:
        # 📌 1. Obtener el turno
        turno = Turno.objects.get(id_turno=id_turno)
        logging.info(f"obtener_fechas_turno_normal - Turno: {turno.dia} {turno.horario}")
    except Turno.DoesNotExist:
        logging.error(f"obtener_fechas_turno_normal - Turno no encontrado: {id_turno}")
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
        logging.error(f"obtener_fechas_turno_normal - Día del turno inválido: {turno.dia}")
        return {"error": "Día del turno inválido"}

    dia_turno_idx = dias_map[turno.dia]
    logging.info(f"obtener_fechas_turno_normal - Índice del día del turno: {dia_turno_idx}")

    # 📌 3. Convertir `fecha_inicio` a objeto `datetime.date`
    fecha_actual = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    logging.info(f"obtener_fechas_turno_normal - Fecha de inicio: {fecha_actual}, día de la semana: {fecha_actual.weekday()}")
    
    # Avanzar hasta el primer día después de la fecha de inicio que coincida con el día del turno
    while fecha_actual.weekday() != dia_turno_idx:
        fecha_actual += timedelta(days=1)
    
    logging.info(f"obtener_fechas_turno_normal - Primera fecha del turno: {fecha_actual}")
    
    # 📌 4. Buscar las próximas `n` fechas en las que cae el turno
    fechas = []
    for _ in range(n):
        fechas.append(fecha_actual.strftime("%Y-%m-%d"))
        fecha_actual += timedelta(days=7)  # Avanzar una semana para la próxima clase

    logging.info(f"obtener_fechas_turno_normal - Fechas generadas: {fechas}")
    return {"fechas": fechas}


def crear_turnos():
    """Crea turnos solo si la tabla está vacía."""
    if Turno.objects.exists():
        print("Los turnos ya están creados. No es necesario ejecutar el script.")
        return {"mensaje": "Los turnos ya existen, no se crearon nuevos."}
    else:
        utils.crear_turnos()

    return {"mensaje": f"Se crearon los turnos"}

def crear_clases():
    """Crea clases solo si la tabla está vacía."""
    if Clase.objects.exists():
        logging.info("Las clases ya están creadas. No es necesario ejecutar el script.")
        return {"mensaje": "Las clases ya existen, no se crearon nuevas."}
    else:
        utils.crear_clases_rango_fechas('2025-01-01', '2025-12-31')
        logging.info("Se crearon las clases")
        return {"mensaje": f"Se crearon las clases"}
