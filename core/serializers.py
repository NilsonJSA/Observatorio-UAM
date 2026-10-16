from rest_framework import serializers

from .models import ReservaObservacion

from django.utils import timezone

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

def validar_fecha_y_horario(datos):
    fecha = datos["fecha"]
    inicio = datos["hora_inicio"]
    fin = datos["hora_fin"]

    if fin <= inicio:
        raise serializers.ValidationError({
            "hora_fin": (
                "La hora final debe ser posterior "
                "a la hora de inicio."
            )
        })

    hoy = timezone.localdate()

    if fecha < hoy:
        raise serializers.ValidationError({
            "fecha":"No se permiten reservas en fechas pasadas."
        })

    if fecha == hoy:
        hora_actual = timezone.localtime().time()

        if inicio <= hora_actual:
            raise serializers.ValidationError({
                "hora_inicio": (
                    "La hora de inicio debe ser futura."
                )
            })
    return datos


class ReservaObservacionSerializer(serializers.ModelSerializer):
    objetivo_display = serializers.CharField(
        source="get_objetivo_display",
        read_only=True
    )

    estado_display = serializers.CharField(
        source = "get_estado_display",
        read_only=True
    )

    class Meta:
        model = ReservaObservacion
        fields = [
            "id",
            "objetivo",
            "objetivo_display",
            "fecha",
            "hora_inicio",
            "hora_fin",
            "comentarios",
            "estado",
            "estado_display",
            "mensaje_admin",
            "fecha_solicitud",
            "ultima_modificacion",
        ]

        read_only_fields = fields

class ReservaCreacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservaObservacion
        fields = [
            "id",
            "objetivo",
            "fecha",
            "hora_inicio",
            "hora_fin",
            "comentarios",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        return validar_fecha_y_horario(attrs)

class ConsultaDisponibilidadSerializer(serializers.Serializer):
    fecha = serializers. DateField()
    hora_inicio = serializers.TimeField()
    hora_fin = serializers.TimeField()

    def validate(self, attrs):
        return validar_fecha_y_horario(attrs)

class RegistroUsuarioSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=150)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False
    )

    def validate_email(self, value):
        email = value.strip().lower()

        if get_user_model().objects.filter(
            username__iexact=email
        ).exists():
            raise serializers.ValidationError(
                "Este correo ya está registrado."
            )

        return email

    def validate(self, attrs):
        User = get_user_model()

        usuario = User(
            username=attrs["email"],
            email=attrs["email"],
            first_name=attrs["nombre"]
        )

        try:
            validate_password(
                attrs["password"],
                user=usuario
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError({
                "password": error.messages
            })

        return attrs

    def create(self, validated_data):
        User = get_user_model()

        return User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            first_name=validated_data["nombre"],
            password=validated_data["password"]
        )