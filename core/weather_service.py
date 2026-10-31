from datetime import date, datetime, time
from math import isfinite
from zoneinfo import ZoneInfo


# Umbrales provisionales para el prototipo.
# NO representan todavía una política aprobada por la UAM.
MAX_NUBOSIDAD = 20
MAX_PRECIPITACION_3H = 2


def _milisegundos(fecha, hora):
    """Convierte una fecha y hora de Nicaragua al formato de Windy."""

    if isinstance(fecha, str):
        fecha = date.fromisoformat(fecha)

    if isinstance(hora, str):
        hora = time.fromisoformat(hora)

    if not isinstance(fecha, date) or not isinstance(hora, time):
        raise ValueError("Fecha u hora inválida")

    momento = datetime.combine(
        fecha,
        hora,
        tzinfo=ZoneInfo("America/Managua"),
    )

    return int(momento.timestamp() * 1000)


def _obtener_valor(datos, indice, *claves):
    """Obtiene un valor numérico válido de una serie de Windy."""

    for clave in claves:
        serie = datos.get(clave)

        if not isinstance(serie, list):
            continue

        if indice >= len(serie):
            return None

        valor = serie[indice]

        if (
            isinstance(valor, bool)
            or not isinstance(valor, (int, float))
            or not isfinite(valor)
        ):
            return None

        return valor

    return None


def evaluar_datos_windy(
    datos,
    fecha,
    hora_inicio,
    hora_fin=None,
):
    """
    Evalúa las muestras disponibles del pronóstico.

    No consulta Internet.
    No crea reservas.
    No decide si debe bloquearse el envío.
    """

    try:
        inicio_ms = _milisegundos(fecha, hora_inicio)

        fin_ms = (
            _milisegundos(fecha, hora_fin)
            if hora_fin is not None
            else inicio_ms
        )

        if fin_ms < inicio_ms:
            raise ValueError("Intervalo inválido")

    except (ValueError, TypeError):
        return {
            "estado": "formato_invalido",
            "mensaje": "Fecha u horario inválido.",
        }

    if not isinstance(datos, dict):
        return {"estado": "sin_datos"}

    tiempos = datos.get("ts", [])

    if (
        not isinstance(tiempos, list)
        or not tiempos
        or any(
            isinstance(t, bool)
            or not isinstance(t, (int, float))
            or not isfinite(t)
            for t in tiempos
        )
    ):
        return {"estado": "sin_datos"}

    if any(
        tiempos[i] >= tiempos[i + 1]
        for i in range(len(tiempos) - 1)
    ):
        return {"estado": "sin_datos"}

    # No utilizar muestras fuera del horizonte disponible.
    if inicio_ms < tiempos[0] or fin_ms > tiempos[-1]:
        return {"estado": "fuera_de_rango"}

    # Cada muestra representa el periodo más cercano a su
    # timestamp. Identificamos las muestras que corresponden
    # al intervalo solicitado.
    indices = []

    for i, momento in enumerate(tiempos):
        limite_izquierdo = (
            (tiempos[i - 1] + momento) / 2
            if i > 0
            else momento
        )

        limite_derecho = (
            (momento + tiempos[i + 1]) / 2
            if i < len(tiempos) - 1
            else momento
        )

        if inicio_ms == fin_ms:
            coincide = (
                limite_izquierdo <= inicio_ms
                <= limite_derecho
            )
        else:
            coincide = (
                limite_izquierdo < fin_ms
                and limite_derecho > inicio_ms
            )

        if coincide:
            indices.append(i)

    if not indices:
        return {"estado": "sin_datos"}

    nubosidades = []
    precipitaciones = []

    for indice in indices:
        bajas = _obtener_valor(
            datos, indice, "lclouds-surface", "lclouds"
        )
        medias = _obtener_valor(
            datos, indice, "mclouds-surface", "mclouds"
        )
        altas = _obtener_valor(
            datos, indice, "hclouds-surface", "hclouds"
        )
        lluvia = _obtener_valor(
            datos,
            indice,
            "past3hprecip-surface",
            "precip-surface",
            "precip",
        )

        if any(
            valor is None
            for valor in (bajas, medias, altas, lluvia)
        ):
            return {"estado": "sin_datos"}

        nubosidades.append(max(bajas, medias, altas))
        precipitaciones.append(lluvia)

    nubosidad_maxima = round(max(nubosidades), 1)
    precipitacion_maxima = round(max(precipitaciones), 2)

    desfavorable = (
        nubosidad_maxima > MAX_NUBOSIDAD
        or precipitacion_maxima > MAX_PRECIPITACION_3H
    )

    return {
        "estado": (
            "desfavorable" if desfavorable else "favorable"
        ),
        "nubosidad": nubosidad_maxima,
        "precipitacion_3h": precipitacion_maxima,
        "muestras_evaluadas": len(indices),
    }