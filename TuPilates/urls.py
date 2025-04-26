from django.contrib import admin
from django.urls import path
from Pilapp.views import prueba_railway, registrar_alumno

urlpatterns = [
    path('admin/', admin.site.urls),
    path('prueba/', prueba_railway, name='prueba_railway'),
    path('registrar_alumno/', registrar_alumno, name='registrar_alumno'),
]
