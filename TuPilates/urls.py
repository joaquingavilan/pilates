from django.contrib import admin
from django.urls import path
from Pilapp.views import *
from django.urls import include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('registrar_alumno/', registrar_alumno, name='registrar_alumno'),
    path('actualizar_ruc/', actualizar_ruc, name='actualizar_ruc'),
    path('verificar_turno/', verificar_turno, name='verificar_turno'), #ready
    path('verificar_clase_hoy/', verificar_clase_hoy, name='verificar_clase_hoy'), #lista
    path('registrar_alumno_ocasional/', registrar_alumno_ocasional, name='registrar_alumno_ocasional'),
    path('verificar_turno_a_partir_de/', verificar_turno_a_partir_de, name='verificar_turno_a_partir_de'), #listo
    path('verificar_turno_manana/', verificar_turno_manana, name='verificar_turno_manana'), #done
    path('verificar_turno_antes_de/', verificar_turno_antes_de, name='verificar_turno_antes_de'), #creado
    path('listar_precios_paquetes/', listar_precios_paquetes, name='listar_precios_paquetes'), #done
    path('obtener_alumnos_turno/', obtener_alumnos_turno, name='obtener_alumnos_turno'), #listo
    path('obtener_alumnos_dia/', obtener_alumnos_dia, name='obtener_alumnos_dia'), #done
    path('obtener_alumnos_clase/', obtener_alumnos_clase, name='obtener_alumnos_clase'), #yeeesh
    path('obtener_id_alumno/', obtener_id_alumno, name='obtener_id_alumno'), #ready
    path('registrar_asistencias/', registrar_asistencias, name='registrar_asistencias'),
    path('obtener_clases_agendadas/', obtener_clases_agendadas, name='obtener_clases_agendadas'), #donezo
    path('reprogramar_clase/', reprogramar_clase, name='reprogramar_clase'),
    path('panel/', include('Pilapp.urls_panel')),
]
