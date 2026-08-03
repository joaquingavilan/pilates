import re

with open('Pilapp/templates/admin_panel/alumnos/detalle.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_html = """            <select name="id_alumno_paquete" id="pago_id_alumno_paquete" class="form-select" required>
              <option value="">Selecciona un paquete...</option>
              {% for paquete in paquetes %}
              <option value="{{ paquete.id_alumno_paquete }}">{{ paquete.id_paquete.nombre }} ({{ paquete.estado_pago|title }})</option>
              {% endfor %}
            </select>"""

new_html = """            <select name="id_alumno_paquete" id="pago_id_alumno_paquete" class="form-select" required>
              <option value="">Selecciona un paquete...</option>
              {% for paquete in paquetes %}
              <option value="{{ paquete.id_alumno_paquete }}">
                Paquete {{ paquete.id_paquete.cantidad_clases }} clases - 
                Inicio: {{ paquete.fecha_inicio|date:"d/m/Y"|default:"Pendiente" }} - 
                Usadas: {{ paquete.clases_usadas }}/{{ paquete.id_paquete.cantidad_clases }} 
                ({{ paquete.estado_pago|title }})
              </option>
              {% endfor %}
            </select>"""

content = content.replace(old_html, new_html)

with open('Pilapp/templates/admin_panel/alumnos/detalle.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched detalle.html successfully.")
