from rest_framework import serializers

from .models import ReservaObservacion

from django.utils import timezone


class ReservaObservacionSerializer(serializers.ModelSerializer):
    objetivo_display = serializers.CharField(
        source="get_objetivo_display",
        read_only=True
    )

    estado_display = serializers.CharField(
        source="get_estado_display",
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
            inicio = attrs["hora_inicio"]
            fin = attrs["hora_fin"]

            if fin <= inicio:
                raise serializers.ValidationError({
                    "hora_fin": (
                        "La hora de finalización debe "
                        "Ser posterior a la hora de inicio."
                    )
                })

            return attrs

        def validate_fecha(self, value):
            if value < timezone.localdate():
                raise serializers.ValidationError(
                    "No se permiten reservas en fechas pasadas."
                )
            return value

class ConsultaDisponibilidadSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    hora_inicio = serializers.TimeField()
    hora_fin = serializers.TimeField()

    def validate(self, attrs):
        fecha = attrs["fecha"]
        inicio = attrs["hora_inicio"]
        fin = attrs["hora_fin"]

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
                "fecha": "No se permiten fechas pasadas."
            })

        if fecha == hoy:
            hora_actual = timezone.localtime().time()

            if inicio <= hora_actual:
                raise serializers.ValidationError({
                    "hora_inicio": (
                        "La hora de inicio debe ser futura."
                    )
                })

        return attrs