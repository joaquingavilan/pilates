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
import unicodedata
from difflib import get_close_matches

DAY_INDEX = {
    "Lunes": 0,
    "Martes": 1,
    "Miércoles": 2,
    "Jueves": 3,
    "Viernes": 4,
    "Sábado": 5,
    "Domingo": 6
}
DAY_NAME_ES = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo"
}


@csrf_exempt
@transaction.atomic
def reprogramar_clase(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    errores = []

    try:
        data = json.loads(request.body)
        id_alumno = data.get("id_alumno")
        id_clase_origen = data.get("id_clase_origen")
        dia_destino = data.get("dia_destino")
        hora_destino = data.get("hora_destino")
        fecha_destino_str = data.get("fecha_destino")

        if not id_alumno:
            errores.append("Falta el campo 'id_alumno'.")
        if not id_clase_origen:
            errores.append("Falta el campo 'id_clase_origen'.")
        if not dia_destino or not hora_destino or not fecha_destino_str:
            errores.append("Debes proporcionar 'dia_destino', 'hora_destino' y 'fecha_destino'.")

        try:
            fecha_destino = datetime.strptime(fecha_destino_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            errores.append("La fecha debe tener el formato YYYY-MM-DD.")

        if errores:
            return JsonResponse({"errores": errores}, status=400)

        alumno = Alumno.objects.get(id_alumno=id_alumno)

        clase_origen = Clase.objects.get(id_clase=id_clase_origen)

        # Determinar si es regular u ocasional
        paquetes = AlumnoPaquete.objects.filter(id_alumno=alumno)
        alumno_clase = AlumnoClase.objects.filter(id_alumno_paquete__in=paquetes, id_clase=clase_origen).first()
        tipo_alumno = "regular" if alumno_clase else None


        if not alumno_clase:
            alumno_clase_ocasional = AlumnoClaseOcasional.objects.filter(id_alumno=alumno, id_clase=clase_origen).first()
            if alumno_clase_ocasional:
                tipo_alumno = "ocasional"

        if not tipo_alumno:
            return JsonResponse({"errores": ["El alumno no está registrado en la clase de origen."]}, status=404)

        # Verificar clase destino
        try:
            turno_destino = Turno.objects.get(dia=dia_destino, horario=hora_destino)
        except Turno.DoesNotExist:
            return JsonResponse({"errores": ["No existe el turno destino especificado."]}, status=404)

        try:
            clase_destino = Clase.objects.get(id_turno=turno_destino, fecha=fecha_destino)
        except Clase.DoesNotExist:
            return JsonResponse({"errores": ["No existe una clase programada para ese turno y fecha."]}, status=404)

        if clase_destino.total_inscriptos >= 4:
            return JsonResponse({"errores": ["La clase destino ya está llena."]}, status=400)

        # Verificar si ya está anotado a la clase destino
        ya_en_clase = False
        if tipo_alumno == "regular":
            ya_en_clase = AlumnoClase.objects.filter(
                id_alumno_paquete__id_alumno=alumno,
                id_clase=clase_destino
            ).exists()
        else:
            ya_en_clase = AlumnoClaseOcasional.objects.filter(
                id_alumno=alumno,
                id_clase=clase_destino
            ).exists()

        if ya_en_clase:
            return JsonResponse({"errores": ["El alumno ya está registrado en la clase destino."]}, status=400)

        # Realizar la reprogramación
        if tipo_alumno == "regular":
            alumno_paquete = alumno_clase.id_alumno_paquete
            alumno_clase.estado = "reprogramó"
            alumno_clase.save()

            AlumnoClase.objects.create(
                id_alumno_paquete=alumno_paquete,
                id_clase=clase_destino,
                estado="recuperó"
            )
        else:
            alumno_clase_ocasional.estado = "canceló"
            alumno_clase_ocasional.save()

            AlumnoClaseOcasional.objects.create(
                id_alumno=alumno,
                id_clase=clase_destino,
                estado="reservado"
            )

        return JsonResponse({
            "message": "Clase reprogramada correctamente.",
            "tipo_alumno": tipo_alumno,
            "clase_origen": {
                "fecha": str(clase_origen.fecha),
                "hora": clase_origen.id_turno.horario.strftime("%H:%M")
            },
            "clase_destino": {
                "fecha": str(clase_destino.fecha),
                "hora": clase_destino.id_turno.horario.strftime("%H:%M")
            }
        })

    except Alumno.DoesNotExist:
        return JsonResponse({"errores": ["Alumno no encontrado."]}, status=404)
    except Clase.DoesNotExist:
        return JsonResponse({"errores": ["Clase de origen no encontrada."]}, status=404)
    except Exception as e:
        logging.error(f"[reprogramar_clase] Error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@transaction.atomic
def obtener_clases_agendadas(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    errores = []

    try:
        data = json.loads(request.body)
        id_alumno = data.get("id_alumno")
        fecha_minima_str = data.get("fecha_minima")

        if not id_alumno:
            errores.append("Falta el campo 'id_alumno'.")

        # Validar y convertir fecha
        fecha_minima = date.today()
        if fecha_minima_str:
            try:
                fecha_minima = datetime.strptime(fecha_minima_str, "%Y-%m-%d").date()
            except ValueError:
                errores.append("La fecha debe tener el formato YYYY-MM-DD.")

        if errores:
            return JsonResponse({"errores": errores}, status=400)

        try:
            alumno = Alumno.objects.get(id_alumno=id_alumno)
        except Alumno.DoesNotExist:
            return JsonResponse({"errores": ["Alumno no encontrado"]}, status=404)

        clases_resultado = []

        if alumno.estado == "regular":
            clases_regulares = AlumnoClase.objects.filter(
                id_alumno_paquete__id_alumno=alumno
            ).select_related("id_clase", "id_clase__id_turno")

            for ac in clases_regulares:
                clase = ac.id_clase
                clases_resultado.append({
                    "id_clase": clase.id_clase,
                    "fecha": str(clase.fecha),
                    "dia": clase.fecha.strftime("%A").capitalize(),
                    "hora": clase.id_turno.horario.strftime("%H:%M"),
                    "tipo": "regular",
                    "estado": ac.estado
                })

        elif alumno.estado == "ocasional":
            clases_ocasionales = AlumnoClaseOcasional.objects.filter(
                id_alumno=alumno,
                id_clase__fecha__gte=fecha_minima
            ).select_related("id_clase", "id_clase__id_turno")

            for ao in clases_ocasionales:
                clase = ao.id_clase
                clases_resultado.append({
                "id_clase": clase.id_clase,
                "fecha": str(clase.fecha),
                "dia": clase.fecha.strftime("%A").capitalize(),  # o un mapa ES consistente
                "hora": clase.id_turno.horario.strftime("%H:%M"),
                "tipo": "ocasional",
                "estado": ao.estado
                })


        else:
            return JsonResponse({
                "clases": [],
                "message": "El alumno está inactivo, no tiene clases agendadas actualmente."
            })

        # Filtrar por fecha mínima
        clases_filtradas = [
            c for c in clases_resultado
            if datetime.strptime(c["fecha"], "%Y-%m-%d").date() >= fecha_minima
        ]

        clases_ordenadas = sorted(clases_filtradas, key=lambda c: (c["fecha"], c["hora"]))

        return JsonResponse({"clases": clases_ordenadas})

    except Exception as e:
        logging.error(f"[obtener_clases_agendadas] Error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

































def normalizar(texto):
    if not texto:
        return ""
    texto = texto.strip().lower()
    texto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn')

def resolver_nombre(nombre_dict, alumnos_dict):
    """
    Intenta matchear el nombre recibido con los nombres normalizados de alumnos anotados.
    Retorna id_alumno si hay un único match.
    """
    nombre_input = normalizar(nombre_dict.get("nombre", ""))
    apellido_input = normalizar(nombre_dict.get("apellido", ""))
    nombre_completo_input = f"{nombre_input} {apellido_input}".strip()

    posibles = []

    # 1. Coincidencia exacta nombre completo
    if nombre_completo_input in alumnos_dict:
        return nombre_completo_input

    # 2. Substring parcial (nombre dentro de nombre completo anotado)
    for nombre_guardado in alumnos_dict:
        if nombre_input and nombre_input in nombre_guardado:
            if apellido_input and apellido_input in nombre_guardado:
                posibles.append(nombre_guardado)
            elif not apellido_input:
                posibles.append(nombre_guardado)

    if len(posibles) == 1:
        return posibles[0]

    # 3. Fuzzy
    difusos = get_close_matches(nombre_completo_input, alumnos_dict.keys(), n=1, cutoff=0.85)
    if len(difusos) == 1:
        return difusos[0]

    return None


@csrf_exempt
@transaction.atomic
def registrar_asistencias(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    errores = []
    try:
        data = json.loads(request.body)
        dia = data.get("dia")
        horario = data.get("horario")
        fecha_str = data.get("fecha")
        faltaron = data.get("faltaron", [])
        asistieron = data.get("asistieron", [])

        if not dia:
            errores.append("Falta el campo 'dia'.")
        if not horario:
            errores.append("Falta el campo 'horario'.")

        if errores:
            return JsonResponse({"errores": errores}, status=400)

        # Validar fecha
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                if fecha > date.today():
                    errores.append("No se puede registrar asistencia para fechas futuras.")
            except ValueError:
                errores.append("Formato de fecha inválido, debe ser YYYY-MM-DD.")
        else:
            fecha = date.today()

        if errores:
            return JsonResponse({"errores": errores}, status=400)

        # Turno
        try:
            turno = Turno.objects.get(dia=dia, horario=horario)
        except Turno.DoesNotExist:
            errores.append("Turno no encontrado.")
            return JsonResponse({"errores": errores}, status=404)

        # Clase
        try:
            clase = Clase.objects.get(id_turno=turno, fecha=fecha)
        except Clase.DoesNotExist:
            errores.append("Clase no encontrada para ese turno y fecha.")
            return JsonResponse({"errores": errores}, status=404)

        # Construir diccionario: nombre_normalizado → (id_alumno, instancia, tipo)
        alumnos_dict = {}

        alumnos_regulares = AlumnoClase.objects.filter(id_clase=clase)
        for ac in alumnos_regulares:
            persona = ac.id_alumno_paquete.id_alumno.id_persona
            nombre = normalizar(f"{persona.nombre} {persona.apellido}")
            alumnos_dict[nombre] = (persona.id_persona, ac, "regular")

        alumnos_ocasionales = AlumnoClaseOcasional.objects.filter(id_clase=clase)
        for ao in alumnos_ocasionales:
            persona = ao.id_alumno.id_persona
            nombre = normalizar(f"{persona.nombre} {persona.apellido}")
            alumnos_dict[nombre] = (persona.id_persona, ao, "ocasional")

        procesados = []
        ya_procesados = set()
        no_encontrados = []

        # Marcar faltaron
        for alumno_dict in faltaron:
            nombre_match = resolver_nombre(alumno_dict, alumnos_dict)
            if nombre_match:
                _, instancia, _ = alumnos_dict[nombre_match]
                instancia.estado = "faltó"
                instancia.save()
                if nombre_match not in ya_procesados:
                    procesados.append(nombre_match)
                    ya_procesados.add(nombre_match)
            else:
                nombre_visible = alumno_dict.get("nombre", "")
                apellido_visible = alumno_dict.get("apellido", "")
                no_encontrados.append(f"{nombre_visible} {apellido_visible}".strip())

        # Marcar asistieron
        for alumno_dict in asistieron:
            nombre_match = resolver_nombre(alumno_dict, alumnos_dict)
            if nombre_match and nombre_match not in ya_procesados:
                _, instancia, _ = alumnos_dict[nombre_match]
                instancia.estado = "asistió"
                instancia.save()
                procesados.append(nombre_match)
                ya_procesados.add(nombre_match)
            elif not nombre_match:
                nombre_visible = alumno_dict.get("nombre", "")
                apellido_visible = alumno_dict.get("apellido", "")
                no_encontrados.append(f"{nombre_visible} {apellido_visible}".strip())

        return JsonResponse({
            "asistencias_registradas": procesados,
            "alumnos_no_encontrados": no_encontrados,
            "message": f"Asistencias registradas correctamente para {len(procesados)} alumnos."
        })

    except Exception as e:
        logging.error(f"[registrar_asistencias] Error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


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
def obtener_id_alumno(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            telefono = data.get("telefono")
            nombre = data.get("nombre", "").strip().lower()
            apellido = data.get("apellido", "").strip().lower()

            if not telefono:
                return JsonResponse({"error": "El campo 'telefono' es obligatorio."}, status=400)

            personas = Persona.objects.filter(telefono=telefono.strip())
            personas_filtradas = []

            if personas.count() == 0:
                return JsonResponse({"error": "No se encontró ninguna persona con ese teléfono."}, status=404)

            if personas.count() == 1:
                persona = personas.first()
            else:
                # Más de una persona con ese teléfono, aplicar comparación con nombre y apellido
                for p in personas:
                    if p.nombre.strip().lower() == nombre and p.apellido.strip().lower() == apellido:
                        personas_filtradas.append(p)

                if len(personas_filtradas) == 0:
                    return JsonResponse({
                        "error": "Hay varias personas con ese teléfono, pero ninguna coincide exactamente con el nombre y apellido."
                    }, status=400)
                if len(personas_filtradas) > 1:
                    return JsonResponse({
                        "error": "Se encontró más de una persona con ese teléfono, nombre y apellido."
                    }, status=400)

                persona = personas_filtradas[0]

            # Buscar Alumno asociado
            try:
                alumno = Alumno.objects.get(id_persona=persona)
            except Alumno.DoesNotExist:
                return JsonResponse({"error": "La persona existe pero no está registrada como alumno."}, status=404)

            return JsonResponse({
                "id_alumno": alumno.id_alumno,
                "estado": alumno.estado
            })

        except Exception as e:
            logging.error(f"[obtener_id_alumno] Error: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

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
    if not data.get("hora_turno"):
        errores.append("Debe proporcionar el horario del turno.")

    fecha_clase = None
    dia_turno = data.get("dia_turno")
    fecha_str = data.get("fecha")

    # 📌 Resolver fecha y día
    if fecha_str:
        try:
            fecha_clase = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            if not dia_turno:
                dia_numero = fecha_clase.weekday()
                dia_nombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                dia_turno = dia_nombre[dia_numero]
        except ValueError:
            errores.append("La fecha debe tener el formato YYYY-MM-DD.")
    else:
        if not dia_turno:
            errores.append("Debe proporcionar el día del turno si no proporciona la fecha.")
        else:
            fecha_clase = obtener_fecha_proximo_dia(dia_turno)

    turno = None
    clase = None

    if not errores:
        # 📌 Obtener turno
        try:
            turno = Turno.objects.get(dia=dia_turno, horario=data["hora_turno"])
        except Turno.DoesNotExist:
            errores.append(f"El turno {dia_turno} {data['hora_turno']} no existe.")

    if not errores:
        # 📌 Validar clase específica en esa fecha
        try:
            clase = Clase.objects.get(id_turno=turno, fecha=fecha_clase)
            if clase.total_inscriptos >= 4:
                errores.append(f"La clase del {fecha_clase} a las {data['hora_turno']} ya está llena.")
        except Clase.DoesNotExist:
            errores.append(f"No existe clase programada para {fecha_clase} en el turno {dia_turno} {data['hora_turno']}.")


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

    return {
        "mensaje": "Alumno ocasional registrado correctamente",
        "fecha_clase": str(fecha_clase),
        "turno": f"{dia_turno} {data['hora_turno']}"
    }



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
        canal_captacion=data.get("canal_captacion"),
        estado="regular"
    )

    alumno_paquete = AlumnoPaquete.objects.create(
        id_alumno=alumno,
        id_paquete=paquete,
        estado='activo',
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
                return JsonResponse({"message": "No hay un turno registrado para ese día y horario. No tenemos clases en ese horario."})

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
            lugares_ocupados = lugares_ocupados = (AlumnoClase.objects.filter(id_clase=clase).count() +
                    AlumnoClaseOcasional.objects.filter(id_clase=clase).count())
            
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
            telefono = data.get("telefono")
            nombre = data.get("nombre", "").strip().lower()
            apellido = data.get("apellido", "").strip().lower()
            nuevo_ruc = data.get("ruc")

            errores = []
            if not telefono:
                errores.append("El teléfono es obligatorio.")
            if not nuevo_ruc:
                errores.append("El nuevo RUC es obligatorio.")

            if errores:
                return JsonResponse({"error": " ".join(errores)}, status=400)

            # Buscar por teléfono
            personas = Persona.objects.filter(telefono=telefono.strip())
            personas_filtradas = []

            if personas.count() == 0:
                return JsonResponse({"error": "No se encontró ninguna persona con ese teléfono."}, status=404)

            if personas.count() == 1:
                persona = personas.first()
            else:
                # Hay más de una → usar nombre y apellido para desambiguar
                for p in personas:
                    if p.nombre.strip().lower() == nombre and p.apellido.strip().lower() == apellido:
                        personas_filtradas.append(p)

                if len(personas_filtradas) == 0:
                    return JsonResponse({
                        "error": "Hay varias personas con ese teléfono, pero ninguna coincide exactamente con el nombre y apellido."
                    }, status=400)
                if len(personas_filtradas) > 1:
                    return JsonResponse({
                        "error": "Se encontró más de una persona con ese teléfono, nombre y apellido."
                    }, status=400)

                persona = personas_filtradas[0]

            # Actualizar RUC
            persona.ruc = nuevo_ruc
            persona.save()

            return JsonResponse({
                "message": f"RUC actualizado correctamente para {persona.nombre} {persona.apellido}."
            })

        except Exception as e:
            logging.error(f"[actualizar_ruc] Error: {str(e)}")
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
