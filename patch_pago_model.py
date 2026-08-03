import re

with open('Pilapp/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_pago = """class PagoAlumno(models.Model):
    \"\"\"
    Relaciona un pago con el paquete de un alumno.

    Campos:
        id_pago_alumno (PK)
        id_pago (FK Pago)
        id_alumno_paquete (FK)
        observaciones (texto opcional)
    \"\"\"
    id_pago_alumno = models.AutoField(primary_key=True)
    id_pago = models.ForeignKey(Pago, on_delete=models.CASCADE)
    id_alumno_paquete = models.ForeignKey(AlumnoPaquete, on_delete=models.CASCADE)
    observaciones = models.TextField(blank=True, null=True)"""

new_pago = """class PagoAlumno(models.Model):
    \"\"\"
    Relaciona un pago con el paquete de un alumno.

    Campos:
        id_pago_alumno (PK)
        id_pago (FK Pago)
        id_alumno (FK Alumno)
        id_alumno_paquete (FK) (Opcional, si es saldo a favor)
        observaciones (texto opcional)
    \"\"\"
    id_pago_alumno = models.AutoField(primary_key=True)
    id_pago = models.ForeignKey(Pago, on_delete=models.CASCADE)
    id_alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, null=True, blank=True)
    id_alumno_paquete = models.ForeignKey(AlumnoPaquete, on_delete=models.SET_NULL, null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)"""

content = content.replace(old_pago, new_pago)

with open('Pilapp/models.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched models.py successfully.")
