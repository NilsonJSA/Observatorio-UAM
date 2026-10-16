from django.urls import path
from . import api_views


urlpatterns = [
    path("health/", api_views.health_check, name="api-health"),
    path("reservas/mias/", api_views.mis_reservas, name="api-mis-reservas"),
    path("login/", api_views.api_login, name="api-login"),
    path(
        "reservas/",
        api_views.crear_reserva,
        name="api-crear-reserva"
    ),
    path(
        "disponibilidad/",
        api_views.consultar_disponibilidad,
        name="api-disponibilidad"
    ),

    path(
        "reservas/<int:reserva_id>/",
        api_views.detalle_reserva,
        name="api-detalle-reserva"
    ),

    path(
        "registro/",
        api_views.api_registro,
        name="api-registro"
    ),

    path(
        "logout/",
        api_views.api_logout,
        name="api-logout"
    ),
]