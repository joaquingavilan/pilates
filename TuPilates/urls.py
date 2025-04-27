from django.contrib import admin
from django.urls import path
from Pilapp.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('prueba/', prueba_railway, name='prueba_railway'),
    path('registrar_alumno/', registrar_alumno, name='registrar_alumno'),
    path('actualizar_ruc/', actualizar_ruc, name='actualizar_ruc'),
    path('verificar_turno/', verificar_turno, name='verificar_turno'),
    path('verificar_clase_hoy/', verificar_clase_hoy, name='verificar_clase_hoy'),
]
