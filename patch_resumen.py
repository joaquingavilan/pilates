import re

with open('Pilapp/templates/admin_panel/pagos/resumen.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_str = """                                      {% for pa in pago.pagoalumno_set.all %}
                                          <strong>{{ pa.id_alumno_paquete.id_alumno.id_persona.nombre }} {{ pa.id_alumno_paquete.id_alumno.id_persona.apellido }}</strong> - """

new_str = """                                      {% for pa in pago.pagoalumno_set.all %}
                                          <strong>
                                            {% if pa.id_alumno %}
                                                {{ pa.id_alumno.id_persona.nombre }} {{ pa.id_alumno.id_persona.apellido }}
                                            {% else %}
                                                {{ pa.id_alumno_paquete.id_alumno.id_persona.nombre }} {{ pa.id_alumno_paquete.id_alumno.id_persona.apellido }}
                                            {% endif %}
                                          </strong> 
                                          {% if not pa.id_alumno_paquete %}
                                            <span class="badge bg-warning text-dark ms-1" style="font-size: 0.7rem;">Saldo a favor</span>
                                          {% endif %}
                                          - """

content = content.replace(old_str, new_str)

old_ruc = """                                          {% if pa.id_alumno_paquete.id_alumno.id_persona.ruc or pa.id_alumno_paquete.id_alumno.id_persona.razon_social %}
                                          <span class="d-block text-black-50 mt-1" style="font-size: 0.8rem;">
                                              <i class="bi bi-receipt me-1"></i>
                                              {{ pa.id_alumno_paquete.id_alumno.id_persona.razon_social|default:"Sin razn social" }} 
                                              (RUC: {{ pa.id_alumno_paquete.id_alumno.id_persona.ruc|default:"N/A" }})
                                          </span>
                                          {% endif %}"""
# Since old_ruc has encoding for 'Sin razón social', we will use a more robust regex or string matching.

import builtins
builtins.content = content
