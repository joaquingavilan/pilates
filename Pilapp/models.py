from django.db import models

# Modelo Alumno
class Alumno(models.Model):
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    fecha_nacimiento = models.DateField()
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

# Modelo Paquete
class Paquete(models.Model):
    cantidad_clases = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Paquete {self.cantidad_clases} clases - {self.precio} guaraníes."

# Modelo AlumnoPaquete
class AlumnoPaquete(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="paquetes")
    paquete = models.ForeignKey(Paquete, on_delete=models.CASCADE, related_name="alumnos")
    fecha_inicio = models.DateField()
    fecha_pago = models.DateField()
    FORMA_PAGO_CHOICES = [
        ('EF', 'Efectivo'),
        ('TF', 'Transferencia'),
        ('TD', 'Tarjeta de Débito'),
        ('OT', 'Otros'),
    ]
    forma_pago = models.CharField(max_length=2, choices=FORMA_PAGO_CHOICES)

    def __str__(self):
        return f"{self.alumno} - {self.paquete} ({self.forma_pago})"
