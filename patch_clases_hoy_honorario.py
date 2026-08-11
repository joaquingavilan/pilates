import os

file_path = r'C:\Users\jesus\Documents\pilates\Pilapp\templates\admin_panel\profes\clases_hoy.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

button_html = """
        {% if not es_reemplazo %}
        <div class="mt-4 text-center">
            <button class="btn btn-primary rounded-pill px-4 py-2 shadow-sm fw-bold" style="background-color: #6366f1; border: none; font-family: 'Outfit', sans-serif;" data-bs-toggle="modal" data-bs-target="#honorarioModal">
                <i class="bi bi-wallet2 me-2"></i>Registrar Mis Honorarios de Hoy
            </button>
        </div>

        <!-- Modal Honorarios -->
        <div class="modal fade" id="honorarioModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow-lg rounded-4">
                    <div class="modal-header bg-light border-0 rounded-top-4">
                        <h5 class="modal-title fw-bold" style="font-family: 'Outfit', sans-serif; color: #1e293b;">
                            <i class="bi bi-journal-check me-2 text-primary"></i>Registrar Honorarios
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <form method="post" action="{% url 'profes_registrar_honorario' token %}">
                        {% csrf_token %}
                        <input type="hidden" name="fecha" value="{{ fecha_hoy|date:'Y-m-d' }}">
                        <div class="modal-body p-4">
                            <p class="text-muted small mb-4">Registra tu jornada de hoy <strong>{{ fecha_hoy|date:"d/m/Y" }}</strong>.</p>
                            
                            <div class="mb-3">
                                <label class="form-label fw-semibold text-secondary small">Instructora</label>
                                <select class="form-select bg-light border-0 shadow-sm" name="id_instructor" required>
                                    <option value="">Selecciona tu nombre...</option>
                                    {% for prof in instructores_lista %}
                                    <option value="{{ prof.id_instructor }}">{{ prof.id_persona.nombre }} {{ prof.id_persona.apellido }}</option>
                                    {% endfor %}
                                </select>
                            </div>

                            <div class="row mb-3">
                                <div class="col-6">
                                    <label class="form-label fw-semibold text-secondary small">Turno</label>
                                    <select class="form-select bg-light border-0 shadow-sm" name="turno" required>
                                        <option value="Mañana">Mañana</option>
                                        <option value="Tarde">Tarde</option>
                                    </select>
                                </div>
                                <div class="col-6">
                                    <label class="form-label fw-semibold text-secondary small">Cant. Clases</label>
                                    <input type="number" class="form-control bg-light border-0 shadow-sm" name="cantidad_clases" value="1" min="1" required>
                                </div>
                            </div>

                            <div class="mb-3">
                                <label class="form-label fw-semibold text-secondary small">Monto Total (Gs.)</label>
                                <input type="number" class="form-control bg-light border-0 shadow-sm fs-5 fw-bold text-primary" name="monto_total" placeholder="Ej: 70000" required>
                            </div>
                        </div>
                        <div class="modal-footer border-0 bg-light rounded-bottom-4">
                            <button type="button" class="btn btn-light fw-medium" data-bs-dismiss="modal">Cancelar</button>
                            <button type="submit" class="btn btn-primary fw-bold shadow-sm" style="background-color: #6366f1; border: none;">Guardar Honorario</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        {% endif %}
"""

if "honorarioModal" not in content:
    target = "    </div>\n\n    <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>"
    content = content.replace(target, button_html + target)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Modal and button added to clases_hoy.html")
else:
    print("Modal already exists in clases_hoy.html")
