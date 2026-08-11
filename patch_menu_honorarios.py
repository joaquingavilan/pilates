import os

file_path = r'C:\Users\jesus\Documents\pilates\Pilapp\templates\admin_panel\base.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """            <li class="nav-item">
                <a class="nav-link {% if request.resolver_match.url_name == 'panel_prospectos' %}active{% endif %}" 
                   href="{% url 'panel_prospectos' %}">
                    <i class="bi bi-person-plus"></i> Prospectos
                </a>
            </li>"""

replacement = """            <li class="nav-item">
                <a class="nav-link {% if request.resolver_match.url_name == 'panel_prospectos' %}active{% endif %}" 
                   href="{% url 'panel_prospectos' %}">
                    <i class="bi bi-person-plus"></i> Prospectos
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link {% if request.resolver_match.url_name == 'panel_honorarios_resumen' %}active{% endif %}" 
                   href="{% url 'panel_honorarios_resumen' %}">
                    <i class="bi bi-journal-check"></i> Honorarios de Profes
                </a>
            </li>"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Menu item added to base.html")
else:
    print("Target not found in base.html")
