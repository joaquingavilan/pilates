import re

with open('Pilapp/templates/admin_panel/alumnos/detalle.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add "Saldo a favor" badge
old_info = """                <h4 class="mb-3">{{ alumno.id_persona.nombre }} {{ alumno.id_persona.apellido }}</h4>"""
new_info = """                <h4 class="mb-2">{{ alumno.id_persona.nombre }} {{ alumno.id_persona.apellido }}</h4>
                {% if saldo_favor and saldo_favor > 0 %}
                <div class="mb-3">
                    <span class="badge bg-success" style="font-size: 0.9rem;">
                        <i class="bi bi-wallet2 me-1"></i> Saldo a favor: $ {{ saldo_favor|floatformat:0|intcomma }}
                    </span>
                </div>
                {% endif %}"""

content = content.replace(old_info, new_info)

# 2. Update modal "Registrar pago" select
old_select = """            <select name="id_alumno_paquete" id="pago_id_alumno_paquete" class="form-select" required>
              <option value="">Selecciona un paquete...</option>"""

new_select = """            <select name="id_alumno_paquete" id="pago_id_alumno_paquete" class="form-select">
              <option value="">(Ninguno - Dejar como Saldo a Favor / Adelanto)</option>"""

content = content.replace(old_select, new_select)

with open('Pilapp/templates/admin_panel/alumnos/detalle.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched detalle.html successfully.")
