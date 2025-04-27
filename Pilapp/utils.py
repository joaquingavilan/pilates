from datetime import datetime, date, timedelta
from django.utils.timezone import make_aware
from Pilapp.models import Turno, Clase, Instructor, HorarioDisponible

def crear_turnos():
    """
    Crea turnos a partir de los horarios disponibles en la tabla HorarioDisponible.
    """
    turnos_creados = 0
    turnos_existentes = 0

    horarios = HorarioDisponible.objects.all()

    for horario_disponible in horarios:
        dia = horario_disponible.dia
        horario = horario_disponible.horario

        turno_existente = Turno.objects.filter(dia=dia, horario=horario).exists()

        if not turno_existente:
            Turno.objects.create(
                dia=dia,
                horario=horario,
                estado='Libre',
                lugares_ocupados=0
            )
            turnos_creados += 1
        else:
            turnos_existentes += 1

    return {
        'creados': turnos_creados,
        'existentes': turnos_existentes,
        'mensaje': f'Se crearon {turnos_creados} turnos nuevos. {turnos_existentes} turnos ya existían.'
    }


def crear_clases_para_fecha(fecha=None):
    """
    Crea clases para todos los turnos correspondientes al día de la semana de la fecha proporcionada.
    Si no se proporciona una fecha, se utiliza la fecha actual.
    Todas las clases se asocian con la instructora que tiene id_instructor=1.
    
    Args:
        fecha (date, optional): Fecha para la cual crear las clases. Por defecto es la fecha actual.
    
    Returns:
        dict: Un diccionario con información sobre la operación realizada.
              - 'creadas': Número de clases creadas.
              - 'existentes': Número de clases que ya existían.
              - 'mensaje': Mensaje descriptivo del resultado.
              - 'dia_semana': Día de la semana para el que se crearon las clases.
    """
    # Si no se proporciona fecha, usar la fecha actual
    if fecha is None:
        fecha = date.today()
    
    # Mapeo de índice de día de la semana (0=lunes, 6=domingo) a nombre del día
    dias_semana = {
        0: "Lunes",
        1: "Martes",
        2: "Miércoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sábado",
        6: "Domingo"
    }
    
    # Obtener el día de la semana de la fecha proporcionada
    dia_semana_idx = fecha.weekday()
    dia_semana = dias_semana.get(dia_semana_idx)
    
    # Si es domingo, no hay clases
    if dia_semana_idx > 5:
        return {
            'creadas': 0,
            'existentes': 0,
            'mensaje': f'No se crean clases para {dia_semana} ({fecha.strftime("%d/%m/%Y")})',
            'dia_semana': dia_semana
        }
    
    # Obtener la instructora con id=1
    try:
        instructora = Instructor.objects.get(id_instructor=1)
    except Instructor.DoesNotExist:
        return {
            'error': 'No se encontró la instructora con id=1',
            'creadas': 0,
            'existentes': 0,
            'dia_semana': dia_semana
        }
    
    # Obtener todos los turnos para el día de la semana
    turnos = Turno.objects.filter(dia=dia_semana)
    
    clases_creadas = 0
    clases_existentes = 0
    
    # Para cada turno, crear una clase si no existe
    for turno in turnos:
        # Verificar si ya existe una clase para este turno y fecha
        clase_existente = Clase.objects.filter(
            id_turno=turno,
            fecha=fecha
        ).exists()
        
        if not clase_existente:
            # Crear la clase
            Clase.objects.create(
                id_instructor=instructora,
                id_turno=turno,
                fecha=fecha
            )
            clases_creadas += 1
        else:
            clases_existentes += 1
    
    resultado = {
        'creadas': clases_creadas,
        'existentes': clases_existentes,
        'mensaje': f'Se crearon {clases_creadas} clases para {dia_semana} ({fecha.strftime("%d/%m/%Y")}). {clases_existentes} clases ya existían.',
        'dia_semana': dia_semana
    }
    
    return resultado


def crear_clases_rango_fechas(fecha_inicio, fecha_fin):
    """
    Crea clases para todas las fechas en un rango especificado.
    
    Args:
        fecha_inicio (str o date): Fecha de inicio del rango en formato 'YYYY-MM-DD' o como objeto date.
        fecha_fin (str o date): Fecha de fin del rango en formato 'YYYY-MM-DD' o como objeto date.
    
    Returns:
        dict: Un diccionario con información sobre la operación realizada.
              - 'total_creadas': Número total de clases creadas.
              - 'total_existentes': Número total de clases que ya existían.
              - 'dias_procesados': Número de días procesados.
              - 'dias_con_clases': Número de días en los que se crearon clases (excluyendo domingos).
              - 'mensaje': Mensaje descriptivo del resultado.
              - 'resultados_por_dia': Lista de resultados detallados por día.
    """
    # Convertir fechas a objetos date si son strings
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    
    # Validar que fecha_inicio sea anterior o igual a fecha_fin
    if fecha_inicio > fecha_fin:
        return {
            'error': 'La fecha de inicio debe ser anterior o igual a la fecha de fin',
            'total_creadas': 0,
            'total_existentes': 0,
            'dias_procesados': 0,
            'dias_con_clases': 0
        }
    
    total_creadas = 0
    total_existentes = 0
    dias_procesados = 0
    dias_con_clases = 0
    resultados_por_dia = []
    
    # Iterar por cada fecha en el rango
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        # Crear clases para la fecha actual
        resultado_dia = crear_clases_para_fecha(fecha=fecha_actual)
        resultados_por_dia.append(resultado_dia)
        
        # Actualizar contadores
        dias_procesados += 1
        
        # Solo contar días con clases (lunes a sábado)
        if fecha_actual.weekday() <= 5:  # 0=lunes, 5=sábado
            dias_con_clases += 1
            total_creadas += resultado_dia.get('creadas', 0)
            total_existentes += resultado_dia.get('existentes', 0)
        
        # Avanzar al siguiente día
        fecha_actual += timedelta(days=1)
    
    # Preparar resultado final
    resultado = {
        'total_creadas': total_creadas,
        'total_existentes': total_existentes,
        'dias_procesados': dias_procesados,
        'dias_con_clases': dias_con_clases,
        'mensaje': f'Se procesaron {dias_procesados} días ({dias_con_clases} días hábiles). Se crearon {total_creadas} clases nuevas. {total_existentes} clases ya existían.',
        'resultados_por_dia': resultados_por_dia
    }
    
    return resultado



