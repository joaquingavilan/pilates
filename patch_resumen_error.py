import os

path = r'C:\Users\jesus\Documents\pilates\Pilapp\templates\admin_panel\pagos\resumen.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = """                                        {% with persona=pa.id_alumno.id_persona|default:pa.id_alumno_paquete.id_alumno.id_persona %}
                                        {% if persona.ruc or persona.razon_social %}
                                        <br>
                                        <span class="text-primary" style="font-size: 0.8rem;">
                                            <i class="bi bi-receipt"></i> 
                                            Facturar a: {{ persona.razon_social|default:"(Sin Razón Social)" }} - RUC: {{ persona.ruc|default:"(Sin RUC)" }}
                                        </span>
                                        {% endif %}
                                        {% endwith %}"""

new_logic = """                                        {% if pa.id_alumno and pa.id_alumno.id_persona %}
                                            {% if pa.id_alumno.id_persona.ruc or pa.id_alumno.id_persona.razon_social %}
                                            <br>
                                            <span class="text-primary" style="font-size: 0.8rem;">
                                                <i class="bi bi-receipt"></i> 
                                                Facturar a: {{ pa.id_alumno.id_persona.razon_social|default:"(Sin Razón Social)" }} - RUC: {{ pa.id_alumno.id_persona.ruc|default:"(Sin RUC)" }}
                                            </span>
                                            {% endif %}
                                        {% elif pa.id_alumno_paquete and pa.id_alumno_paquete.id_alumno and pa.id_alumno_paquete.id_alumno.id_persona %}
                                            {% if pa.id_alumno_paquete.id_alumno.id_persona.ruc or pa.id_alumno_paquete.id_alumno.id_persona.razon_social %}
                                            <br>
                                            <span class="text-primary" style="font-size: 0.8rem;">
                                                <i class="bi bi-receipt"></i> 
                                                Facturar a: {{ pa.id_alumno_paquete.id_alumno.id_persona.razon_social|default:"(Sin Razón Social)" }} - RUC: {{ pa.id_alumno_paquete.id_alumno.id_persona.ruc|default:"(Sin RUC)" }}
                                            </span>
                                            {% endif %}
                                        {% endif %}"""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patch applied to resumen.html")
else:
    print("Could not find old logic in resumen.html")
