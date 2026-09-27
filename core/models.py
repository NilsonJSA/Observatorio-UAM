from django.db import models
from django.contrib.auth.models import User

class ReservaObservacion(models.Model):
    # 1. Opciones del formulario (¿Qué quieren ver?)
    OBJETIVOS_CHOICES = [
        ('luna', 'La Luna (Fases y Cráteres)'),
        ('jupiter', 'Júpiter y lunas galileanas'),
        ('saturno', 'Saturno y sus anillos'),
        ('marte', 'Marte'),
        ('espacio_profundo', 'Espacio Profundo (Nebulosas y Galaxias)'),
        ('todo', 'Un poco de todo (Jornada larga)'),
    ]

    # 2. EL FLUJO DE TRABAJO DE LA UAM (Workflow de Aprobaciones)
    ESTADOS_CHOICES = [
        ('1_admin', 'Paso 1: Revisión Administración'),
        ('2_cartera', 'Paso 2: Revisión Cartera y Cobro'),
        ('3_director', 'Paso 3: Revisión Director del Observatorio'),
        ('aprobada', '✅ Aprobada Definitivamente'),
        ('reprogramar', '⚠️ Cupo Lleno - Requiere Reprogramar'),
        ('rechazada', '❌ Rechazada / Cancelada'),
        ('finalizada', '🏁 Observación Finalizada'),
    ]

    # 3. Datos del Estudiante / Investigador
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservas')
    
    # 4. Datos de la Reserva (Lo que viene del HTML que hicimos)
    objetivo = models.CharField(max_length=50, choices=OBJETIVOS_CHOICES)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    comentarios = models.TextField(blank=True, null=True)

    # 5. Control de Aforo y Aprobación
    # Todo ticket nuevo nace en el Paso 1 automáticamente
    estado = models.CharField(max_length=30, choices=ESTADOS_CHOICES, default='1_admin') 
    
    # Campo para que el Admin le escriba al usuario por qué debe reprogramar
    mensaje_admin = models.TextField(blank=True, null=True, help_text="Ej: 'El aforo máximo de 15 personas ya se alcanzó este día. Por favor elige mañana.'")

    # Auditoría de tiempo
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    ultima_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Reserva de Observación'
        verbose_name_plural = 'Reservas de Observaciones'
        ordering = ['-fecha_solicitud'] # Muestra las más nuevas primero

    def __str__(self):
        return f"Reserva {self.id} | {self.usuario.username} | {self.fecha} - {self.get_estado_display()}"