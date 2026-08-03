import re

with open('Pilapp/urls_panel.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_path = "path('alumnos/', views_panel.panel_alumnos, name='panel_alumnos'),"
new_path = "path('alumnos/', views_panel.panel_alumnos, name='panel_alumnos'),\n    path('ex-alumnos/', views_panel.panel_ex_alumnos, name='panel_ex_alumnos'),"
content = content.replace(old_path, new_path)

with open('Pilapp/urls_panel.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched Pilapp/urls_panel.py successfully.")
