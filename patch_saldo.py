import re

with open('Pilapp/views_panel.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_ctx = """    context = {
        "alumno": alumno,
        "paquetes": paquetes,
        "pagos": pagos,
        "clases": todas_las_clases,
        "lista_paquetes": lista_paquetes,
        
        # Nuevas variables pasadas al template
        "ultimo_paquete_id": ultimo_paquete_id,
        "total_pagado_ultimo": total_pagado_ultimo,
        "restante_ultimo": restante_ultimo,
        
        # Para el calendario opcional
        "eventos_calendario": json.dumps(eventos_calendario, cls=DjangoJSONEncoder)
    }"""

new_ctx = """    # Calcular saldo a favor (pagos sin asignar)
    saldo_favor = PagoAlumno.objects.filter(
        id_alumno=alumno,
        id_alumno_paquete__isnull=True,
        id_pago__estado__in=["pagado", "parcial"]
    ).aggregate(total=Sum("id_pago__monto")).get("total") or Decimal("0")

    context = {
        "alumno": alumno,
        "paquetes": paquetes,
        "pagos": pagos,
        "clases": todas_las_clases,
        "lista_paquetes": lista_paquetes,
        "saldo_favor": saldo_favor,
        
        # Nuevas variables pasadas al template
        "ultimo_paquete_id": ultimo_paquete_id,
        "total_pagado_ultimo": total_pagado_ultimo,
        "restante_ultimo": restante_ultimo,
        
        # Para el calendario opcional
        "eventos_calendario": json.dumps(eventos_calendario, cls=DjangoJSONEncoder)
    }"""

content = content.replace(old_ctx, new_ctx)

with open('Pilapp/views_panel.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched panel_alumno_detalle successfully.")
