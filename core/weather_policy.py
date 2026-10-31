from django.conf import settings


def debe_bloquear_por_clima(
    estado,
    *,
    fuente_real_verificada=False,
):
    """
    Determina si una solicitud debe bloquearse por el clima.

    La fuente debe estar verificada por el backend.
    Nunca se debe aceptar este indicador desde el cliente.
    """

    return (
        settings.WEATHER_MODE == "REAL_BLOQUEO"
        and fuente_real_verificada
        and estado == "desfavorable"
    )