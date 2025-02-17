from django.contrib import admin
from .models import *

admin.site.register(Persona)
admin.site.register(Alumno)
admin.site.register(Instructor)
admin.site.register(Turno)
admin.site.register(Clase)
admin.site.register(Paquete)
admin.site.register(AlumnoPaquete)
admin.site.register(AlumnoClase)
admin.site.register(Pago)
admin.site.register(PagoAlumno)
admin.site.register(PagoInstructor)
admin.site.register(FacturaPago)
admin.site.register(AlumnoPaqueteTurno)
