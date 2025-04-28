from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import *
import json
import logging
from datetime import datetime, timedelta
from django.db import transaction
from django.utils.timezone import now  # Para fecha de hoy respetando timezone
from datetime import date


DAY_INDEX = {
    "Lunes": 0,
    "Martes": 1,
    "Miércoles": 2,
    "Jueves": 3,
    "Viernes": 4,
    "Sábado": 5,
    "Domingo": 6
}


def obtener_fecha_proximo_dia(dia_nombre):
    hoy = datetime.now().date()
    dia_actual = hoy.weekday()
    dia_objetivo = DAY_INDEX[dia_nombre]

    dias_hasta_objetivo = (dia_objetivo - dia_actual + 7) % 7
    if dias_hasta_objetivo == 0:
        dias_hasta_objetivo = 7  # Si es hoy, te vas al próximo mismo día (no hoy mismo)

    fecha_objetivo = hoy + timedelta(days=dias_hasta_objetivo)
    return fecha_objetivo


@csrf_exempt
@transaction.atomic
def registrar_alumno_ocasional(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            response = registrar_alumno_ocasional_datos(data)
            return JsonResponse(response)
        except Exception as e:
            logging.error(f"Error en registrar_alumno_ocasional: {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Método no permitido"}, status=405)


@csrf_exempt
@transaction.atomic
def registrar_alumno_ocasional(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            response = registrar_alumno_ocasional_datos(data)
            return JsonResponse(response)
        except Exception as e:
            # Mejorar logging
            logging.error(f"[registrar_alumno_ocasional] Error: {str(e)}")
            logging.error(f"[registrar_alumno_ocasional] Datos recibidos: {request.body.decode('utf-8')}")
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Método no permitido"}, status=405)

def registrar_alumno_ocasional_datos(data):
    errores = []

    # 📌 Validar campos básicos
    if not data.get("nombre"):
        errores.append("Debe proporcionar un nombre.")
    if not data.get("apellido"):
        errores.append("Debe proporcionar un apellido.")
    if not data.get("telefono"):
        errores.append("Debe proporcionar un número de teléfono.")
    if not data.get("dia_turno"):
        errores.append("Debe proporcionar el día del turno.")
    if not data.get("hora_turno"):
        errores.append("Debe proporcionar el horario del turno.")

    turno = None
    clase = None

    if not errores:
        # 📌 Validar turno
        try:
            turno = Turno.objects.get(dia=data["dia_turno"], horario=data["hora_turno"])
            if turno.estado == "Ocupado":
                errores.append(f"El turno {data['dia_turno']} {data['hora_turno']} ya está lleno.")
        except Turno.DoesNotExist:
            errores.append(f"El turno {data['dia_turno']} {data['hora_turno']} no existe.")

    if turno and not errores:
        # 📌 Validar clase correspondiente al próximo día
        fecha_clase = obtener_fecha_proximo_dia(data["dia_turno"])
        try:
            clase = Clase.objects.get(id_turno=turno, fecha=fecha_clase)
            if clase.total_inscriptos >= 4:
                errores.append(f"La clase del {fecha_clase} a las {data['hora_turno']} ya está llena.")
        except Clase.DoesNotExist:
            errores.append(f"No existe clase programada para {fecha_clase} en el turno {data['dia_turno']} {data['hora_turno']}.")

    # 📌 Si hay errores, abortar
    if errores:
        raise ValueError("Errores encontrados: " + "; ".join(errores))

    # 📌 Crear Persona
    persona = Persona.objects.create(
        nombre=data["nombre"],
        apellido=data["apellido"],
        telefono=data["telefono"],
        observaciones=data.get("observaciones", "")
    )

    # 📌 Crear Alumno
    alumno = Alumno.objects.create(
        id_persona=persona,
        canal_captacion=data.get("canal_captacion", ""),
        estado="ocasional"
    )

    # 📌 Crear AlumnoClaseOcasional
    AlumnoClaseOcasional.objects.create(
        id_alumno=alumno,
        id_clase=clase,
        estado="reservado"
    )

    return {"mensaje": "Alumno ocasional registrado correctamente"}



@csrf_exempt
@transaction.atomic
def registrar_alumno(request):  #registrar un alumno con un paquete y turnos
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
    clases_a_reservar = []  # Nuevo: para preparar las clases validadas

    # 📌 Validar turnos
    for turno_str in data["turnos"]:
        try:
            dia, horario = turno_str.split()
            turno = Turno.objects.get(dia=dia, horario=horario)
            if turno.estado == "Ocupado":
                errores.append(f"El turno {turno_str} ya tiene su cupo general completo.")
            else:
                turnos_asignados.append(turno)
        except Turno.DoesNotExist:
            errores.append(f"El turno {turno_str} no existe.")

    # 📌 Validar paquete
    try:
        paquete = Paquete.objects.get(cantidad_clases=data["paquete"])
    except Paquete.DoesNotExist:
        errores.append(f"Paquete con {data['paquete']} clases no existe.")

    # 📌 Validar clases específicas
    if not errores:
        cantidad_clases = paquete.cantidad_clases
        cantidad_turnos = len(turnos_asignados)
        clases_por_turno = cantidad_clases // cantidad_turnos

        for turno in turnos_asignados:
            fecha_inicio = data.get("fecha_inicio")
            if not fecha_inicio:
                fecha_inicio = str(obtener_fecha_proximo_dia(turno.dia))  # Buscamos automáticamente el próximo día de ese turno

            fechas_clases = obtener_fechas_turno_normal(turno.id_turno, fecha_inicio, clases_por_turno)["fechas"]

            for fecha in fechas_clases:
                fecha_clase = datetime.strptime(fecha, "%Y-%m-%d").date()
                try:
                    clase = Clase.objects.get(
                        id_instructor=Instructor.objects.get(id_instructor=1),
                        id_turno=turno,
                        fecha=fecha_clase
                    )
                    if clase.total_inscriptos >= 4:
                        errores.append(f"La clase del {fecha_clase} a las {turno.horario} ya está llena.")
                    else:
                        clases_a_reservar.append((turno, clase))  # Lo guardamos para después
                except Clase.DoesNotExist:
                    errores.append(f"No existe clase programada para {fecha_clase} en el turno {turno.dia} {turno.horario}.")

    # 📌 Si hay errores, devolverlos todos juntos
    if errores:
        raise ValueError("Errores encontrados: " + "; ".join(errores))

    # 📌 Crear objetos (solo si todo está validado)
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
        fecha_inicio= fecha_inicio
    )

    for turno, clase in clases_a_reservar:
        AlumnoPaqueteTurno.objects.get_or_create(id_alumno_paquete=alumno_paquete, id_turno=turno)
        AlumnoClase.objects.create(id_alumno_paquete=alumno_paquete, id_clase=clase, estado="pendiente")

    return {"message": "Alumno registrado exitosamente"}




@csrf_exempt
def listar_precios_paquetes(request):
    if request.method == "GET":
        try:
            cantidad = request.GET.get("cantidad")  # <-- Capturamos parámetro opcional
            
            if cantidad:
                # Si se envió cantidad, buscar solo ese paquete
                try:
                    paquete = Paquete.objects.get(cantidad_clases=int(cantidad))
                    lista_paquetes = [{
                        "cantidad_clases": paquete.cantidad_clases,
                        "costo": f"{int(paquete.costo):,}".replace(",", ".")
                    }]
                except Paquete.DoesNotExist:
                    return JsonResponse({"message": f"No existe paquete de {cantidad} clases."})
            else:
                # Si no, listar todos
                paquetes = Paquete.objects.all().order_by('cantidad_clases')
                lista_paquetes = []
                for paquete in paquetes:
                    lista_paquetes.append({
                        "cantidad_clases": paquete.cantidad_clases,
                        "costo": f"{int(paquete.costo):,}".replace(",", ".")
                    })

            return JsonResponse({"paquetes": lista_paquetes})

        except Exception as e:
            logging.error(f"Error en listar_precios_paquetes: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Método no permitido"}, status=405)


@csrf_exempt
def obtener_alumnos_turno(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            dia = data.get("dia")  # Ejemplo: "Martes"
            horario = data.get("horario")  # Ejemplo: "18:00"

            if not dia or not horario:
                return JsonResponse({"error": "Debes enviar 'dia' y 'horario'"}, status=400)

            # Buscar turno
            try:
                turno = Turno.objects.get(dia=dia, horario=horario)
            except Turno.DoesNotExist:
                return JsonResponse({"message": f"No existe turno para {dia} a las {horario}."})
            hoy = date.today()
            dia_a_numero = {
                "Lunes": 0,
                "Martes": 1,
                "Miércoles": 2,
                "Jueves": 3,
                "Viernes": 4,
                "Sábado": 5
            }

            # Si el día que pidieron no es hoy, buscar la próxima fecha de ese día
            if hoy.weekday() != dia_a_numero[dia]:
                dias_a_sumar = (dia_a_numero[dia] - hoy.weekday()) % 7
                if dias_a_sumar == 0:
                    dias_a_sumar = 7
                fecha_objetivo = hoy + timedelta(days=dias_a_sumar)
            else:
                fecha_objetivo = hoy

            # Buscar clase de hoy para ese turno
            try:
                clase = Clase.objects.get(id_turno=turno, fecha=fecha_objetivo)
            except Clase.DoesNotExist:
                return JsonResponse({"message": f"No hay clase hoy para el turno {dia} {horario}."})

            alumnos = []

            # Alumnos regulares
            alumnos_regulares = AlumnoClase.objects.filter(id_clase=clase)
            for ac in alumnos_regulares:
                persona = ac.id_alumno_paquete.id_alumno.id_persona
                alumnos.append({
                    "nombre": persona.nombre,
                    "apellido": persona.apellido,
                    "telefono": persona.telefono,
                    "tipo": "regular"
                })

            # Alumnos ocasionales
            alumnos_ocasionales = AlumnoClaseOcasional.objects.filter(id_clase=clase)
            for ao in alumnos_ocasionales:
                persona = ao.id_alumno.id_persona
                alumnos.append({
                    "nombre": persona.nombre,
                    "apellido": persona.apellido,
                    "telefono": persona.telefono,
                    "tipo": "ocasional"
                })

            return JsonResponse({
                "dia": dia,
                "horario": horario,
                "fecha": str(fecha_objetivo),
                "alumnos": alumnos
            })

        except Exception as e:
            logging.error(f"Error en obtener_alumnos_turno: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    else:
        return JsonResponse({"error": "Método no permitido"}, status=405)


@csrf_exempt
def obtener_alumnos_clase(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            dia = data.get("dia")
            horario = data.get("horario")
            fecha = data.get("fecha")  # Opcional

            if not dia or not horario:
                return JsonResponse({"error": "Debes enviar 'dia' y 'horario'"}, status=400)

            # Buscar turno
            try:
                turno = Turno.objects.get(dia=dia, horario=horario)
            except Turno.DoesNotExist:
                return JsonResponse({"message": f"No existe turno {dia} {horario}."})

            # Resolver fecha
            if fecha:
                fecha_objetivo = datetime.strptime(fecha, "%Y-%m-%d").date()
            else:
                # Buscar la próxima fecha de ese día
                hoy = date.today()
                dias_semana = {
                    "Lunes": 0,
                    "Martes": 1,
                    "Miércoles": 2,
                    "Jueves": 3,
                    "Viernes": 4,
                    "Sábado": 5
                }
                dia_numero = dias_semana[dia]
                dias_a_sumar = (dia_numero - hoy.weekday()) % 7
                if dias_a_sumar == 0:
                    dias_a_sumar = 7
                fecha_objetivo = hoy + timedelta(days=dias_a_sumar)

            # Buscar clase
            try:
                clase = Clase.objects.get(id_turno=turno, fecha=fecha_objetivo)
            except Clase.DoesNotExist:
                return JsonResponse({"message": f"No hay clase programada para {dia} {horario} el {fecha_objetivo}."})

            alumnos = []

            # Alumnos regulares
            alumnos_regulares = AlumnoClase.objects.filter(id_clase=clase)
            for ac in alumnos_regulares:
                persona = ac.id_alumno_paquete.id_alumno.id_persona
                alumnos.append({
                    "nombre": persona.nombre,
                    "apellido": persona.apellido,
                    "telefono": persona.telefono,
                    "tipo": "regular"
                })

            # Alumnos ocasionales
            alumnos_ocasionales = AlumnoClaseOcasional.objects.filter(id_clase=clase)
            for ao in alumnos_ocasionales:
                persona = ao.id_alumno.id_persona
                alumnos.append({
                    "nombre": persona.nombre,
                    "apellido": persona.apellido,
                    "telefono": persona.telefono,
                    "tipo": "ocasional"
                })

            return JsonResponse({
                "dia": dia,
                "horario": horario,
                "fecha": str(fecha_objetivo),
                "alumnos": alumnos
            })

        except Exception as e:
            logging.error(f"Error en obtener_alumnos_clase: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Método no permitido"}, status=405)



@csrf_exempt
def obtener_alumnos_dia(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            dia = data.get("dia")  # Ejemplo: "Martes"

            if not dia:
                return JsonResponse({"error": "Debes enviar 'dia'"}, status=400)


            # Calcular fecha correcta según el día solicitado
            hoy = date.today()
            dia_a_numero = {
                "Lunes": 0,
                "Martes": 1,
                "Miércoles": 2,
                "Jueves": 3,
                "Viernes": 4,
                "Sábado": 5
            }

            # Buscar la próxima fecha que sea el día pedido
            if hoy.weekday() != dia_a_numero[dia]:
                dias_a_sumar = (dia_a_numero[dia] - hoy.weekday()) % 7
                if dias_a_sumar == 0:
                    dias_a_sumar = 7
                fecha_objetivo = hoy + timedelta(days=dias_a_sumar)
            else:
                fecha_objetivo = hoy

            # Buscar clases en la fecha correcta
            clases = Clase.objects.filter(
                fecha=fecha_objetivo,
                id_turno__dia=dia
            )


            if not clases.exists():
                return JsonResponse({"message": f"No hay clases programadas para hoy {dia}."})

            alumnos = []

            for clase in clases:
                # Alumnos regulares
                alumnos_regulares = AlumnoClase.objects.filter(id_clase=clase)
                for ac in alumnos_regulares:
                    persona = ac.id_alumno_paquete.id_alumno.id_persona
                    alumnos.append({
                        "nombre": persona.nombre,
                        "apellido": persona.apellido,
                        "telefono": persona.telefono,
                        "turno": clase.id_turno.horario.strftime("%H:%M"),
                        "tipo": "regular"
                    })

                # Alumnos ocasionales
                alumnos_ocasionales = AlumnoClaseOcasional.objects.filter(id_clase=clase)
                for ao in alumnos_ocasionales:
                    persona = ao.id_alumno.id_persona
                    alumnos.append({
                        "nombre": persona.nombre,
                        "apellido": persona.apellido,
                        "telefono": persona.telefono,
                        "turno": clase.id_turno.horario.strftime("%H:%M"),
                        "tipo": "ocasional"
                    })

            return JsonResponse({
                "dia": dia,
                "fecha": str(fecha_objetivo),
                "alumnos": alumnos
            })

        except Exception as e:
            logging.error(f"Error en obtener_alumnos_dia: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    else:
        return JsonResponse({"error": "Método no permitido"}, status=405)




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


@csrf_exempt
def verificar_turno_a_partir_de(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            dia = data.get("dia")  # Opcional ahora
            hora_minima = data.get("hora_minima")

            if not hora_minima:
                return JsonResponse({"error": "Debes enviar 'hora_minima'"}, status=400)

            if dia:
                dias_a_buscar = [dia]
            else:
                dias_a_buscar = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]

            resultados = []

            for dia_actual in dias_a_buscar:
                turnos_disponibles = buscar_turnos_disponibles(dia_actual, operador_hora="gte", hora_referencia=hora_minima)

                if turnos_disponibles:
                    resultados.append({
                        "dia": dia_actual,
                        "hora_minima": hora_minima,
                        "turnos_disponibles": turnos_disponibles
                    })

            if not resultados:
                return JsonResponse({"message": f"No hay turnos disponibles después de {hora_minima}."})

            return JsonResponse({"resultados": resultados})

        except Exception as e:
            logging.error(f"Error en verificar_turno_a_partir_de: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Método no permitido"}, status=405)

@csrf_exempt
def verificar_turno_antes_de(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            dia = data.get("dia")  # Ejemplo: "Miércoles"
            hora_maxima = data.get("hora_maxima")  # Ejemplo: "10:00"

            if not dia or not hora_maxima:
                return JsonResponse({"error": "Debes enviar 'dia' y 'hora_maxima'"}, status=400)

            turnos_disponibles = buscar_turnos_disponibles(dia, operador_hora="lt", hora_referencia=hora_maxima)

            if not turnos_disponibles:
                return JsonResponse({"message": f"No hay turnos disponibles para {dia} antes de {hora_maxima}."})

            return JsonResponse({
                "dia": dia,
                "hora_maxima": hora_maxima,
                "turnos_disponibles": turnos_disponibles
            })

        except Exception as e:
            logging.error(f"Error en verificar_turno_antes_de: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Método no permitido"}, status=405)


@csrf_exempt
def verificar_turno_manana(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            dia = data.get("dia")

            if not dia:
                return JsonResponse({"error": "Debes enviar 'dia'"}, status=400)

            turnos_disponibles = buscar_turnos_disponibles(dia, operador_hora="lt", hora_referencia="12:00")

            if not turnos_disponibles:
                return JsonResponse({"message": f"No hay turnos disponibles para la mañana del {dia}."})

            return JsonResponse({
                "dia": dia,
                "turnos_disponibles_mañana": turnos_disponibles
            })

        except Exception as e:
            logging.error(f"Error en verificar_turno_manana: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Método no permitido"}, status=405)


def buscar_turnos_disponibles(dia, operador_hora=None, hora_referencia=None):
    """
    Busca turnos disponibles de acuerdo al día y un criterio de horario opcional.
    
    Args:
        dia (str): Día de la semana ("Martes").
        operador_hora (str, optional): Uno de 'gte' (mayor o igual), 'lt' (menor), 'exact' (igual). Default None.
        hora_referencia (str, optional): Hora en formato "HH:MM" para comparar. Default None.
    
    Returns:
        list: Lista de turnos disponibles [{'horario': 'HH:MM', 'lugares_disponibles': int}]
    """
    filtros = {"dia": dia}

    if operador_hora and hora_referencia:
        filtros[f"horario__{operador_hora}"] = hora_referencia

    turnos = Turno.objects.filter(**filtros).order_by('horario')

    turnos_disponibles = []
    for turno in turnos:
        lugares_disponibles = 4 - turno.lugares_ocupados
        if lugares_disponibles > 0:
            turnos_disponibles.append({
                "horario": turno.horario.strftime("%H:%M"),
                "lugares_disponibles": lugares_disponibles
            })

    return turnos_disponibles



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
