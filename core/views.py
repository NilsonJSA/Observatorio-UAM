from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

import requests
from django.http import JsonResponse
from django.conf import settings
from datetime import datetime, timezone, timedelta
from .models import ReservaObservacion

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import (
    ReservaCreacionSerializer,
    RegistroUsuarioSerializer,
)

from django.utils import timezone as django_timezone

from math import isfinite

from .weather_client import consultar_condiciones_windy

# Tu vista home queda igual
def home(request):
    return render(request, 'core/index.html')

# Vista de Inicio de Sesión
def login_view(request):
    if request.method == 'POST':
        # 1. Capturamos lo que el usuario escribió
        email = request.POST.get('email')
        contrasena = request.POST.get('password')

        # 2. Django usa 'username' por defecto. Como pedimos correo,
        # le decimos que valide usando el email en el campo username.
        user = authenticate(request, username=email, password=contrasena)

        # 3. Verificamos si existe y la contraseña es correcta
        if user is not None:
            login(request, user) # ¡Sesión iniciada!
            return redirect('home') # Lo mandamos a la página principal
        else:
            # Si falla, mandamos un mensaje de error
            messages.error(request, "Correo o contraseña incorrectos.")

    return render(request, 'core/login.html')

# Vista de Registro
def register_view(request):
    if request.method == "POST":
        serializer = RegistroUsuarioSerializer(
            data={
                "nombre": request.POST.get("nombre", ""),
                "email": request.POST.get("email", ""),
                "password": request.POST.get("password", ""),
            }
        )
        if serializer.is_valid():
            serializer.save()
            messages.success(
                request,
                "¡Cuenta creada correctamente! "
                "Ahora puedes iniciar sesión."
            )
            return redirect("login")
        for campo, errores in serializer.errors.items():
            for error in errores:
                messages.error(
                    request,
                    f"{campo}: {error}"
                )
    return render(
        request,
        "core/register.html",
        {
            "nombre_previo": (
                request.POST.get("nombre", "")
                if request.method == "POST" else ""
            ),
            "email_previo": (
                request.POST.get("email", "")
                if request.method == "POST" else ""
            ),
        },
    )

# Tu vista agendar 2.0
@login_required(login_url='login')
def agendar_view(request):

    if request.method == 'POST':

        serializer = ReservaCreacionSerializer(
            data=request.POST
        )

        if serializer.is_valid():

            serializer.save(
                usuario=request.user
            )

            messages.success(
                request,
                "Tu reserva ha sido registrada correctamente. "
                "Está pendiente de revisión administrativa."
            )

            return redirect('perfil')

        for campo, errores in serializer.errors.items():
            for error in errores:
                messages.error(
                    request,
                    f"{campo}: {error}"
                )

    return render(
        request,
        "core/agendar.html",
        {
            "fecha_minima": django_timezone.localdate().isoformat(),
            "datos_formulario": (
                request.POST if request.method == "POST" else {}
            ),
        },
    )

# Vista para Cerrar Sesión
def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión exitosamente. ¡Vuelve pronto!")
    return redirect('home')

# Vista del Perfil (El decorador asegura que solo entren usuarios logueados)
@login_required
def perfil_view(request):
    # Traemos SOLO las reservas del usuario que está logueado
    mis_reservas = ReservaObservacion.objects.filter(usuario=request.user).order_by('-fecha_solicitud')

    context = {
        'reservas': mis_reservas
    }
    return render(request, 'core/perfil.html', context)


#Api del clima
# #UAM google maps 12.108975711245238, -86.25688407914218
#UAM Windy 12.109, -86.257


def consultar_clima_api(request):
    fecha = request.GET.get("fecha")
    hora = request.GET.get("hora", "18:00")
    hora_fin = request.GET.get("hora_fin") or None

    if not fecha:
        return JsonResponse({
            "estado": "esperando_fecha",
            "mensaje": "Esperando fecha..."
        })

    # Consulta centralizada: Windy + evaluación meteorológica.
    resultado = consultar_condiciones_windy(
        fecha,
        hora,
        hora_fin,
    )

    estado = resultado.get("estado", "error_servicio")

    # Condiciones que se pudieron evaluar.
    if estado in ("favorable", "desfavorable"):

        nubosidad = resultado["nubosidad"]
        lluvia = resultado["precipitacion_3h"]

        if settings.WEATHER_MODE == "PRUEBAS":
            origen = "Datos meteorológicos de prueba"
        else:
            origen = "Evaluación meteorológica"

        if estado == "desfavorable":
            mensaje = (
                f"⚠️ {origen}: "
                f"{nubosidad}% de nubosidad y "
                f"{lluvia} mm de precipitación "
                "acumulada en tres horas. "
                "Indicadores desfavorables según "
                "los umbrales provisionales."
            )

            if settings.WEATHER_MODE == "PRUEBAS":
                mensaje += (
                    " Puedes enviar tu solicitud "
                    "para revisión administrativa."
                )
            else:
                mensaje += (
                    " La solicitud está sujeta a "
                    "la política meteorológica del servidor."
                )

        else:
            mensaje = (
                f"ℹ️ {origen}: "
                f"{nubosidad}% de nubosidad y "
                f"{lluvia} mm de precipitación "
                "acumulada en tres horas. "
                "Indicadores favorables según "
                "los umbrales provisionales. "
                "Esto no constituye una aprobación."
            )

        return JsonResponse({
            "estado": estado,
            "mensaje": mensaje,
            "nubosidad": nubosidad,
            "precipitacion_3h": lluvia,
            "muestras_evaluadas": resultado[
                "muestras_evaluadas"
            ],
        })

    # Respuestas cuando no se pudo evaluar el clima.
    mensajes = {
        "formato_invalido": (
            "⚠️ Formato de fecha u hora inválido."
        ),
        "sin_datos": (
            "⚠️ Información meteorológica incompleta. "
            "No es posible evaluar las condiciones."
        ),
        "fuera_de_rango": (
            "ℹ️ No hay pronóstico disponible para "
            "la fecha y el horario seleccionados."
        ),
        "error_configuracion": (
            "El servicio meteorológico no está configurado."
        ),
        "error_servicio": (
            "No fue posible consultar el servicio meteorológico."
        ),
    }

    mensaje = resultado.get(
        "mensaje",
        mensajes.get(
            estado,
            "No fue posible evaluar las condiciones."
        )
    )

    if estado == "formato_invalido":
        codigo_http = 400
    elif estado in ("error_servicio", "error_configuracion"):
        codigo_http = resultado.get("codigo_http", 503)
    else:
        codigo_http = 200

    return JsonResponse(
        {
            "estado": estado,
            "mensaje": mensaje,
        },
        status=codigo_http,
    )
