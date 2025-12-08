from django import template

register = template.Library()


@register.filter
def get_clase(calendario, fecha):
    """Obtiene las clases de una fecha específica del calendario."""
    return calendario.get(str(fecha), {})


@register.filter
def get_horario(clases_dia, horario):
    """Obtiene la clase de un horario específico."""
    return clases_dia.get(str(horario), None)