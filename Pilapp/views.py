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
    """
    POST /reprogramar_clase/
    ------------------------
    Reprograma una clase de un alumno (regular u ocasional) hacia otra fecha y horario.

    Métodos admitidos:
    - POST → ejecuta la reprogramación.
    - Otros métodos → 405 {"error": "Método no permitido"}

    Entradas (JSON):
    - id_alumno (int)                 [obligatorio]
    - id_clase_origen (int)           [obligatorio]
    - dia_destino (str)               [obligatorio]
    - hora_destino (str)              [obligatorio]
    - fecha_destino (str, YYYY-MM-DD) [obligatorio]

    Validaciones y posibles errores:
    - Falta alguno de los campos anteriores → 400 {"errores": ["Falta el campo '...'", ...]}
    - Fecha con formato inválido → 400 {"errores": ["La fecha debe tener el formato YYYY-MM-DD."]}
    - Alumno no encontrado → 404 {"errores": ["Alumno no encontrado."]}
    - Clase de origen no encontrada → 404 {"errores": ["Clase de origen no encontrada."]}
    - Alumno no registrado en la clase de origen → 404 {"errores": ["El alumno no está registrado en la clase de origen."]}
    - Turno destino inexistente → 404 {"errores": ["No existe el turno destino especificado."]}
    - Clase destino inexistente → 404 {"errores": ["No existe una clase programada para ese turno y fecha."]}
    - Clase destino con cupo completo (>=4) → 400 {"errores": ["La clase destino ya está llena."]}
    - Alumno ya registrado en clase destino → 400 {"errores": ["El alumno ya está registrado en la clase destino."]}
    - Error no controlado → 500 {"error": "<mensaje de excepción>"}

    Operaciones internas observables:
    - Determina si el alumno es "regular" (AlumnoClase) u "ocasional" (AlumnoClaseOcasional).
    - Si es regular:
    • marca la clase original como estado="reprogramó".
    • crea un nuevo AlumnoClase con estado="recuperó".
    - Si es ocasional:
    • marca la clase original como estado="canceló".
    • crea un nuevo AlumnoClaseOcasional con estado="reservado".

    Respuesta 200 OK:
    {
    "message": "Clase reprogramada correctamente.",
    "tipo_alumno": "regular" | "ocasional",
    "clase_origen":  {"fecha": "YYYY-MM-DD", "hora": "HH:MM"},
    "clase_destino": {"fecha": "YYYY-MM-DD", "hora": "HH:MM"}
    }
    """
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
    """
    POST /obtener_clases_agendadas/
    -------------------------------
    Devuelve la lista de clases agendadas para un alumno, filtradas desde una fecha mínima (por defecto, la fecha actual).

    Métodos admitidos:
    - POST → obtiene las clases agendadas.
    - Otros métodos → 405 {"error": "Método no permitido"}

    Entradas (JSON):
    - id_alumno (int)                 [obligatorio]
    - fecha_minima (str, YYYY-MM-DD)  [opcional]

    Validaciones y posibles errores:
    - Falta 'id_alumno' → 400 {"errores": ["Falta el campo 'id_alumno'."]}
    - 'fecha_minima' con formato inválido → 400 {"errores": ["La fecha debe tener el formato YYYY-MM-DD."]}
    - Alumno no encontrado → 404 {"errores": ["Alumno no encontrado"]}
    - Error no controlado → 500 {"error": "<mensaje de excepción>"}

    Comportamiento según estado del alumno:
    - estado == "regular" → consulta en AlumnoClase (clases regulares).
    - estado == "ocasional" → consulta en AlumnoClaseOcasional (clases con fecha >= fecha_minima).
    - estado distinto (p. ej. "inactivo") → 200 {"clases": [], "message": "El alumno está inactivo, no tiene clases agendadas actualmente."}

    Cada elemento de la lista "clases" tiene esta estructura:
    {
    "id_clase": int,
    "fecha": "YYYY-MM-DD",
    "dia": "NombreDelDía",
    "hora": "HH:MM",
    "tipo": "regular" | "ocasional",
    "estado": "<estado actual>"
    }

    Respuesta 200 OK:
    {
    "clases": [
        {
        "id_clase": 12,
        "fecha": "2025-11-10",
        "dia": "Lunes",
        "hora": "18:00",
        "tipo": "regular",
        "estado": "reservado"
        },
        ...
    ]
    }
    """

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
    """
    POST /registrar_asistencias/
    ----------------------------
    Registra las asistencias y ausencias de alumnos (regulares y ocasionales) en una clase determinada por día, horario y fecha.

    Métodos admitidos:
    - POST → registra las asistencias.
    - Otros métodos → 405 {"error": "Método no permitido"}

    Entradas (JSON):
    - dia (str)                   [obligatorio]
    - horario (str)               [obligatorio]
    - fecha (str, YYYY-MM-DD)     [opcional; si falta, se usa la fecha actual del sistema]
    - asistieron (list[dict])     [opcional; formato {"nombre": "Ana", "apellido": "Pérez"}]
    - faltaron (list[dict])       [opcional; formato {"nombre": "Laura", "apellido": "Gómez"}]

    Validaciones y posibles errores:
    - Falta 'dia' o 'horario' → 400 {"errores": ["Falta el campo 'dia'.", "Falta el campo 'horario'."]}
    - 'fecha' con formato inválido → 400 {"errores": ["Formato de fecha inválido, debe ser YYYY-MM-DD."]}
    - 'fecha' futura → 400 {"errores": ["No se puede registrar asistencia para fechas futuras."]}
    - Turno no encontrado → 404 {"errores": ["Turno no encontrado."]}
    - Clase no encontrada para ese turno y fecha → 404 {"errores": ["Clase no encontrada para ese turno y fecha."]}
    - Excepción no controlada → 500 {"error": "<mensaje de excepción>"}

    Comportamiento interno:
    - Busca el turno (Turno.dia, Turno.horario).
    - Busca la clase correspondiente (Clase.id_turno, Clase.fecha).
    - Crea un diccionario de alumnos de la clase (regulares y ocasionales), indexados por nombre normalizado.
    - Actualiza el estado de cada alumno:
    • "faltó" para los incluidos en `faltaron`
    • "asistió" para los incluidos en `asistieron`
    - Si el nombre no se encuentra, se agrega a `alumnos_no_encontrados`.

    Respuesta 200 OK:
    {
    "asistencias_registradas": ["ana pérez", "laura gómez", ...],
    "alumnos_no_encontrados": ["maría fernández", ...],
    "message": "Asistencias registradas correctamente para <N> alumnos."
    }
    """

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
    """
    Calcula la próxima fecha (tipo date) correspondiente a un día de la semana dado.
    """
    logging.info(f"[obtener_fecha_proximo_dia] Calculando próxima fecha para día: {dia_nombre}")
    
    hoy = datetime.now().date()
    logging.debug(f"[obtener_fecha_proximo_dia] Fecha de hoy: {hoy}")
    
    dia_actual = hoy.weekday()
    logging.debug(f"[obtener_fecha_proximo_dia] Día actual (weekday): {dia_actual}")
    
    dia_objetivo = DAY_INDEX[dia_nombre]
    logging.debug(f"[obtener_fecha_proximo_dia] Día objetivo (weekday): {dia_objetivo} para '{dia_nombre}'")
    
    dias_hasta_objetivo = (dia_objetivo - dia_actual + 7) % 7
    logging.debug(f"[obtener_fecha_proximo_dia] Días hasta objetivo (inicial): {dias_hasta_objetivo}")
    
    if dias_hasta_objetivo == 0:
        dias_hasta_objetivo = 7  # Si es hoy, te vas al próximo mismo día (no hoy mismo)
        logging.debug(f"[obtener_fecha_proximo_dia] Es hoy, ajustando a próxima semana: {dias_hasta_objetivo} días")
    
    fecha_objetivo = hoy + timedelta(days=dias_hasta_objetivo)
    logging.info(f"[obtener_fecha_proximo_dia] Fecha calculada: {fecha_objetivo} ({dia_nombre})")
    
    return fecha_objetivo

@csrf_exempt
def obtener_id_alumno(request):
    """
    POST /obtener_id_alumno/
    ------------------------
    Obtiene el ID y el estado de un alumno a partir de su número de teléfono.  
    Si existen múltiples personas con el mismo teléfono, utiliza nombre y apellido para desambiguar.

    Métodos admitidos:
    - POST → realiza la búsqueda del alumno.
    - Otros métodos → 405 {"error": "Método no permitido"}

    Entradas (JSON):
    - telefono (str)    [obligatorio]
    - nombre (str)      [opcional; usado para desambiguar si hay más de una persona con el mismo teléfono]
    - apellido (str)    [opcional; usado para desambiguar si hay más de una persona con el mismo teléfono]

    Validaciones y posibles errores:
    - Falta 'telefono' → 400 {"error": "El campo 'telefono' es obligatorio."}
    - Ninguna persona con ese teléfono → 404 {"error": "No se encontró ninguna persona con ese teléfono."}
    - Varias personas con el mismo teléfono y sin coincidencia exacta de nombre/apellido → 400 {"error": "Hay varias personas con ese teléfono, pero ninguna coincide exactamente con el nombre y apellido."}
    - Más de una coincidencia exacta → 400 {"error": "Se encontró más de una persona con ese teléfono, nombre y apellido."}
    - Persona sin registro como alumno → 404 {"error": "La persona existe pero no está registrada como alumno."}
    - Error no controlado → 500 {"error": "<mensaje de excepción>"}

    Salida exitosa (200 OK):
    {
    "id_alumno": <int>,
    "estado": "<regular|ocasional|inactivo>"
    }
    """

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
    """
    POST /registrar_alumno_ocasional/
    ---------------------------------
    Registra un nuevo alumno ocasional en una clase puntual (sin paquete).

    Métodos admitidos:
    - POST → crea la persona, el alumno y su registro en una clase existente.
    - Otros métodos → 405 {"error": "Método no permitido"}

    Entradas (JSON):
    - nombre (str)              [obligatorio]
    - apellido (str)            [obligatorio]
    - telefono (str)            [obligatorio]
    - hora_turno (str)          [obligatorio]
    - dia_turno (str)           [opcional si se envía 'fecha']
    - fecha (str, YYYY-MM-DD)   [opcional]
    - canal_captacion (str)     [opcional]
    - observaciones (str)       [opcional]

    Validaciones y posibles errores:
    - Falta alguno de los campos obligatorios → ValueError con mensaje unificado.
    - 'fecha' con formato inválido → "La fecha debe tener el formato YYYY-MM-DD."
    - Si no se proporciona 'fecha' ni 'dia_turno' → "Debe proporcionar el día del turno si no proporciona la fecha."
    - Turno inexistente → "El turno <día> <hora> no existe."
    - Clase inexistente en ese turno/fecha → "No existe clase programada para <fecha> en el turno <día> <hora>."
    - Clase llena (≥4 inscriptos) → "La clase del <fecha> a las <hora> ya está llena."
    - Excepción no controlada → 400 {"error": "<mensaje>"}

    Comportamiento interno:
    1. Si se envía `fecha`:
    - Se convierte a date.
    - Si falta `dia_turno`, se infiere desde la fecha.
    2. Si no se envía `fecha`, calcula la próxima fecha correspondiente a `dia_turno` (usando `obtener_fecha_proximo_dia`).
    3. Busca el `Turno` correspondiente al día y horario.
    4. Busca la `Clase` existente en esa fecha.
    5. Si hay cupo, crea:
    - Una nueva `Persona`.
    - Un `Alumno` con estado `"ocasional"`.
    - Un `AlumnoClaseOcasional` asociado con estado `"reservado"`.

    Salida exitosa (200 OK):
    {
    "mensaje": "Alumno ocasional registrado correctamente",
    "fecha_clase": "YYYY-MM-DD",
    "turno": "Día HH:MM"
    }
    """

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
    """
    Registra en base de datos un nuevo alumno ocasional y lo asigna a una clase específica.

    Parámetros:
    - data (dict): Diccionario con los datos de entrada.  
    Claves esperadas:
        - nombre (str)              [obligatorio]
        - apellido (str)            [obligatorio]
        - telefono (str)            [obligatorio]
        - hora_turno (str)          [obligatorio]
        - dia_turno (str)           [opcional si se envía 'fecha']
        - fecha (str, YYYY-MM-DD)   [opcional]
        - canal_captacion (str)     [opcional]
        - observaciones (str)       [opcional]

    Validaciones:
    - Verifica que existan los campos obligatorios.
    - Si se envía `fecha`, la convierte a `datetime.date`.  
    - Si no se envía `dia_turno`, lo deduce automáticamente desde la fecha.  
    - Si el formato de `fecha` es incorrecto, agrega error.
    - Si no se envía `fecha`, requiere `dia_turno` y calcula la próxima fecha válida usando `obtener_fecha_proximo_dia`.
    - Verifica que exista un `Turno` para el `dia_turno` y `hora_turno`.
    - Verifica que exista una `Clase` para ese turno y fecha, y que no esté completa (`total_inscriptos < 4`).
    - Si hay errores acumulados, lanza `ValueError` con el resumen de los mensajes concatenados.

    Acciones ejecutadas:
    1. Crea una instancia de `Persona` (nombre, apellido, teléfono, observaciones).
    2. Crea un `Alumno` asociado con esa persona (`estado="ocasional"`).
    3. Crea un registro en `AlumnoClaseOcasional` vinculado a la `Clase` existente, con `estado="reservado"`.

    Retorna:
    - dict con los datos del registro creado:
    {
        "mensaje": "Alumno ocasional registrado correctamente",
        "fecha_clase": "YYYY-MM-DD",
        "turno": "Día HH:MM"
    }

    Excepciones:
    - ValueError: cuando se detectan errores de validación o disponibilidad.
    - Cualquier otra excepción será capturada por la vista superior (`registrar_alumno_ocasional`) y devuelta como JSON con status 400.
    """

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
    """
    POST /registrar_alumno/
    -----------------------
    Registra un nuevo alumno regular con un paquete de clases y sus turnos asociados.

    Métodos admitidos:
    - POST → crea la persona, el alumno, el paquete y las clases asociadas.
    - Otros métodos → 405 {"error": "Método no permitido"}

    Entradas (JSON):
    - nombre (str)                 [obligatorio]
    - apellido (str)               [obligatorio]
    - telefono (str)               [obligatorio]
    - paquete (int)                [obligatorio] cantidad de clases (ej. 4, 8, 12)
    - turnos (list[str])           [obligatorio] formato ["Lunes 18:00", "Miércoles 19:00", ...]
    - fecha_inicio (str, YYYY-MM-DD) [opcional]
    - canal_captacion (str)        [opcional]
    - ruc (str)                    [opcional]
    - observaciones (str)          [opcional]

    Validaciones y posibles errores:
    - Turno inexistente → "El turno <día> <hora> no existe."
    - Turno con estado "Ocupado" → "El turno <día> <hora> ya tiene su cupo general completo."
    - Paquete inexistente → "Paquete con <n> clases no existe."
    - Clase no programada → "No existe clase programada para <fecha> en el turno <día> <hora>."
    - Clase llena (≥4 inscriptos) → "La clase del <fecha> a las <hora> ya está llena."
    - Excepciones de validación → 400 {"error": "Errores encontrados: ..."}
    - Excepciones no controladas → 400 {"error": "<mensaje de excepción>"}

    Comportamiento interno:
    1. Valida los turnos recibidos, descartando los inexistentes o llenos.
    2. Valida que el paquete de clases exista.
    3. Calcula la cantidad de clases por turno (`paquete.cantidad_clases // len(turnos)`).
    4. Determina las fechas a reservar:
    - Usa `fecha_inicio` si se especifica.
    - Si no, obtiene la próxima fecha para cada turno mediante `obtener_fecha_proximo_dia`.
    - Calcula las fechas reales con `obtener_fechas_turno_normal(id_turno, fecha_inicio, clases_por_turno)`.
    5. Verifica que existan clases programadas y con cupo disponible en esas fechas.
    6. Si todas las validaciones pasan:
    - Crea una `Persona` (nombre, apellido, teléfono, etc.).
    - Crea un `Alumno` asociado (`estado="regular"`).
    - Crea un `AlumnoPaquete` con estado `"activo"`.
    - Registra los turnos (`AlumnoPaqueteTurno`) y las clases (`AlumnoClase` con estado `"pendiente"`).

    Salida exitosa (200 OK):
    {
    "message": "Alumno registrado exitosamente"
    }
    """

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
    """
    Procesa los datos recibidos en /registrar_alumno/ y realiza las validaciones y registros en base de datos.
    """
    logging.info(f"[registrar_alumno_datos] Iniciando con data: {data}")
    
    errores = []
    turnos_asignados = []
    clases_a_reservar = []  # Nuevo: para preparar las clases validadas

    # 📌 Validar turnos
    logging.info(f"[registrar_alumno_datos] Validando turnos: {data.get('turnos')}")
    for turno_str in data["turnos"]:
        try:
            dia, horario = turno_str.split()
            logging.debug(f"[registrar_alumno_datos] Buscando turno: dia={dia}, horario={horario}")
            turno = Turno.objects.get(dia=dia, horario=horario)
            logging.debug(f"[registrar_alumno_datos] Turno encontrado: {turno}, estado={turno.estado}")
            if turno.estado == "Ocupado":
                logging.warning(f"[registrar_alumno_datos] Turno {turno_str} ocupado")
                errores.append(f"El turno {turno_str} ya tiene su cupo general completo.")
            else:
                turnos_asignados.append(turno)
                logging.info(f"[registrar_alumno_datos] Turno {turno_str} asignado correctamente")
        except Turno.DoesNotExist:
            logging.error(f"[registrar_alumno_datos] Turno {turno_str} no existe")
            errores.append(f"El turno {turno_str} no existe.")

    # 📌 Validar paquete
    logging.info(f"[registrar_alumno_datos] Validando paquete: {data.get('paquete')} clases")
    try:
        paquete = Paquete.objects.get(cantidad_clases=data["paquete"])
        logging.info(f"[registrar_alumno_datos] Paquete encontrado: {paquete}")
    except Paquete.DoesNotExist:
        logging.error(f"[registrar_alumno_datos] Paquete con {data['paquete']} clases no existe")
        errores.append(f"Paquete con {data['paquete']} clases no existe.")

    # 📌 Validar clases específicas
    if not errores:
        cantidad_clases = paquete.cantidad_clases
        cantidad_turnos = len(turnos_asignados)
        clases_por_turno = cantidad_clases // cantidad_turnos
        logging.info(f"[registrar_alumno_datos] Distribución: {cantidad_clases} clases / {cantidad_turnos} turnos = {clases_por_turno} clases por turno")

        for turno in turnos_asignados:
            logging.info(f"[registrar_alumno_datos] Procesando turno: {turno.dia} {turno.horario}")
            
            fecha_inicio = data.get("fecha_inicio")
            logging.debug(f"[registrar_alumno_datos] fecha_inicio recibida en data: {fecha_inicio}")
            
            if not fecha_inicio:
                logging.info(f"[registrar_alumno_datos] No hay fecha_inicio, calculando próxima fecha para día: {turno.dia}")
                fecha_calculada = obtener_fecha_proximo_dia(turno.dia)
                logging.info(f"[registrar_alumno_datos] Fecha calculada (date): {fecha_calculada}")
                fecha_inicio = str(fecha_calculada)
                logging.info(f"[registrar_alumno_datos] Fecha convertida a string: {fecha_inicio}")
            
            logging.info(f"[registrar_alumno_datos] Obteniendo fechas para turno_id={turno.id_turno}, fecha_inicio={fecha_inicio}, clases={clases_por_turno}")
            fechas_clases = obtener_fechas_turno_normal(turno.id_turno, fecha_inicio, clases_por_turno)["fechas"]
            logging.info(f"[registrar_alumno_datos] Fechas obtenidas: {fechas_clases}")

            for fecha in fechas_clases:
                fecha_clase = datetime.strptime(fecha, "%Y-%m-%d").date()
                logging.debug(f"[registrar_alumno_datos] Validando clase para fecha: {fecha_clase}")
                try:
                    clase = Clase.objects.get(
                        id_instructor=Instructor.objects.get(id_instructor=1),
                        id_turno=turno,
                        fecha=fecha_clase
                    )
                    logging.debug(f"[registrar_alumno_datos] Clase encontrada: id={clase.id_clase}, inscriptos={clase.total_inscriptos}")
                    if clase.total_inscriptos >= 4:
                        logging.warning(f"[registrar_alumno_datos] Clase llena: {fecha_clase} {turno.horario}")
                        errores.append(f"La clase del {fecha_clase} a las {turno.horario} ya está llena.")
                    else:
                        clases_a_reservar.append((turno, clase))
                        logging.info(f"[registrar_alumno_datos] Clase reservada: {fecha_clase} {turno.horario}")
                except Clase.DoesNotExist:
                    logging.error(f"[registrar_alumno_datos] No existe clase para {fecha_clase} en turno {turno.dia} {turno.horario}")
                    errores.append(f"No existe clase programada para {fecha_clase} en el turno {turno.dia} {turno.horario}.")

    # 📌 Si hay errores, devolverlos todos juntos
    if errores:
        logging.error(f"[registrar_alumno_datos] Errores acumulados: {errores}")
        raise ValueError("Errores encontrados: " + "; ".join(errores))

    # 📌 Crear objetos (solo si todo está validado)
    logging.info(f"[registrar_alumno_datos] Creando persona: {data['nombre']} {data['apellido']}")
    persona = Persona.objects.create(
        nombre=data["nombre"],
        apellido=data["apellido"],
        telefono=data.get("telefono"),
        ruc=data.get("ruc"),
        observaciones=data.get("observaciones")
    )
    logging.info(f"[registrar_alumno_datos] Persona creada: id={persona.id_persona}")

    alumno = Alumno.objects.create(
        id_persona=persona,
        canal_captacion=data.get("canal_captacion"),
        estado="regular"
    )
    logging.info(f"[registrar_alumno_datos] Alumno creado: id={alumno.id_alumno}")

    logging.info(f"[registrar_alumno_datos] Creando AlumnoPaquete con fecha_inicio={fecha_inicio}")
    alumno_paquete = AlumnoPaquete.objects.create(
        id_alumno=alumno,
        id_paquete=paquete,
        estado='activo',
        fecha_inicio=fecha_inicio
    )
    logging.info(f"[registrar_alumno_datos] AlumnoPaquete creado: id={alumno_paquete.id_alumno_paquete}")

    for turno, clase in clases_a_reservar:
        logging.debug(f"[registrar_alumno_datos] Creando AlumnoPaqueteTurno para turno {turno.dia} {turno.horario}")
        AlumnoPaqueteTurno.objects.get_or_create(id_alumno_paquete=alumno_paquete, id_turno=turno)
        
        logging.debug(f"[registrar_alumno_datos] Creando AlumnoClase para clase fecha={clase.fecha}")
        AlumnoClase.objects.create(id_alumno_paquete=alumno_paquete, id_clase=clase, estado="pendiente")

    logging.info(f"[registrar_alumno_datos] Proceso completado exitosamente")
    return {"message": "Alumno registrado exitosamente"}





@csrf_exempt
def listar_precios_paquetes(request):
    """
    GET /listar_precios_paquetes/
    -----------------------------
    Devuelve la lista de paquetes de clases disponibles y sus costos.  
    Permite filtrar opcionalmente por cantidad de clases.

    Métodos admitidos:
    - GET → obtiene la lista de paquetes.
    - Otros métodos → 405 {"error": "Método no permitido"}

    Parámetros (query string):
    - cantidad (int) [opcional] → si se especifica, filtra por la cantidad exacta de clases.

    Comportamiento:
    - Si se envía `cantidad`, busca un solo paquete con esa cantidad de clases.
    • Si existe, devuelve su cantidad y costo.
    • Si no existe, devuelve {"message": "No existe paquete de <cantidad> clases."}
    - Si no se envía `cantidad`, lista todos los paquetes existentes ordenados por cantidad de clases.
    - Los costos se devuelven formateados con separadores de miles usando puntos ("1.200.000").

    Validaciones y posibles errores:
    - Error interno → 500 {"error": "<mensaje de excepción>"}

    Salida exitosa (200 OK):
    {
    "paquetes": [
        {"cantidad_clases": 4, "costo": "180.000"},
        {"cantidad_clases": 8, "costo": "340.000"},
        {"cantidad_clases": 12, "costo": "480.000"}
    ]
    }

    Ejemplo con filtro:
    GET /listar_precios_paquetes/?cantidad=8  
    → {"paquetes": [{"cantidad_clases": 8, "costo": "340.000"}]}
    """

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
    """
    POST /obtener_alumnos_turno/
    ----------------------------
    Devuelve los alumnos (regulares y ocasionales) del **próximo encuentro**
    correspondiente al turno indicado (día + horario).

    Concepto:
    - "Turno" → horario fijo que se repite semanalmente (ej. Martes 18:00).
    - "Clase" → instancia específica de ese turno en una fecha concreta.

    Entradas (JSON):
    - dia (str)       [obligatorio] Ejemplo: "Martes"
    - horario (str)   [obligatorio] Ejemplo: "18:00"

    Lógica:
    1. Busca el turno definido por día y horario (`Turno`).
    2. Calcula la próxima fecha que corresponda a ese turno (puede ser hoy o el próximo martes).
    3. Busca la clase concreta (`Clase`) de ese turno en esa fecha.
    4. Devuelve la lista de alumnos asociados (regulares y ocasionales).

    Errores comunes:
    - Falta de parámetros → 400 {"error": "Debes enviar 'dia' y 'horario'"}
    - Turno inexistente → {"message": "No existe turno para <día> a las <hora>."}
    - Clase no encontrada → {"message": "No hay clase hoy para el turno <día> <hora>."}

    Respuesta:
    {
    "dia": "Martes",
    "horario": "18:00",
    "fecha": "2025-11-11",
    "alumnos": [
        {"nombre": "Laura", "apellido": "Gómez", "telefono": "0981...", "tipo": "regular"},
        {"nombre": "Sofía", "apellido": "Torres", "telefono": "0971...", "tipo": "ocasional"}
    ]
    }
    """


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
    """
    POST /obtener_alumnos_clase/
    ----------------------------
    Devuelve los alumnos (regulares y ocasionales) de una **clase específica**,
    identificada por su turno (día y horario) y una fecha concreta.

    Concepto:
    - "Clase" → la ocurrencia en una fecha particular de un turno semanal.

    Entradas (JSON):
    - dia (str)       [obligatorio] Ejemplo: "Martes"
    - horario (str)   [obligatorio] Ejemplo: "18:00"
    - fecha (str, YYYY-MM-DD) [opcional] → Si no se envía, se usa la próxima fecha para ese turno.

    Lógica:
    1. Busca el `Turno` correspondiente.
    2. Determina la fecha:
    • Usa la recibida, o si falta, calcula la próxima que caiga en ese día.
    3. Busca la `Clase` asociada a ese turno y fecha.
    4. Devuelve todos los alumnos inscriptos en esa clase.

    Errores comunes:
    - Parámetros faltantes → 400 {"error": "Debes enviar 'dia' y 'horario'"}
    - Turno inexistente → {"message": "No existe turno <día> <hora>."}
    - Clase inexistente → {"message": "No hay clase programada para <día> <hora> el <fecha>."}

    Respuesta:
    {
    "dia": "Martes",
    "horario": "18:00",
    "fecha": "2025-11-11",
    "alumnos": [
        {"nombre": "Laura", "apellido": "Gómez", "telefono": "0981...", "tipo": "regular"},
        {"nombre": "Sofía", "apellido": "Torres", "telefono": "0971...", "tipo": "ocasional"}
    ]
    }
    """

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
    """
    POST /obtener_alumnos_dia/
    --------------------------
    Devuelve todos los alumnos (regulares y ocasionales) de **todas las clases**
    que ocurren en un día determinado (por ejemplo, todos los martes próximos).

    Concepto:
    - Devuelve múltiples clases, una por turno, en la fecha que coincide con el día indicado.

    Entradas (JSON):
    - dia (str) [obligatorio] Ejemplo: "Martes"

    Lógica:
    1. Calcula la fecha del próximo día solicitado (ej. próximo martes).
    2. Busca todas las clases (`Clase`) programadas para esa fecha y ese día.
    3. Devuelve los alumnos de todas ellas, indicando a qué turno pertenece cada uno.

    Errores comunes:
    - Falta 'dia' → 400 {"error": "Debes enviar 'dia'"}
    - Sin clases programadas → {"message": "No hay clases programadas para hoy <día>."}

    Respuesta:
    {
    "dia": "Martes",
    "fecha": "2025-11-11",
    "alumnos": [
        {"nombre": "Lucía", "apellido": "Aguirre", "telefono": "0982...", "turno": "17:00", "tipo": "regular"},
        {"nombre": "Nadia", "apellido": "Torres", "telefono": "0974...", "turno": "18:00", "tipo": "ocasional"}
    ]
    }
    """

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
    """
    POST /verificar_turno/
    ----------------------
    Verifica si existe un turno (día + horario) y cuántos lugares disponibles tiene actualmente.

    Concepto:
    - "Turno" = un horario recurrente semanal (ej. Lunes 07:00).
    - No se valida la clase de una fecha específica, sino la configuración general del turno.

    Entradas (JSON):
    - dia (str)       [obligatorio] Ejemplo: "Lunes"
    - horario (str)   [obligatorio] Ejemplo: "07:00"

    Lógica:
    1. Busca el turno configurado con ese día y horario (`Turno`).
    2. Si no existe, devuelve un mensaje indicando que no hay clases en ese horario.
    3. Si existe, calcula los lugares disponibles (4 - lugares_ocupados).
    4. Devuelve un mensaje indicando si hay cupos libres o no.

    Errores:
    - Falta de parámetros → 400 {"error": "Debes enviar 'dia' y 'horario'"}
    - Turno inexistente → {"message": "No hay un turno registrado para ese día y horario. No tenemos clases en ese horario."}
    - Error interno → 500 {"error": "<mensaje>"}

    Salida:
    {"message": "Hay 2 lugares disponibles."}
    o
    {"message": "No hay lugares disponibles."}
    """

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
    """
    POST /verificar_turno_a_partir_de/
    ----------------------------------
    Busca todos los turnos disponibles en uno o varios días, a partir de una hora mínima especificada.

    Concepto:
    - Permite consultar horarios iguales o posteriores a una hora de referencia.
    - Si no se especifica 'dia', busca en todos los días de la semana hábiles.

    Entradas (JSON):
    - hora_minima (str) [obligatorio] Ejemplo: "15:00"
    - dia (str)         [opcional] Ejemplo: "Martes"

    Lógica:
    1. Si se envía 'dia', busca solo en ese día; si no, recorre todos los días Lunes–Sábado.
    2. Para cada día, llama a `buscar_turnos_disponibles(dia_actual, operador_hora="gte", hora_referencia=hora_minima)`.
    3. Devuelve los turnos que tienen lugares disponibles.

    Errores:
    - Falta de parámetros → 400 {"error": "Debes enviar 'hora_minima'"}
    - Sin resultados → {"message": "No hay turnos disponibles después de <hora_minima>."}
    - Error interno → 500 {"error": "<mensaje>"}

    Salida:
    {
    "resultados": [
        {
        "dia": "Martes",
        "hora_minima": "15:00",
        "turnos_disponibles": [
            {"horario": "15:00", "lugares_disponibles": 2},
            {"horario": "16:00", "lugares_disponibles": 1}
        ]
        },
        {
        "dia": "Miércoles",
        "hora_minima": "15:00",
        "turnos_disponibles": [...]
        }
    ]
    }
    """

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
    """
    POST /verificar_turno_antes_de/
    -------------------------------
    Busca los turnos disponibles antes de una hora máxima dentro de un día determinado.

    Concepto:
    - Permite conocer los horarios disponibles previos a una hora límite.

    Entradas (JSON):
    - dia (str)         [obligatorio] Ejemplo: "Miércoles"
    - hora_maxima (str) [obligatorio] Ejemplo: "10:00"

    Lógica:
    1. Busca todos los turnos del día indicado cuya hora sea anterior a la hora máxima.
    2. Usa `buscar_turnos_disponibles(dia, operador_hora="lt", hora_referencia=hora_maxima)`.
    3. Devuelve los turnos con cupos disponibles.

    Errores:
    - Falta de parámetros → 400 {"error": "Debes enviar 'dia' y 'hora_maxima'"}
    - Sin resultados → {"message": "No hay turnos disponibles para <día> antes de <hora_maxima>."}
    - Error interno → 500 {"error": "<mensaje>"}

    Salida:
    {
    "dia": "Miércoles",
    "hora_maxima": "10:00",
    "turnos_disponibles": [
        {"horario": "08:00", "lugares_disponibles": 1},
        {"horario": "09:00", "lugares_disponibles": 3}
    ]
    }
    """

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
    """
    POST /verificar_turno_manana/
    -----------------------------
    Devuelve los turnos con lugares disponibles durante la **mañana** (antes de las 12:00)
    para un día específico.

    Concepto:
    - "Turno" = horario fijo recurrente (ej. Lunes 08:00).
    - Este endpoint filtra todos los turnos de ese día cuya hora sea menor a las 12:00.

    Entradas (JSON):
    - dia (str) [obligatorio] Ejemplo: "Martes"

    Lógica:
    1. Valida que se reciba el campo 'dia'.
    2. Llama a `buscar_turnos_disponibles(dia, operador_hora="lt", hora_referencia="12:00")`.
    3. Si hay turnos con cupos libres, los devuelve con su horario y cantidad de lugares.
    4. Si no hay, devuelve un mensaje indicando que no hay turnos disponibles esa mañana.

    Errores:
    - Falta de parámetros → 400 {"error": "Debes enviar 'dia'"}
    - Sin resultados → {"message": "No hay turnos disponibles para la mañana del <día>."}
    - Error interno → 500 {"error": "<mensaje>"}

    Salida:
    {
    "dia": "Martes",
    "turnos_disponibles_mañana": [
        {"horario": "07:00", "lugares_disponibles": 2},
        {"horario": "08:00", "lugares_disponibles": 1}
    ]
    }
    """

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
    Busca los turnos con lugares disponibles según el día y un criterio horario opcional.

    Esta función se utiliza por varios endpoints (`verificar_turno_a_partir_de`,
    `verificar_turno_antes_de`, `verificar_turno_manana`) para obtener turnos libres
    con distintos filtros de hora.

    Parámetros:
    - dia (str): Día de la semana. Ejemplo: "Martes".
    - operador_hora (str, opcional): Tipo de comparación sobre la hora del turno.
    • 'gte' → mayor o igual que la hora de referencia.
    • 'lt'  → menor que la hora de referencia.
    • 'exact' → igual a la hora de referencia.
    - hora_referencia (str, opcional): Hora de referencia en formato "HH:MM".

    Lógica:
    1. Construye el filtro dinámico (por ejemplo: `horario__lt="12:00"`).
    2. Filtra los turnos (`Turno.objects.filter(...)`) del día indicado.
    3. Calcula los lugares disponibles (4 - lugares_ocupados).
    4. Retorna solo los turnos con cupos > 0.

    Retorna:
    list[dict] → Ejemplo:
    [
    {"horario": "07:00", "lugares_disponibles": 2},
    {"horario": "08:00", "lugares_disponibles": 1}
    ]
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
    """
    POST /verificar_clase_hoy/
    --------------------------
    Verifica si existe una clase programada **para hoy** en un horario determinado
    y devuelve cuántos lugares quedan disponibles.

    Concepto:
    - "Turno" = horario recurrente semanal (ej. Lunes 19:00).
    - "Clase" = la instancia concreta de ese turno para la fecha actual (hoy).

    Entradas (JSON):
    - horario (str) [obligatorio] Ejemplo: "19:00"

    Lógica:
    1. Obtiene la fecha actual (`now().date()`).
    2. Determina el nombre del día actual en español (Lunes–Sábado).
    3. Si hoy es domingo → no hay clases.
    4. Busca el turno correspondiente al día actual y al horario.
    5. Busca la clase asociada a ese turno y la fecha actual.
    6. Cuenta los alumnos regulares (`AlumnoClase`) y ocasionales (`AlumnoClaseOcasional`) de esa clase.
    7. Calcula los lugares disponibles (4 - lugares_ocupados).
    8. Devuelve un mensaje indicando la disponibilidad.

    Errores:
    - Falta 'horario' → 400 {"error": "Debes enviar 'horario'."}
    - Domingo → {"message": "Hoy es domingo y no hay clases."}
    - Turno inexistente → {"message": "No hay turno registrado para hoy a ese horario."}
    - Clase inexistente → {"message": "No hay clase programada hoy a ese horario."}
    - Error interno → 500 {"error": "<mensaje>"}

    Salida:
    {"message": "Hay 2 lugares disponibles para hoy a las 19:00."}
    o
    {"message": "No hay lugares disponibles para hoy a las 19:00."}
    """

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
    """
    POST /actualizar_ruc/
    ---------------------
    Actualiza el número de RUC asociado a una persona ya registrada, identificada principalmente por su teléfono.

    Concepto:
    - Cada persona se identifica primero por su número de teléfono.
    - Si hay más de una persona con el mismo teléfono, se usa nombre y apellido para desambiguar.
    - El RUC se guarda directamente en la tabla `Persona`.

    Entradas (JSON):
    - telefono (str) [obligatorio]
    - ruc (str) [obligatorio]
    - nombre (str) [opcional, requerido si hay duplicados de teléfono]
    - apellido (str) [opcional, requerido si hay duplicados de teléfono]

    Lógica:
    1. Valida que existan los campos `telefono` y `ruc`.
    2. Busca todas las personas con ese número de teléfono.
    3. Si hay más de una coincidencia:
    - Filtra por nombre y apellido exactos (sin mayúsculas/minúsculas ni espacios extra).
    4. Si no encuentra coincidencias o encuentra varias ambiguas, devuelve error.
    5. Si hay una coincidencia válida, actualiza el campo `ruc` de esa persona.

    Errores:
    - Falta de parámetros → 400 {"error": "El teléfono es obligatorio. El nuevo RUC es obligatorio."}
    - Persona no encontrada → 404 {"error": "No se encontró ninguna persona con ese teléfono."}
    - Ambigüedad por duplicados → 400 {"error": "Hay varias personas con ese teléfono, pero ninguna coincide exactamente..."}
    - Error interno → 500 {"error": "<mensaje>"}

    Salida:
    {"message": "RUC actualizado correctamente para Marta Gómez."}
    """

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
    """
    Genera una lista de fechas semanales correspondientes a un turno recurrente.

    Concepto:
    - "Turno" = horario fijo en un día de la semana (ej. Lunes 19:00).
    - Esta función calcula las próximas `n` fechas donde ese turno ocurre,
    comenzando desde una fecha inicial.

    Parámetros:
    - id_turno (int): ID del turno en la base de datos.
    - fecha_inicio (str): Fecha base en formato "YYYY-MM-DD". Si no coincide con el día del turno,
    se ajusta automáticamente al siguiente día correspondiente.
    - n (int): Cantidad de fechas a generar (por ejemplo, 4 clases → 4 fechas).

    Lógica:
    1. Busca el turno correspondiente por `id_turno`.
    2. Determina el índice del día de la semana (Lunes=0, Viernes=4).
    3. Ajusta `fecha_inicio` al próximo día que coincida con el día del turno.
    4. Genera `n` fechas separadas por intervalos de 7 días.
    5. Devuelve las fechas en formato "YYYY-MM-DD".

    Errores:
    - Turno inexistente → {"error": "Turno no encontrado"}
    - Día del turno inválido → {"error": "Día del turno inválido"}

    Salida:
    {
    "fechas": ["2025-11-10", "2025-11-17", "2025-11-24", "2025-12-01"]
    }
    """

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
