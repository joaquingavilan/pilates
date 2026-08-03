import re

with open('Pilapp/views_panel.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I will replace the entire logic of panel_registrar_pago_alumno
# Need to find the start and end of it.

old_logic = """def panel_registrar_pago_alumno(request, id_alumno):
    alumno = get_object_or_404(Alumno, id_alumno=id_alumno)
    id_alumno_paquete = request.POST.get("id_alumno_paquete")
    if not id_alumno_paquete:
        messages.error(request, "Debes seleccionar un paquete para el pago.")
        return redirect("panel_alumno_detalle", id_alumno=alumno.id_alumno)
        
    alumno_paquete = get_object_or_404(
        AlumnoPaquete,
        id_alumno_paquete=id_alumno_paquete,
        id_alumno=alumno
    )

    monto_raw = (request.POST.get("monto") or "").strip()
    metodo_pago = (request.POST.get("metodo_pago") or "").strip()
    comprobante = (request.POST.get("comprobante") or "").strip()
    observaciones = (request.POST.get("observaciones") or "").strip()

    errores = []

    if not monto_raw:
        errores.append("Debes ingresar un monto.")
    if metodo_pago not in ("efectivo", "tarjeta", "transferencia"):
        errores.append("Debes seleccionar un método de pago válido.")

    try:
        monto = Decimal(monto_raw)
        if monto <= 0:
            errores.append("El monto debe ser mayor que 0.")
    except (InvalidOperation, ValueError):
        errores.append("El monto no tiene un formato válido.")

    if errores:
        # Si no usas messages, puedes devolver un HttpResponse o guardar en session.
        # Por simplicidad, redirigimos al detalle.
        return redirect("panel_alumno_detalle", id_alumno=alumno.id_alumno)

    # Costo del paquete y acumulado anterior
    costo = alumno_paquete.id_paquete.costo or Decimal("0")

    total_pagado_antes = (
        PagoAlumno.objects
        .filter(id_alumno_paquete=alumno_paquete, id_pago__estado__in=["pagado", "parcial"])
        .aggregate(total=Sum("id_pago__monto"))
        .get("total") or Decimal("0")
    )

    restante_antes = max(Decimal("0"), costo - total_pagado_antes)

    # Estado del pago creado (según lo que faltaba en ese momento)
    estado_pago_creado = "pagado" if monto >= restante_antes else "parcial"

    nro_pago = f"APQ-{alumno_paquete.id_alumno_paquete}-{timezone.now().strftime('%Y%m%d-%H%M%S')}"

    pago = Pago.objects.create(
        fecha=timezone.localdate(),
        monto=monto,
        metodo_pago=metodo_pago,
        comprobante=comprobante,
        estado=estado_pago_creado,
        nro_pago=nro_pago,
    )

    PagoAlumno.objects.create(
        id_pago=pago,
        id_alumno_paquete=alumno_paquete,
        observaciones=observaciones
    )

    # Volvemos a calcular el total pagado (incluyendo el actual)
    total_nuevo = (
        PagoAlumno.objects
        .filter(id_alumno_paquete=alumno_paquete, id_pago__estado__in=["pagado", "parcial"])
        .aggregate(total=Sum("id_pago__monto"))
        .get("total") or Decimal("0")
    )

    # Actualizar estado de pago del paquete
    if total_nuevo >= costo:
        alumno_paquete.estado_pago = "pagado"
    else:
        alumno_paquete.estado_pago = "parcial"
        
    alumno_paquete.save()

    return redirect("panel_alumno_detalle", id_alumno=alumno.id_alumno)"""

new_logic = """def panel_registrar_pago_alumno(request, id_alumno):
    alumno = get_object_or_404(Alumno, id_alumno=id_alumno)
    id_alumno_paquete = request.POST.get("id_alumno_paquete")
    
    if id_alumno_paquete:
        alumno_paquete = get_object_or_404(
            AlumnoPaquete,
            id_alumno_paquete=id_alumno_paquete,
            id_alumno=alumno
        )
    else:
        alumno_paquete = None

    monto_raw = (request.POST.get("monto") or "").strip()
    metodo_pago = (request.POST.get("metodo_pago") or "").strip()
    comprobante = (request.POST.get("comprobante") or "").strip()
    observaciones = (request.POST.get("observaciones") or "").strip()

    errores = []

    if not monto_raw:
        errores.append("Debes ingresar un monto.")
    if metodo_pago not in ("efectivo", "tarjeta", "transferencia"):
        errores.append("Debes seleccionar un m\\u00e9todo de pago v\\u00e1lido.")

    try:
        monto = Decimal(monto_raw)
        if monto <= 0:
            errores.append("El monto debe ser mayor que 0.")
    except (InvalidOperation, ValueError):
        errores.append("El monto no tiene un formato v\\u00e1lido.")

    if errores:
        for error in errores:
            messages.error(request, error)
        return redirect("panel_alumno_detalle", id_alumno=alumno.id_alumno)

    if alumno_paquete:
        # Costo del paquete y acumulado anterior
        costo = alumno_paquete.id_paquete.costo or Decimal("0")

        total_pagado_antes = (
            PagoAlumno.objects
            .filter(id_alumno_paquete=alumno_paquete, id_pago__estado__in=["pagado", "parcial"])
            .aggregate(total=Sum("id_pago__monto"))
            .get("total") or Decimal("0")
        )

        restante_antes = max(Decimal("0"), costo - total_pagado_antes)

        # Estado del pago creado (seg\\u00fan lo que faltaba en ese momento)
        estado_pago_creado = "pagado" if monto >= restante_antes else "parcial"
        nro_pago = f"APQ-{alumno_paquete.id_alumno_paquete}-{timezone.now().strftime('%Y%m%d-%H%M%S')}"
    else:
        estado_pago_creado = "pagado"
        nro_pago = f"ADV-{alumno.id_alumno}-{timezone.now().strftime('%Y%m%d-%H%M%S')}"

    pago = Pago.objects.create(
        fecha=timezone.localdate(),
        monto=monto,
        metodo_pago=metodo_pago,
        comprobante=comprobante,
        estado=estado_pago_creado,
        nro_pago=nro_pago,
    )

    PagoAlumno.objects.create(
        id_pago=pago,
        id_alumno=alumno,
        id_alumno_paquete=alumno_paquete,
        observaciones=observaciones
    )

    if alumno_paquete:
        # Volvemos a calcular el total pagado (incluyendo el actual)
        total_nuevo = (
            PagoAlumno.objects
            .filter(id_alumno_paquete=alumno_paquete, id_pago__estado__in=["pagado", "parcial"])
            .aggregate(total=Sum("id_pago__monto"))
            .get("total") or Decimal("0")
        )

        # Actualizar estado de pago del paquete
        if total_nuevo >= costo:
            alumno_paquete.estado_pago = "pagado"
        else:
            alumno_paquete.estado_pago = "parcial"
            
        alumno_paquete.save()
    
    messages.success(request, "Pago registrado correctamente.")
    return redirect("panel_alumno_detalle", id_alumno=alumno.id_alumno)"""

# In case encoding issues prevent simple replace, we use a regex search for the function signature
start_str = "def panel_registrar_pago_alumno(request, id_alumno):"
end_str = "return redirect(\"panel_alumno_detalle\", id_alumno=alumno.id_alumno)"

start_idx = content.find(start_str)
end_idx = content.find(end_str, start_idx) + len(end_str)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_logic + content[end_idx:]
    with open('Pilapp/views_panel.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched panel_registrar_pago_alumno successfully.")
else:
    print("Could not find the function to patch.")
