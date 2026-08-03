import os
import re

# 1. Update urls_panel.py
urls_path = 'Pilapp/urls_panel.py'
with open(urls_path, 'r', encoding='utf-8') as f:
    urls_content = f.read()

urls_insertion = """    # Feriados
    path('feriados/', views_panel.panel_feriados, name='panel_feriados'),
    path('feriados/<str:fecha_str>/eliminar/', views_panel.panel_feriados_eliminar, name='panel_feriados_eliminar'),
    
    # Reemplazos
    path('reemplazos/', views_panel.panel_reemplazos, name='panel_reemplazos'),
    path('reemplazos/<str:fecha_str>/eliminar/', views_panel.panel_reemplazos_eliminar, name='panel_reemplazos_eliminar'),
"""
if 'path(\'reemplazos/\'' not in urls_content:
    urls_content = re.sub(
        r"    # Feriados\n    path\('feriados/', views_panel\.panel_feriados, name='panel_feriados'\),\n    path\('feriados/<str:fecha_str>/eliminar/', views_panel\.panel_feriados_eliminar, name='panel_feriados_eliminar'\),",
        urls_insertion,
        urls_content
    )
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls_content)


# 2. Update views_panel.py
views_path = 'Pilapp/views_panel.py'
with open(views_path, 'r', encoding='utf-8') as f:
    views_content = f.read()

views_insertion = """
@require_http_methods(["GET", "POST"])
def panel_reemplazos(request):
    from .models import ReemplazoDia
    from datetime import datetime
    
    if request.method == "POST":
        fecha_str = request.POST.get("fecha")
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                ReemplazoDia.objects.get_or_create(fecha=fecha)
                messages.success(request, f"Día de reemplazo agregado para el {fecha.strftime('%d/%m/%Y')}.")
            except ValueError:
                messages.error(request, "Fecha inválida.")
            except Exception as e:
                messages.error(request, f"Error: {e}")
        return redirect("panel_reemplazos")
        
    reemplazos = ReemplazoDia.objects.all().order_by("-fecha")
    return render(request, "admin_panel/reemplazos.html", {"reemplazos": reemplazos})

@require_POST
def panel_reemplazos_eliminar(request, fecha_str):
    from .models import ReemplazoDia
    from datetime import datetime
    
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        ReemplazoDia.objects.filter(fecha=fecha).delete()
        messages.success(request, f"Día de reemplazo ({fecha.strftime('%d/%m/%Y')}) eliminado.")
    except ValueError:
        messages.error(request, "Fecha inválida.")
    except Exception as e:
        messages.error(request, f"Error al eliminar: {e}")
        
    return redirect("panel_reemplazos")

# --- VISTAS PARA PROFES (ACCESO DIRECTO MAGICO) ---
"""

if 'def panel_reemplazos(' not in views_content:
    views_content = views_content.replace("# --- VISTAS PARA PROFES (ACCESO DIRECTO MAGICO) ---", views_insertion)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views_content)


# 3. Create reemplazos.html
template_content = """{% extends "admin_panel/base.html" %}

{% block title %}Días de Reemplazo{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row mb-4 align-items-center">
        <div class="col-md-6">
            <h2 class="h3 mb-0" style="font-weight: 700; color: #1e293b; font-family: 'Outfit', sans-serif;">
                <i class="bi bi-person-badge me-2 text-primary"></i>Días de Reemplazo
            </h2>
            <p class="text-muted mt-2 mb-0">Habilita fechas en las que el link de reemplazantes funcionará.</p>
        </div>
        <div class="col-md-6 text-md-end mt-3 mt-md-0">
            <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-toggle="modal" data-bs-target="#agregarReemplazoModal">
                <i class="bi bi-plus-lg me-1"></i> Agregar Día
            </button>
        </div>
    </div>

    {% if messages %}
    <div class="mt-3">
        {% for message in messages %}
        <div class="alert alert-{{ message.tags }} alert-dismissible fade show shadow-sm" role="alert">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="card shadow-sm border-0" style="border-radius: 16px;">
        <div class="card-body p-0">
            {% if reemplazos %}
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th class="ps-4">Fecha</th>
                            <th>Estado Actual</th>
                            <th class="text-end pe-4">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in reemplazos %}
                        <tr>
                            <td class="ps-4 fw-medium">{{ item.fecha|date:"l d/m/Y"|title }}</td>
                            <td>
                                <span class="badge bg-success-subtle text-success">Link Habilitado</span>
                            </td>
                            <td class="text-end pe-4">
                                <form method="post" action="{% url 'panel_reemplazos_eliminar' item.fecha|date:'Y-m-d' %}" class="d-inline" onsubmit="return confirm('¿Seguro que deseas desactivar el link para esta fecha?');">
                                    {% csrf_token %}
                                    <button type="submit" class="btn btn-sm btn-outline-danger" title="Desactivar acceso">
                                        <i class="bi bi-trash"></i> Desactivar
                                    </button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="p-5 text-center text-muted">
                <i class="bi bi-calendar-x fs-1 text-secondary opacity-50 mb-3 d-block"></i>
                <h5>No hay días de reemplazo configurados</h5>
                <p>Agrega un día para permitir el acceso temporal a través del link de reemplazantes.</p>
            </div>
            {% endif %}
        </div>
    </div>
    
    <div class="alert alert-info mt-4" role="alert">
        <i class="bi bi-info-circle-fill me-2"></i> <strong>Link para Reemplazantes:</strong> 
        Copia y envía esta dirección a las profesoras reemplazantes: 
        <br><br>
        <code class="fs-5 bg-white p-2 rounded border">https://{{ request.get_host }}/panel/profes/reemplazo/clases/</code>
        <br><br>
        <em>Nota: Este enlace mostrará "Acceso denegado" a menos que hayas agregado la fecha del día actual en la tabla de arriba.</em>
    </div>
</div>

<!-- Modal Agregar Reemplazo -->
<div class="modal fade" id="agregarReemplazoModal" tabindex="-1" aria-labelledby="agregarReemplazoModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content border-0 shadow" style="border-radius: 16px;">
            <div class="modal-header border-bottom-0 pb-0">
                <h5 class="modal-title fw-bold" id="agregarReemplazoModalLabel">Habilitar Nuevo Día</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <form method="post" action="{% url 'panel_reemplazos' %}">
                {% csrf_token %}
                <div class="modal-body py-4">
                    <p class="text-muted mb-4 text-sm">Selecciona una fecha para habilitar el link de las reemplazantes ese día.</p>
                    
                    <div class="mb-3">
                        <label for="fecha" class="form-label fw-medium text-dark">Fecha</label>
                        <input type="date" class="form-control form-control-lg bg-light border-0" id="fecha" name="fecha" required>
                    </div>
                </div>
                <div class="modal-footer border-top-0 pt-0 pb-4 px-4">
                    <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancelar</button>
                    <button type="submit" class="btn btn-primary px-4">Habilitar Día</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""

os.makedirs('Pilapp/templates/admin_panel', exist_ok=True)
with open('Pilapp/templates/admin_panel/reemplazos.html', 'w', encoding='utf-8') as f:
    f.write(template_content)


# 4. Update base.html
base_path = 'Pilapp/templates/admin_panel/base.html'
with open(base_path, 'r', encoding='utf-8') as f:
    base_content = f.read()

sidebar_insertion = """            <li class="nav-item">
                <a class="nav-link {% if 'feriado' in request.resolver_match.url_name %}active{% endif %}" 
                   href="{% url 'panel_feriados' %}">
                    <i class="bi bi-calendar-x"></i> Feriados
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link {% if 'reemplazo' in request.resolver_match.url_name %}active{% endif %}" 
                   href="{% url 'panel_reemplazos' %}">
                    <i class="bi bi-person-badge"></i> Reemplazos
                </a>
            </li>"""

if 'panel_reemplazos' not in base_content:
    base_content = re.sub(
        r'            <li class="nav-item">\n                <a class="nav-link \{% if \'feriado\' in request.resolver_match.url_name %\}active\{% endif %\}" \n                   href="\{% url \'panel_feriados\' %\}">\n                    <i class="bi bi-calendar-x"></i> Feriados\n                </a>\n            </li>',
        sidebar_insertion,
        base_content
    )
    with open(base_path, 'w', encoding='utf-8') as f:
        f.write(base_content)

print("Patch applied successfully.")
