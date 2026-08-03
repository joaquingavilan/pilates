import re

with open('Pilapp/templates/admin_panel/pagos/resumen.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the name display
content = re.sub(
    r'\{\{ pa\.id_alumno_paquete\.id_alumno\.id_persona\.nombre \}\} \{\{ pa\.id_alumno_paquete\.id_alumno\.id_persona\.apellido \}\}',
    r'{% if pa.id_alumno %}{{ pa.id_alumno.id_persona.nombre }} {{ pa.id_alumno.id_persona.apellido }}{% else %}{{ pa.id_alumno_paquete.id_alumno.id_persona.nombre }} {{ pa.id_alumno_paquete.id_alumno.id_persona.apellido }}{% endif %}',
    content
)

# Add badge for Saldo a Favor
content = content.replace(
    r'{% if pa.observaciones %}',
    r'{% if not pa.id_alumno_paquete %}<span class="badge bg-warning text-dark ms-1" style="font-size: 0.7rem;">Adelanto</span>{% endif %} {% if pa.observaciones %}'
)

# Replace the ruc checks
content = content.replace(
    r'pa.id_alumno_paquete.id_alumno.id_persona.ruc',
    r'pa.id_alumno.id_persona.ruc'
).replace(
    r'pa.id_alumno_paquete.id_alumno.id_persona.razon_social',
    r'pa.id_alumno.id_persona.razon_social'
)

with open('Pilapp/templates/admin_panel/pagos/resumen.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched resumen.html successfully.")
