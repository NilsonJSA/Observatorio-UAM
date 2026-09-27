from django.db import models
from django.contrib.auth.models import User # Importamos el sistema de usuarios de Django

class Reserva(models.Model):
    # 1. Definimos las opciones para la lista vertical (Dropdown)
    OBJETIVOS_CHOICES = [
        ('luna', 'La Luna (Fases y Cráteres)'),
        ('jupiter', 'Júpiter y sus lunas galileanas'),
        ('saturno', 'Saturno y sus anillos'),
        ('marte', 'Marte'),
        ('espacio_profundo', 'Espacio Profundo (Nebulosas y Galaxias)'),
        ('todo', 'Un poco de todo (Jornada larga)'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Aprobación'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('completada', 'Observación Completada'),
    ]

    # 2. Relación con el usuario que hace la reserva
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # 3. El astro u objetivo a observar
    objetivo = models.CharField(max_length=20, choices=OBJETIVOS_CHOICES, default='luna')
    
    # 4. Fechas y Horas
    fecha_observacion = models.DateField(verbose_name="Fecha de Observación")
    hora_inicio = models.TimeField(verbose_name="Hora de Inicio")
    hora_fin = models.TimeField(verbose_name="Hora de Finalización")
    
    # 5. Comentarios adicionales (El "blank=True, null=True" significa que es opcional)
    comentarios = models.TextField(blank=True, null=True, verbose_name="Comentarios Específicos")
    
    # 6. Control interno del sistema
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True) # Se guarda automáticamente hoy

    # Esta función hace que en el panel de control se lea bonito el nombre de la reserva
    def __str__(self):
        return f"{self.usuario.username} - {self.get_objetivo_display()} - {self.fecha_observacion}"