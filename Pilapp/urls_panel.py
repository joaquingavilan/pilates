from django.urls import path
from . import views_panel

urlpatterns = [
    # Dashboard
    path('', views_panel.panel_dashboard, name='panel_dashboard'),
    
    # Calendario
    path('calendario/', views_panel.panel_calendario, name='panel_calendario'),
    
    # Alumnos
    path('alumnos/', views_panel.panel_alumnos, name='panel_alumnos'),
    path('alumnos/<int:id_alumno>/', views_panel.panel_alumno_detalle, name='panel_alumno_detalle'),
    
    # Clases
    path('clases/', views_panel.panel_clases, name='panel_clases'),
    path('clases/<int:id_clase>/', views_panel.panel_clase_detalle, name='panel_clase_detalle'),
    
    # Turnos
    path('turnos/', views_panel.panel_turnos, name='panel_turnos'),
    
    # Pagos
    path('pagos/', views_panel.panel_pagos, name='panel_pagos'),
    
    # Prospectos
    path('prospectos/', views_panel.panel_prospectos, name='panel_prospectos'),
    
    # API endpoints
    path('api/clase/<int:id_clase>/alumnos/', views_panel.api_clase_alumnos, name='api_clase_alumnos'),

    path("api/calendario/", views_panel.api_calendario, name="api_calendario"),

]