from django import forms
from .models import *

class PersonaForm(forms.ModelForm):
    class Meta:
        model = Persona
        fields = ['nombre', 'apellido', 'telefono', 'ruc', 'observaciones']

class AlumnoForm(forms.ModelForm):
    class Meta:
        model = Alumno
        fields = ['canal_captacion', 'ultima_clase']

# forms.py
from django import forms
from .models import Alumno, Paquete

class RegistrarPaqueteForm(forms.Form):
    alumno = forms.ModelChoiceField(
        queryset=Alumno.objects.all(), 
        required=False, 
        label="Alumno"
    )
    paquete = forms.ModelChoiceField(
        queryset=Paquete.objects.all(),
        required=False, 
        label="Paquete"
    )
    # Aquí no definimos los turnos ni las fechas fijas, porque los manejaremos manualmente
    # vía el dict request.POST.
