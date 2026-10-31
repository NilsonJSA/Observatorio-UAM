import requests

from django.conf import settings

from .weather_service import evaluar_datos_windy


WINDY_URL = "https://api.windy.com/api/point-forecast/v2"


def consultar_condiciones_windy(fecha, hora_inicio, hora_fin=None):
    """
    Consulta Windy y evalúa el intervalo solicitado.

    Esta función no aprueba, rechaza ni guarda reservas.
    """

    clave = getattr(settings, "WINDY_API_KEY", None)

    if not clave:
        return {
            "estado": "error_configuracion",
            "mensaje": "El servicio meteorológico no está configurado.",
        }

    datos_consulta = {
        "lat": 12.109,
        "lon": -86.257,
        "model": "gfs",
        "parameters": [
            "lclouds",
            "mclouds",
            "hclouds",
            "precip",
        ],
        "levels": ["surface"],
        "key": clave,
    }

    try:
        respuesta = requests.post(
            WINDY_URL,
            json=datos_consulta,
            timeout=10,
        )

        if respuesta.status_code != 200:
            return {
                "estado": "error_servicio",
                "mensaje": "No fue posible obtener el pronóstico.",
            }

        datos = respuesta.json()

    except requests.exceptions.Timeout:
        return {
            "estado": "error_servicio",
            "mensaje": "Windy no respondió dentro del tiempo esperado.",
            "codigo_http": 504,
        }

    except (requests.exceptions.RequestException, ValueError):
        return {
            "estado": "error_servicio",
            "mensaje": "Ocurrió un error al consultar Windy.",
        }

    return evaluar_datos_windy(
        datos,
        fecha,
        hora_inicio,
        hora_fin,
    )