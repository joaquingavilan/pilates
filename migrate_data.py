import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TuPilates.settings')
django.setup()

from Pilapp.models import PagoAlumno

pagos = PagoAlumno.objects.filter(id_alumno__isnull=True, id_alumno_paquete__isnull=False)
count = 0
for pago in pagos:
    pago.id_alumno = pago.id_alumno_paquete.id_alumno
    pago.save()
    count += 1

print(f"Updated {count} PagoAlumno records.")
