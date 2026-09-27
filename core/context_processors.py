from .models import ReservaObservacion

def notificaciones_usuario(request):
    # Si el usuario ha iniciado sesión, buscamos sus datos
    if request.user.is_authenticated:
        # Traemos las últimas 3 reservas para mostrarlas en la lista desplegable
        ultimas_reservas = ReservaObservacion.objects.filter(usuario=request.user).order_by('-fecha_solicitud')[:3]
        # Contamos cuántas reservas tiene en total para el número de la campana
        total_reservas = ReservaObservacion.objects.filter(usuario=request.user).count()
        
        return {
            'notif_reservas': ultimas_reservas,
            'notif_count': total_reservas
        }
    
    # Si no ha iniciado sesión, devolvemos un diccionario vacío
    return {}