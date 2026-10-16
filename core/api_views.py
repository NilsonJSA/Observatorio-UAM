from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework import status

from .models import ReservaObservacion
from .serializers import (
    ReservaObservacionSerializer,
    ReservaCreacionSerializer,
    ConsultaDisponibilidadSerializer,
    RegistroUsuarioSerializer,
)

from django.contrib.auth import authenticate

from django.db.models import F

from django.shortcuts import get_object_or_404

from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import authentication_classes

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

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def crear_reserva(request):

    serializer = ReservaCreacionSerializer(
        data=request.data
    )

    if serializer.is_valid():

        reserva = serializer.save(
            usuario=request.user
        )

        resultado = ReservaObservacionSerializer(
            reserva
        )

        return Response(
            resultado.data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def consultar_disponibilidad(request):

    serializer = ConsultaDisponibilidadSerializer(
        data=request.query_params
    )

    serializer.is_valid(raise_exception=True)
    datos = serializer.validated_data

    # Estados considerados para el conteo preliminar.
    # No representan reglas institucionales confirmadas.
    estados_relevantes = [
        "1_admin",
        "2_cartera",
        "3_director",
        "aprobada",
    ]

    solapamientos = ReservaObservacion.objects.filter(
        fecha=datos["fecha"],
        estado__in=estados_relevantes,
        hora_inicio__lt=datos["hora_fin"],
        hora_fin__gt=datos["hora_inicio"],
    ).filter(
        hora_fin__gt=F("hora_inicio")
    ).count()

    return Response({
        "fecha": datos["fecha"].isoformat(),
        "hora_inicio": datos["hora_inicio"].strftime("%H:%M"),
        "hora_fin": datos["hora_fin"].strftime("%H:%M"),
        "solicitudes_solapadas": solapamientos,
        "disponibilidad": "pendiente_de_validacion",
        "mensaje": (
            "Los solapamientos son informativos. "
            "La disponibilidad definitiva depende "
            "de las reglas institucionales de aforo "
            "y asignacion de recursos."
        ),
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detalle_reserva(request, reserva_id):

    reserva = get_object_or_404(
        ReservaObservacion,
        pk=reserva_id,
        usuario=request.user
    )

    serializer = ReservaObservacionSerializer(reserva)

    return Response(serializer.data)

@api_view(["POST"])
@permission_classes([AllowAny])
def api_registro(request):
    serializer = RegistroUsuarioSerializer(
        data=request.data
    )

    serializer.is_valid(raise_exception=True)

    usuario = serializer.save()

    return Response({
        "id": usuario.id,
        "email": usuario.email,
        "nombre": usuario.first_name,
    }, status=status.HTTP_201_CREATED)

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def api_logout(request):

    request.auth.delete()

    return Response(
        status=status.HTTP_204_NO_CONTENT
    )