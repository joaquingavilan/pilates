from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from .models import Alumno, AlumnoPaquete, Paquete
import datetime

def crear_alumno(request):
    if request.method == "POST":
        # Datos que llegan del formulario o mensaje
        nombres = request.POST.get("nombres")
        apellidos = request.POST.get("apellidos")
        telefono = request.POST.get("telefono")
        fecha_nacimiento = request.POST.get("fecha_nacimiento")
        observaciones = request.POST.get("observaciones", "")  # Valor por defecto vacío si no se incluye

        # Validación básica
        if not (nombres and apellidos and fecha_nacimiento):
            return JsonResponse({"error": "Faltan campos obligatorios"}, status=400)

        # Crear el alumno
        alumno = Alumno.objects.create(
            nombres=nombres,
            apellidos=apellidos,
            telefono=telefono,
            fecha_nacimiento=fecha_nacimiento,
            observaciones=observaciones,
        )

        # Respuesta
        return JsonResponse({"mensaje": "Alumno creado con éxito", "id": alumno.id})
    
    # Si no es POST, devolver error o renderizar un formulario
    if request.method == "GET":
        return render(request, "crear_alumno.html")  # Un HTML opcional
    return JsonResponse({"error": "Método no permitido"}, status=405)


def modificar_alumno(request, alumno_id):
    # Obtener el alumno
    alumno = get_object_or_404(Alumno, id=alumno_id)

    if request.method == "POST":
        # Datos que llegan del formulario o mensaje
        nombres = request.POST.get("nombres", alumno.nombres)  # Mantener valor actual si no se envía
        apellidos = request.POST.get("apellidos", alumno.apellidos)
        telefono = request.POST.get("telefono", alumno.telefono)
        fecha_nacimiento = request.POST.get("fecha_nacimiento", alumno.fecha_nacimiento)
        observaciones = request.POST.get("observaciones", alumno.observaciones)

        # Actualizar los campos del alumno
        alumno.nombres = nombres
        alumno.apellidos = apellidos
        alumno.telefono = telefono
        alumno.fecha_nacimiento = fecha_nacimiento
        alumno.observaciones = observaciones
        alumno.save()  # Guardar cambios en la base de datos

        # Respuesta de éxito
        return JsonResponse({"mensaje": "Alumno modificado con éxito", "id": alumno.id})

    # Si no es POST, renderizar un formulario HTML opcional
    if request.method == "GET":
        return render(request, "modificar_alumno.html", {"alumno": alumno})
    
    return JsonResponse({"error": "Método no permitido"}, status=405)



def registrar_compra_paquete(request):
    if request.method == "POST":
        # Obtener los datos del POST
        id_alumno = request.POST.get("id_alumno")
        id_paquete = request.POST.get("id_paquete")
        fecha_inicio = request.POST.get("fecha_inicio")
        forma_pago = request.POST.get("forma_pago")

        # Validar que todos los campos estén presentes
        if not (id_alumno and id_paquete and fecha_inicio and forma_pago):
            return JsonResponse({"error": "Faltan campos obligatorios"}, status=400)

        # Obtener el alumno y el paquete
        alumno = get_object_or_404(Alumno, id=id_alumno)
        paquete = get_object_or_404(Paquete, id=id_paquete)

        # Crear el registro en AlumnoPaquete
        alumno_paquete = AlumnoPaquete.objects.create(
            alumno=alumno,
            paquete=paquete,
            fecha_inicio=fecha_inicio,
            forma_pago=forma_pago
        )

        # Responder con éxito
        return JsonResponse({
            "mensaje": "Compra registrada con éxito",
            "id_alumno_paquete": alumno_paquete.id
        })

    # Si no es POST, devolver error
    return JsonResponse({"error": "Método no permitido"}, status=405)


def registrar_inicio_paquete(request):
    if request.method == "POST":
        # Obtener los datos del POST    
        id_alumno_paquete = request.POST.get("id_alumno_paquete")
        fecha_inicio = request.POST.get("fecha_inicio", datetime.now().date())


def registrar_clase_paquete(request):
    if request.method == "POST":
        # Obtener los datos del POST