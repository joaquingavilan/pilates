from django.db import models

class HorarioDisponible(models.Model):
    """
    Define los horarios potencialmente disponibles para configurar turnos.

    Usado como plantilla o referencia para la creación de objetos `Turno`.
    No tiene relación directa con clases o alumnos.

    Campos:
        dia (str): Día de la semana (Lunes–Sábado).
        horario (TimeField): Hora de inicio del turno.

    Ejemplo de representación:
        "Martes 19:00"
    """

    DIAS_CHOICES = [
        ('Lunes', 'Lunes'),
        ('Martes', 'Martes'),
        ('Miércoles', 'Miércoles'),
        ('Jueves', 'Jueves'),
        ('Viernes', 'Viernes'),
        ('Sábado', 'Sábado'),
    ]

    dia = models.CharField(max_length=10, choices=DIAS_CHOICES)
    horario = models.TimeField()

    def __str__(self):
        return f"{self.dia} {self.horario.strftime('%H:%M')}"


class Persona(models.Model):
    """
    Representa una persona física (alumno, instructor o contacto).

    Campos:
        id_persona (PK)
        nombre, apellido
        telefono: identificador principal de contacto.
        ruc: número de contribuyente (puede actualizarse luego).
        observaciones: notas generales (comentarios administrativos).

    Relaciona con:
        - Alumno
        - Instructor
        - Pago (indirectamente vía facturación)
    """    
    id_persona = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    ruc = models.CharField(max_length=20, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class Alumno(models.Model):
    """
    Representa un alumno inscrito en el estudio.

    Campos:
        id_alumno (PK)
        id_persona (FK Persona)
        canal_captacion: medio de llegada (ej. Instagram, referido, etc.)
        ultima_clase: última asistencia registrada.
        estado:
            - 'ocasional': asiste por clase suelta.
            - 'regular': posee paquete activo.
            - 'inactivo': sin actividad reciente.

    Relaciones:
        - AlumnoPaquete (paquetes activos o vencidos)
        - AlumnoClase / AlumnoClaseOcasional (historial de clases)
    """
    id_alumno = models.AutoField(primary_key=True)
    id_persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    canal_captacion = models.CharField(max_length=100, blank=True, null=True)
    ultima_clase = models.DateField(blank=True, null=True)
    estado = models.CharField(max_length=50, choices=[
        ('ocasional', 'Ocasional'),  # Attends without package
        ('regular', 'Regular'),       # Has an active package
        ('inactivo', 'Inactivo')      # No active packages
    ], default='ocasional')
    def __str__(self):
        return f"Alumno: {self.id_persona}"

class Instructor(models.Model):
    """
    Representa un instructor del estudio, asociado a una persona.

    Campos:
        id_instructor (PK)
        id_persona (FK Persona)
    """
    id_instructor = models.AutoField(primary_key=True)
    id_persona = models.ForeignKey(Persona, on_delete=models.CASCADE)

    def __str__(self):
        return f"Instructor: {self.id_persona}"

class Turno(models.Model):
    """
    Define un turno recurrente semanal (día + hora), base para generar clases.

    Campos:
        id_turno (PK)
        horario (TimeField)
        dia (CharField): Lunes–Sábado.

    Propiedades:
        - lugares_ocupados: cantidad de alumnos asignados vía AlumnoPaqueteTurno.
        - estado: "Libre" (<4 lugares) o "Ocupado" (>=4).

    Ejemplo:
        Lunes 19:00 → usado semanalmente para crear clases concretas (Clase).
    """
    DIAS_CHOICES = [
        ('Lunes', 'Lunes'),
        ('Martes', 'Martes'),
        ('Miércoles', 'Miércoles'),
        ('Jueves', 'Jueves'),
        ('Viernes', 'Viernes'),
        ('Sábado', 'Sábado'),
    ]

    id_turno = models.AutoField(primary_key=True)
    horario = models.TimeField()
    dia = models.CharField(max_length=10, choices=DIAS_CHOICES)

    def __str__(self):
        return f"{self.dia} - {self.horario.strftime('%H:%M')}"

    @property
    def lugares_ocupados(self):
        from .models import AlumnoPaqueteTurno
        return AlumnoPaqueteTurno.objects.filter(id_turno_id=self.id_turno).count()

    @property
    def estado(self):
        return 'Ocupado' if self.lugares_ocupados >= 4 else 'Libre'



class Clase(models.Model):
    """
    Instancia concreta de un turno en una fecha determinada.

    Campos:
        id_clase (PK)
        id_instructor (FK Instructor)
        id_turno (FK Turno)
        fecha (DateField)

    Propiedades:
        - total_inscriptos: suma de alumnos regulares y ocasionales asignados.

    Ejemplo:
        Turno: "Martes 19:00" → Clase: "Martes 2025-11-11 19:00"
    """
    id_clase = models.AutoField(primary_key=True)
    id_instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    id_turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
    fecha = models.DateField()

    def __str__(self):
        return f"Clase {self.id_clase} - {self.fecha}"

    @property
    def total_inscriptos(self):
        from .models import AlumnoClase, AlumnoClaseOcasional  # Evitar import circular
        cantidad_regulares = AlumnoClase.objects.filter(id_clase_id=self.id_clase).count()
        cantidad_ocasionales = AlumnoClaseOcasional.objects.filter(id_clase_id=self.id_clase).count()
        return cantidad_regulares + cantidad_ocasionales


class Paquete(models.Model):
    """
    Define un tipo de paquete de clases (por ejemplo, 4, 8 o 12 clases).

    Campos:
        id_paquete (PK)
        cantidad_clases (int)
        costo (decimal)
    """
    id_paquete = models.AutoField(primary_key=True)
    cantidad_clases = models.IntegerField()
    costo = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Paquete {self.id_paquete} - {self.cantidad_clases} clases"

class AlumnoPaquete(models.Model):
    """
    Relaciona a un alumno con un paquete adquirido.

    Campos:
        id_alumno_paquete (PK)
        id_alumno (FK Alumno)
        id_paquete (FK Paquete)
        estado: 'activo' o 'expirado'
        estado_pago: 'pendiente', 'pagado', 'parcial'
        fecha_inicio: inicio del ciclo de clases

    Relaciona con:
        - AlumnoPaqueteTurno (turnos asignados)
        - AlumnoClase (clases generadas)
        - PagoAlumno (pagos asociados)
    """
    id_alumno_paquete = models.AutoField(primary_key=True)
    id_alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    id_paquete = models.ForeignKey(Paquete, on_delete=models.CASCADE)
    estado = models.CharField(max_length=50, choices=[("activo", "Activo"), ("expirado", "Expirado")])
    estado_pago = models.CharField(max_length=50, choices=[
        ("pendiente", "Pendiente"),
        ("pagado", "Pagado"),
        ("parcial", "Pago Parcial")
    ], default="pendiente")
    fecha_inicio = models.DateField(null=True)
    def __str__(self):
        return f"AlumnoPaquete {self.id_alumno_paquete}"


# models.py
class AlumnoPaqueteTurno(models.Model):
    """
    Relaciona un paquete con los turnos seleccionados por el alumno.

    Campos:
        id_alumno_paquete_turno (PK)
        id_alumno_paquete (FK)
        id_turno (FK)
    """
    id_alumno_paquete_turno = models.AutoField(primary_key=True)
    id_alumno_paquete = models.ForeignKey(AlumnoPaquete, on_delete=models.CASCADE)
    id_turno = models.ForeignKey(Turno, on_delete=models.CASCADE)

    def __str__(self):
        return f"AlumnoPaqueteTurno {self.id_alumno_paquete_turno}"

class AlumnoClase(models.Model):
    """
    Registra la participación de un alumno regular en una clase.

    Campos:
        id_alumno_clase (PK)
        id_alumno_paquete (FK)
        id_clase (FK)
        estado:
            'asistió', 'faltó', 'canceló', 'recuperó', 'reprogramó', 'pendiente'

    Representa el detalle de asistencia dentro de un paquete.
    """
    id_alumno_clase = models.AutoField(primary_key=True)
    id_alumno_paquete = models.ForeignKey(AlumnoPaquete, on_delete=models.CASCADE)
    id_clase = models.ForeignKey(Clase, on_delete=models.CASCADE)
    estado = models.CharField(max_length=50, choices=[("asistió", "Asistió"), ("faltó", "Faltó"), ("canceló", "Canceló"), ("recuperó", "Recuperó"), ("reprogramó","Reprogramó"), ("pendiente", "Pendiente")])

    def __str__(self):
        return f"AlumnoClase {self.id_alumno_clase}"


class AlumnoClaseOcasional(models.Model):
    """
    Registra la participación de un alumno ocasional en una clase puntual.

    Campos:
        id_alumno_clase_ocasional (PK)
        id_alumno (FK)
        id_clase (FK)
        estado: 'reservado', 'asistió', 'faltó', 'canceló'

    Restricciones:
        unique_together = ('id_alumno', 'id_clase')
        → Un alumno ocasional no puede anotarse dos veces a la misma clase.
    """
    id_alumno_clase_ocasional = models.AutoField(primary_key=True)
    id_alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    id_clase = models.ForeignKey(Clase, on_delete=models.CASCADE)
    estado = models.CharField(max_length=50, choices=[
        ('reservado', 'Reservado'),
        ('asistió', 'Asistió'), 
        ('faltó', 'Faltó'),
        ('canceló', 'Canceló')
    ])
    
    class Meta:
        unique_together = ('id_alumno', 'id_clase')  # <-- agrega esto

    def __str__(self):
        return f"Clase Ocasional: {self.id_alumno} - {self.id_clase}"

class Pago(models.Model):
    """
    Representa un pago realizado (por alumno o instructor).

    Campos:
        id_pago (PK)
        fecha, monto, nro_pago
        estado: 'pendiente', 'pagado', 'rechazado', 'parcial'
        metodo_pago: 'efectivo', 'tarjeta', 'transferencia'
        comprobante (str): identificador opcional.
        id_factura (FK FacturaPago, nullable)

    Es la entidad raíz de todos los movimientos económicos.
    """
    id_pago = models.AutoField(primary_key=True)
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    nro_pago = models.CharField(max_length=50)
    estado = models.CharField(max_length=50, choices=[
        ("pendiente", "Pendiente"),
        ("pagado", "Pagado"),
        ("rechazado", "Rechazado"),
        ("parcial", "Pago Parcial")
    ])
    id_factura = models.ForeignKey("FacturaPago", on_delete=models.SET_NULL, blank=True, null=True)
    metodo_pago = models.CharField(max_length=50, choices=[("efectivo", "Efectivo"), ("tarjeta", "Tarjeta"), ("transferencia", "Transferencia")])
    comprobante = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Pago {self.id_pago}"

class PagoAlumno(models.Model):
    """
    Relaciona un pago con el paquete de un alumno.

    Campos:
        id_pago_alumno (PK)
        id_pago (FK Pago)
        id_alumno_paquete (FK)
        observaciones (texto opcional)
    """
    id_pago_alumno = models.AutoField(primary_key=True)
    id_pago = models.ForeignKey(Pago, on_delete=models.CASCADE)
    id_alumno_paquete = models.ForeignKey(AlumnoPaquete, on_delete=models.CASCADE)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"PagoAlumno {self.id_pago_alumno}"

class PagoInstructor(models.Model):
    """
    Relaciona un pago con un instructor (por honorarios u otros conceptos).

    Campos:
        id_pago_instructor (PK)
        id_pago (FK Pago)
        id_instructor (FK Instructor)
    """
    id_pago_instructor = models.AutoField(primary_key=True)
    id_pago = models.ForeignKey(Pago, on_delete=models.CASCADE)
    id_instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)

    def __str__(self):
        return f"PagoInstructor {self.id_pago_instructor}"

class FacturaPago(models.Model):
    """
    Representa la factura asociada a un pago emitido.

    Campos:
        id_factura (PK)
        id_pago (FK Pago)
        fecha (DateField)
        identificador (número interno o UUID)
        razon_social, ruc

    Usada para control fiscal y registro contable.
    """
    id_factura = models.AutoField(primary_key=True)
    id_pago = models.ForeignKey(Pago, on_delete=models.CASCADE)
    fecha = models.DateField()
    identificador = models.CharField(max_length=100)
    razon_social = models.CharField(max_length=255)
    ruc = models.CharField(max_length=50)

    def __str__(self):
        return f"Factura {self.id_factura}"

class Conversacion(models.Model):
    """
    Mantiene el estado de una conversación interactiva con un usuario (WhatsApp o web).

    Campos:
        estado (str): flujo actual (ej. 'MenuPrincipal', 'RegistroAlumno', etc.)
        paso (int): número de paso dentro del flujo.
        datos (JSONField): información recolectada (nombre, turno, paquete...).

    Usado por el motor conversacional o agentes MCP.
    """
    estado = models.CharField(max_length=50, default="MenuPrincipal")  # Estado actual del flujo
    paso = models.IntegerField(default=0)  # Paso en el proceso de registro
    datos = models.JSONField(default=dict)  # Datos recolectados

    def __str__(self):
        return f"Conversación {self.estado} - Paso {self.paso}"

class ClienteProspecto(models.Model):
    """
    Representa un cliente potencial antes de registrarse como alumno.

    Campos:
        id_prospecto (PK)
        telefono (str)
        nombre, apellido (opcionales)
        fecha_contacto (auto_now_add)
        canal_captacion: medio de llegada (ej. Instagram, recomendado, etc.)
        estado: 'interesado', 'contactado', 'no_interesado'
        notas: comentarios del equipo.

    Flujo:
        Prospecto → Alumno ocasional → Alumno regular
    """
    id_prospecto = models.AutoField(primary_key=True)
    telefono = models.CharField(max_length=20)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    fecha_contacto = models.DateField(auto_now_add=True)
    canal_captacion = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=50, choices=[
        ('interesado', 'Interesado'),
        ('contactado', 'Contactado'),
        ('no_interesado', 'No Interesado')
    ])
    notas = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Prospecto: {self.telefono}"
