import os

file_path = r'C:\Users\jesus\Documents\pilates\Pilapp\urls_panel.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = "path('profes/<str:token>/pagos/registrar/', views_panel.profes_registrar_pago, name='profes_registrar_pago'),"
replacement1 = """path('profes/<str:token>/pagos/registrar/', views_panel.profes_registrar_pago, name='profes_registrar_pago'),
    path('profes/<str:token>/honorarios/registrar/', views_panel.profes_registrar_honorario, name='profes_registrar_honorario'),"""

target2 = "path('resumen-pagos/', views_panel.panel_resumen_pagos, name='panel_resumen_pagos'),"
replacement2 = """path('resumen-pagos/', views_panel.panel_resumen_pagos, name='panel_resumen_pagos'),
    path('honorarios/resumen/', views_panel.panel_honorarios_resumen, name='panel_honorarios_resumen'),"""

if target1 in content and target2 in content:
    content = content.replace(target1, replacement1)
    content = content.replace(target2, replacement2)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Routes added to urls_panel.py")
else:
    print("Targets not found in urls_panel.py")
