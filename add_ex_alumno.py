with open('Pilapp/models.py', 'a', encoding='utf-8') as f:
    f.write('''
class ExAlumno(models.Model):
    """
    Guarda el historial de un alumno que fue eliminado del sistema.
    """
    id_ex_alumno = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    horarios = models.TextField(blank=True, null=True, help_text="Turnos que tenía asignados")
    fecha_baja = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"
''')
print("Model ExAlumno added")
