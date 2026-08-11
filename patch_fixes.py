import os

# 1. Update inicializacion.py
init_path = r'C:\Users\jesus\Documents\pilates\Pilapp\management\commands\inicializacion.py'
with open(init_path, 'r', encoding='utf-8') as f:
    init_content = f.read()

# Comment out the Turno creation part
init_content = init_content.replace(
    '''        # 2) Turnos
        result_turnos = crear_turnos()
        self.stdout.write(self.style.SUCCESS(f"✓ {result_turnos['mensaje']}"))''',
    '''        # 2) Turnos
        # result_turnos = crear_turnos()
        # self.stdout.write(self.style.SUCCESS(f"✓ {result_turnos['mensaje']}"))'''
)
# Wait, let's use a regex or string replace that is safe against non-utf8 characters like the checkmark
import re
init_content = re.sub(
    r'(# 2\) Turnos\s+result_turnos = crear_turnos\(\)\s+self\.stdout\.write.*?)(\n\s*# 3\) Clases para 30)',
    r'# \1\2',
    init_content,
    flags=re.DOTALL
)

# Actually, just simpler replace:
if 'result_turnos = crear_turnos()' in init_content:
    lines = init_content.split('\n')
    for i, line in enumerate(lines):
        if 'result_turnos = crear_turnos()' in line:
            lines[i] = '        # ' + line.strip()
        if 'self.stdout.write' in line and 'result_turnos' in line:
            lines[i] = '        # ' + line.strip()
    init_content = '\n'.join(lines)

with open(init_path, 'w', encoding='utf-8') as f:
    f.write(init_content)

# 2. Update detalle.html
detalle_path = r'C:\Users\jesus\Documents\pilates\Pilapp\templates\admin_panel\alumnos\detalle.html'
with open(detalle_path, 'r', encoding='utf-8') as f:
    detalle_content = f.read()

detalle_new = """                {% if alumno.id_persona.ruc %}
                <p class="mb-2">
                    <i class="bi bi-building me-2 text-muted"></i>
                    RUC: {{ alumno.id_persona.ruc }}
                </p>
                {% endif %}
                
                {% if alumno.id_persona.razon_social %}
                <p class="mb-2">
                    <i class="bi bi-person-badge me-2 text-muted"></i>
                    Razn Social: {{ alumno.id_persona.razon_social }}
                </p>
                {% endif %}"""

detalle_content = detalle_content.replace(
    """                {% if alumno.id_persona.ruc %}
                <p class="mb-2">
                    <i class="bi bi-building me-2 text-muted"></i>
                    RUC: {{ alumno.id_persona.ruc }}
                </p>
                {% endif %}""",
    detalle_new
)

with open(detalle_path, 'w', encoding='utf-8') as f:
    f.write(detalle_content)

print("Patch applied successfully.")
