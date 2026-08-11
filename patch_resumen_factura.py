import os
import re

path = r'C:\Users\jesus\Documents\pilates\Pilapp\templates\admin_panel\pagos\resumen.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r'{%\s*if\s+pa\.id_alumno\.id_persona\.ruc\s+or\s+pa\.id_alumno\.id_persona\.razon_social\s*%}.*?{%\s*endif\s*%}'

new_logic = """{% with persona=pa.id_alumno.id_persona|default:pa.id_alumno_paquete.id_alumno.id_persona %}
                                        {% if persona.ruc or persona.razon_social %}
                                        <br>
                                        <span class="text-primary" style="font-size: 0.8rem;">
                                            <i class="bi bi-receipt"></i> 
                                            Facturar a: {{ persona.razon_social|default:"(Sin Razón Social)" }} - RUC: {{ persona.ruc|default:"(Sin RUC)" }}
                                        </span>
                                        {% endif %}
                                        {% endwith %}"""

content = re.sub(pattern, new_logic, content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Regex patch applied to resumen.html")
