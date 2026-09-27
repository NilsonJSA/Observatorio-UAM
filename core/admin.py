from django.contrib import admin
from .models import ReservaObservacion

@admin.register(ReservaObservacion)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'fecha', 'estado') # Lo que verás en la tabla
    list_filter = ('estado', 'fecha') # Filtros a la derecha