from rest_framework import serializers

from .models import ReservaObservacion


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

        read_only_fields = fields