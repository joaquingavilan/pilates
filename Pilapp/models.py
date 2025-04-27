from django.db import models

class HorarioDisponible(models.Model):
    DIAS_CHOICES = [
        ('Lunes', 'Lunes'),
        ('Martes', 'Martes'),
        ('Miércoles', 'Miércoles'),
        ('Jueves', 'Jueves'),
        ('Viernes', 'Viernes'),
        ('Sábado', 'Sábado'),
    ]

    dia = models.CharField(max_length=10, choices=DIAS_CHOICES)
    horario = models.TimeField()

    def __str__(self):
        return f"{self.dia} {self.horario.strftime('%H:%M')}"


class Persona(models.Model):
    id_persona = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    ruc = models.CharField(max_length=20, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class Alumno(models.Model):
    id_alumno = models.AutoField(primary_key=True)
    id_persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    canal_captacion = models.CharField(max_length=100, blank=True, null=True)
    ultima_clase = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Alumno: {self.id_persona}"

class Instructor(models.Model):
    id_instructor = models.AutoField(primary_key=True)
    id_persona = models.ForeignKey(Persona, on_delete=models.CASCADE)

    def __str__(self):
        return f"Instructor: {self.id_persona}"

class Turno(models.Model):
    DIAS_CHOICES = [
        ('Lunes', 'Lunes'),
        ('Martes', 'Martes'),
        ('Miércoles', 'Miércoles'),
        ('Jueves', 'Jueves'),
        ('Viernes', 'Viernes'),
        ('Sábado', 'Sábado'),
    ]

    ESTADO_CHOICES = [
        ('Libre', 'Libre'),
        ('Ocupado', 'Ocupado'),
    ]

    id_turno = models.AutoField(primary_key=True)
    horario = models.TimeField()
    dia = models.CharField(max_length=10, choices=DIAS_CHOICES)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Libre')  # Nuevo campo
    lugares_ocupados = models.IntegerField(default=0)
    def __str__(self):
        return f"{self.dia} - {self.horario.strftime('%H:%M')}"  # ejemplo: "Martes - 15:00"


class Clase(models.Model):
    id_clase = models.AutoField(primary_key=True)
    id_instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    id_turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
    fecha = models.DateField()

    def __str__(self):
        return f"Clase {self.id_clase} - {self.fecha}"

class Paquete(models.Model):
    id_paquete = models.AutoField(primary_key=True)
    cantidad_clases = models.IntegerField()
    costo = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Paquete {self.id_paquete} - {self.cantidad_clases} clases"

class AlumnoPaquete(models.Model):
    id_alumno_paquete = models.AutoField(primary_key=True)
    id_alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    id_paquete = models.ForeignKey(Paquete, on_delete=models.CASCADE)
    estado = models.CharField(max_length=50, choices=[("activo", "Activo"), ("expirado", "Expirado")])
    fecha_inicio = models.DateField(null=True)

    def __str__(self):
        return f"AlumnoPaquete {self.id_alumno_paquete}"


# models.py
class AlumnoPaqueteTurno(models.Model):
    id_alumno_paquete_turno = models.AutoField(primary_key=True)
    id_alumno_paquete = models.ForeignKey(AlumnoPaquete, on_delete=models.CASCADE)
    id_turno = models.ForeignKey(Turno, on_delete=models.CASCADE)

    def __str__(self):
        return f"AlumnoPaqueteTurno {self.id_alumno_paquete_turno}"

class AlumnoClase(models.Model):
    id_alumno_clase = models.AutoField(primary_key=True)
    id_alumno_paquete = models.ForeignKey(AlumnoPaquete, on_delete=models.CASCADE)
    id_clase = models.ForeignKey(Clase, on_delete=models.CASCADE)
    estado = models.CharField(max_length=50, choices=[("asistió", "Asistió"), ("faltó", "Faltó"), ("canceló", "Canceló"), ("recuperó", "Recuperó"), ("reprogramó","Reprogramó"), ("pendiente", "Pendiente")])

    def __str__(self):
        return f"AlumnoClase {self.id_alumno_clase}"

class Pago(models.Model):
    id_pago = models.AutoField(primary_key=True)
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    nro_pago = models.CharField(max_length=50)
    estado = models.CharField(max_length=50, choices=[("pendiente", "Pendiente"), ("confirmado", "Confirmado"), ("rechazado", "Rechazado")])
    id_factura = models.ForeignKey("FacturaPago", on_delete=models.SET_NULL, blank=True, null=True)
    metodo_pago = models.CharField(max_length=50, choices=[("efectivo", "Efectivo"), ("tarjeta", "Tarjeta"), ("transferencia", "Transferencia")])
    comprobante = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Pago {self.id_pago}"

class PagoAlumno(models.Model):
    id_pago_alumno = models.AutoField(primary_key=True)
    id_pago = models.ForeignKey(Pago, on_delete=models.CASCADE)
    id_alumno_paquete = models.ForeignKey(AlumnoPaquete, on_delete=models.CASCADE)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"PagoAlumno {self.id_pago_alumno}"

class PagoInstructor(models.Model):
    id_pago_instructor = models.AutoField(primary_key=True)
    id_pago = models.ForeignKey(Pago, on_delete=models.CASCADE)
    id_instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)

    def __str__(self):
        return f"PagoInstructor {self.id_pago_instructor}"

class FacturaPago(models.Model):
    id_factura = models.AutoField(primary_key=True)
    id_pago = models.ForeignKey(Pago, on_delete=models.CASCADE)
    fecha = models.DateField()
    identificador = models.CharField(max_length=100)
    razon_social = models.CharField(max_length=255)
    ruc = models.CharField(max_length=50)

    def __str__(self):
        return f"Factura {self.id_factura}"

class Conversacion(models.Model):
    estado = models.CharField(max_length=50, default="MenuPrincipal")  # Estado actual del flujo
    paso = models.IntegerField(default=0)  # Paso en el proceso de registro
    datos = models.JSONField(default=dict)  # Datos recolectados

    def __str__(self):
        return f"Conversación {self.estado} - Paso {self.paso}"
