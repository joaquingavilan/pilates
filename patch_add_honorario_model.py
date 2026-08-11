import os

models_path = r'C:\Users\jesus\Documents\pilates\Pilapp\models.py'
with open(models_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_model = """

class HonorarioInstructor(models.Model):
    \"\"\"
    Registra el pago u honorario de una instructora por turno/día.
    \"\"\"
    TURNO_CHOICES = [
        ('Mañana', 'Mañana'),
        ('Tarde', 'Tarde'),
        ('Otro', 'Otro')
    ]
    
    id_honorario = models.AutoField(primary_key=True)
    id_instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    fecha = models.DateField()
    turno = models.CharField(max_length=10, choices=TURNO_CHOICES)
    cantidad_clases = models.IntegerField(default=1)
    monto_total = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    observacion = models.CharField(max_length=255, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id_instructor.id_persona.nombre} - {self.fecha} ({self.turno}) - {self.monto_total}"
"""

if "class HonorarioInstructor" not in content:
    with open(models_path, 'a', encoding='utf-8') as f:
        f.write(new_model)
    print("Modelo HonorarioInstructor agregado a models.py")
else:
    print("El modelo ya existía en models.py")
