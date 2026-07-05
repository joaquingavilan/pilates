from django.urls import path, include
from . import views_panel

urlpatterns = [
    # Dashboard
    path('', views_panel.panel_dashboard, name='panel_dashboard'),
    
    # Calendario
    path('calendario/', views_panel.panel_calendario, name='panel_calendario'),
    
    # Alumnos
    path('alumnos/', views_panel.panel_alumnos, name='panel_alumnos'),
    path('vencimientos/', views_panel.panel_vencimientos, name='panel_vencimientos'),
    path('alumnos/crear/', views_panel.panel_alumno_crear, name='panel_alumno_crear'),
    path('alumnos/<int:id_alumno>/', views_panel.panel_alumno_detalle, name='panel_alumno_detalle'),
    path('alumnos/<int:id_alumno>/editar/', views_panel.panel_alumno_editar, name='panel_alumno_editar'),
    path('alumnos/<int:id_alumno>/turnos/editar/', views_panel.panel_alumno_editar_turnos, name='panel_alumno_editar_turnos'),
    path('alumnos/<int:id_alumno>/paquete/<int:id_alumno_paquete>/editar/', views_panel.panel_alumno_paquete_editar, name='panel_alumno_paquete_editar'),
    path('alumnos/<int:id_alumno>/paquete/<int:id_alumno_paquete>/eliminar/', views_panel.panel_alumno_paquete_eliminar, name='panel_alumno_paquete_eliminar'),
    path('alumnos/<int:id_alumno>/paquete/renovar/', views_panel.panel_alumno_paquete_renovar, name='panel_alumno_paquete_renovar'),
    path('alumnos/<int:id_alumno>/pago/<int:id_pago>/editar/', views_panel.panel_alumno_pago_editar, name='panel_alumno_pago_editar'),
    path('alumnos/<int:id_alumno>/clase/crear/', views_panel.panel_alumno_clase_crear, name='panel_alumno_clase_crear'),
    path('alumnos/<int:id_alumno>/clase/<str:tipo>/<int:id_relacion>/editar/', views_panel.panel_alumno_clase_editar, name='panel_alumno_clase_editar'),
    path('alumnos/<int:id_alumno>/clase/reprogramar/<int:id_clase_origen>/', views_panel.panel_alumno_clase_reprogramar, name='panel_alumno_clase_reprogramar'),
    path('alumnos/<int:id_alumno>/clase/<str:tipo>/<int:id_relacion>/eliminar/', views_panel.panel_alumno_clase_eliminar, name='panel_alumno_clase_eliminar'),
    
    # Clases
    path('clases/', views_panel.panel_clases, name='panel_clases'),
    path('clases/<int:id_clase>/', views_panel.panel_clase_detalle, name='panel_clase_detalle'),
    
    # Turnos
    path('turnos/', views_panel.panel_turnos, name='panel_turnos'),
    
    # Pagos
    path('pagos/', views_panel.panel_pagos, name='panel_pagos'),
    path('resumen-pagos/', views_panel.panel_resumen_pagos, name='panel_resumen_pagos'),
    path('pagos/<int:id_pago>/eliminar/', views_panel.panel_pago_eliminar, name='panel_pago_eliminar'),
    path('pagos/<int:id_pago>/factura/', views_panel.panel_pago_actualizar_factura, name='panel_pago_actualizar_factura'),
    
    # Prospectos
    path('prospectos/', views_panel.panel_prospectos, name='panel_prospectos'),

    # API endpoints
    path('api/clase/<int:id_clase>/alumnos/', views_panel.api_clase_alumnos, name='api_clase_alumnos'),
    path("api/calendario/", views_panel.api_calendario, name="api_calendario"),
    path('api/turno/<int:id_turno>/alumnos/', views_panel.api_turno_alumnos, name='api_turno_alumnos'),

    # Acciones Especiales de Alumnos
    path("alumnos/<int:id_alumno>/eliminar/", views_panel.panel_alumno_eliminar, name="panel_alumno_eliminar"),
    path("alumnos/<int:id_alumno>/paquetes/<int:id_alumno_paquete>/registrar_pago/", views_panel.panel_registrar_pago_alumno, name="panel_registrar_pago_alumno"),
    path("alumnos/<int:id_alumno>/paquetes/<int:id_alumno_paquete>/renovar_paquete/", views_panel.panel_renovar_paquete_alumno, name="panel_renovar_paquete_alumno"),
    
    # Feriados
    path('feriados/', views_panel.panel_feriados, name='panel_feriados'),
    path('feriados/<str:fecha_str>/eliminar/', views_panel.panel_feriados_eliminar, name='panel_feriados_eliminar'),
    
    # Vista Mágica Profes
    path('profes/<str:token>/clases/', views_panel.profes_clases_hoy, name='profes_clases_hoy'),
    path('profes/<str:token>/asistencia/', views_panel.profes_marcar_asistencia, name='profes_marcar_asistencia'),
    path('profes/<str:token>/pagos/', views_panel.profes_pagos, name='profes_pagos'),
    path('profes/<str:token>/pagos/registrar/', views_panel.profes_registrar_pago, name='profes_registrar_pago'),
]
