"""
URL configuration for TuPilates project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from Pilapp.views import *
urlpatterns = [
    path('admin/', admin.site.urls),
    path('inscripcion/', inscripcion_view, name='inscripcion'),
    path('inscripcion-exitosa/', inscripcion_exitosa, name='inscripcion_exitosa'),
    path('registrar-paquete/', registrar_paquete_view, name='registrar_paquete'),
    path('registro-exitoso/', paquete_registro_exitoso, name='paquete_registro_exitoso'),
]