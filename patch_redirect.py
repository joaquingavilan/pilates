import os

views_path = r'C:\Users\jesus\Documents\pilates\Pilapp\views_panel.py'
with open(views_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = 'url = redirect("profes_clases_hoy", token=token)'
replacement = 'url = redirect("profes_honorarios", token=token)'
if target in content:
    content = content.replace(target, replacement)
    
with open(views_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed redirect")
