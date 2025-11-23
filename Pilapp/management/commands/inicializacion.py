from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta

from Pilapp.models import Persona, Instructor
from Pilapp.utils import crear_turnos, crear_clases_rango_fechas


class Command(BaseCommand):
    help = "Inicializa la BD de TuPilates: instructora, turnos y clases."

    def handle(self, *args, **kwargs):

        self.stdout.write(self.style.MIGRATE_HEADING("== Bootstrapping TuPilates =="))

        # 1) Instructora
        with transaction.atomic():
            instructora = Instructor.objects.filter(id_instructor=1).first()

            if not instructora:
                persona = Persona.objects.create(
                    nombre="Instructora",
                    apellido="General",
                    telefono="000"
                )
                Instructor.objects.create(id_instructor=1, id_persona=persona)
                self.stdout.write(self.style.SUCCESS("✓ Instructora creada (id=1)"))
            else:
                self.stdout.write("✓ Instructora ya existe")

        # 2) Turnos
        result_turnos = crear_turnos()
        self.stdout.write(self.style.SUCCESS(f"✓ {result_turnos['mensaje']}"))

        # 3) Clases para 30 días
        hoy = date.today()
        rango_fin = hoy + timedelta(days=30)

        self.stdout.write(f"Generando clases desde {hoy} hasta {rango_fin}...")
        result_clases = crear_clases_rango_fechas(hoy, rango_fin)

        self.stdout.write(self.style.SUCCESS(
            f"✓ {result_clases['mensaje']}"
        ))

        self.stdout.write(self.style.MIGRATE_LABEL("== Bootstrap completo =="))
