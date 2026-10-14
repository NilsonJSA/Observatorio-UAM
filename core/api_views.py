from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework import status

from .models import ReservaObservacion
from .serializers import ReservaObservacionSerializer

from django.contrib.auth import authenticate


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

@api_view(["POST"])
@permission_classes([AllowAny])
def api_login(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {
                "detail": "El correo electrónico y la contraseña son obligatorios."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(
        request,
        username=email,
        password=password
    )

    if user is None:
        return Response(
            {
                "detail": "Correo electrónico o contraseña incorrectos."
            },
            status=status.HTTP_401_UNAUTHORIZED
        )

    token, created = Token.objects.get_or_create(user=user)

    return Response({
        "token": token.key,
        "user": {
            "id": user.id,
            "email": user.email,
            "nombre": user.first_name,
        }
    })