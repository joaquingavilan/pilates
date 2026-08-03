import re

with open('Pilapp/templates/admin_panel/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_link = """            <li class="nav-item">
                <a class="nav-link {% if 'alumno' in request.resolver_match.url_name %}active{% endif %}" 
                   href="{% url 'panel_alumnos' %}">
                    <i class="bi bi-people"></i> Alumnos
                </a>
            </li>"""
            
new_link = """            <li class="nav-item">
                <a class="nav-link {% if 'alumno' in request.resolver_match.url_name and 'ex_alumno' not in request.resolver_match.url_name %}active{% endif %}" 
                   href="{% url 'panel_alumnos' %}">
                    <i class="bi bi-people"></i> Alumnos
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link {% if 'ex_alumno' in request.resolver_match.url_name %}active{% endif %}" 
                   href="{% url 'panel_ex_alumnos' %}">
                    <i class="bi bi-archive"></i> Ex-Alumnos
                </a>
            </li>"""
            
content = content.replace(old_link, new_link)

with open('Pilapp/templates/admin_panel/base.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched base.html successfully.")
