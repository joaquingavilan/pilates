import re

with open('Pilapp/templates/admin_panel/clases/detalle.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_html = """                                    <a href="{% url 'panel_alumno_detalle' ac.id_alumno_paquete.id_alumno.id_alumno %}">
                                        {{ ac.id_alumno_paquete.id_alumno.id_persona.nombre }} 
                                        {{ ac.id_alumno_paquete.id_alumno.id_persona.apellido }}
                                    </a>"""

new_html = """                                    <a href="{% url 'panel_alumno_detalle' ac.id_alumno_paquete.id_alumno.id_alumno %}">
                                        {{ ac.id_alumno_paquete.id_alumno.id_persona.nombre }} 
                                        {{ ac.id_alumno_paquete.id_alumno.id_persona.apellido }}
                                    </a>
                                    {% if ac.es_nuevo %}
                                    <span class="badge bg-warning text-dark ms-2" title="Primera clase del primer paquete"><i class="bi bi-star-fill"></i> Nuevo</span>
                                    {% endif %}"""

content = content.replace(old_html, new_html)

with open('Pilapp/templates/admin_panel/clases/detalle.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched detalle.html successfully.")
