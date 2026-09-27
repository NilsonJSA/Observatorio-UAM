from django.contrib import admin
from .models import Reserva

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    # Columnas que se verán en la tabla del panel de administración
    list_display = ('usuario', 'objetivo', 'fecha_observacion', 'hora_inicio', 'estado')
    
    # Agregar filtros laterales
    list_filter = ('estado', 'objetivo', 'fecha_observacion')