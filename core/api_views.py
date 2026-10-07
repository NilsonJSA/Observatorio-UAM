from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import ReservaObservacion
from .serializers import ReservaObservacionSerializer


@api_view(["GET"])
def health_check(request):
    return Response({
        "status": "ok",
        "system": "AstroUAM"
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mis_reservas(request):
    reservas = ReservaObservacion.objects.filter(
        usuario=request.user
        ).order_by('-fecha_solicitud')
    
    serializer = ReservaObservacionSerializer(reservas, many=True)

    return Response(serializer.data)