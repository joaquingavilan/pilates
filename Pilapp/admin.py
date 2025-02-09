from django.contrib import admin
from .models import Alumno, Paquete, AlumnoPaquete

admin.site.register(Alumno)
admin.site.register(Paquete)
admin.site.register(AlumnoPaquete)
