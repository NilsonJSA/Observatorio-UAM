from django.urls import path
from . import api_views


urlpatterns = [
    path("health/", api_views.health_check, name="api-health"),
    path("reservas/mias/", api_views.mis_reservas, name="api-mis-reservas"),
    path("login/", api_views.api_login, name="api-login"),
]