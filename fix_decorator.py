import re

with open('Pilapp/views_panel.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove @admin_required
old = "@admin_required\ndef panel_ex_alumnos(request):"
new = "def panel_ex_alumnos(request):"

content = content.replace(old, new)

with open('Pilapp/views_panel.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Removed @admin_required from panel_ex_alumnos")
