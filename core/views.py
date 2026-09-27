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
    if request.method == 'POST':
        # 1. Capturamos los datos
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        contrasena = request.POST.get('password')
        rol = request.POST.get('rol') 
        
        # 2. Revisamos si el correo ya existe en la base de datos
        if User.objects.filter(username=email).exists():
            messages.error(request, "Este correo ya está registrado. Intenta iniciar sesión.")
        else:
            # 3. Creamos al usuario. (Usamos el email como su username interno)
            user = User.objects.create_user(username=email, email=email, password=contrasena, first_name=nombre)
            user.save()
            
            # ¡Éxito! Lo mandamos a que inicie sesión
            messages.success(request, "¡Cuenta creada con éxito! Ahora puedes iniciar sesión.")
            return redirect('login')
            
    return render(request, 'core/register.html')

# Tu vista agendar 2.0
@login_required(login_url='login')
def agendar_view(request):
    if request.method == 'POST':
        # 1. Atrapamos los datos que vienen del formulario HTML
        objetivo = request.POST.get('objetivo')
        fecha = request.POST.get('fecha')
        hora_inicio = request.POST.get('hora_inicio')
        hora_fin = request.POST.get('hora_fin')
        comentarios = request.POST.get('comentarios', '') # Si está vacío, no pasa nada

        # 2. Verificamos que los campos importantes no vengan vacíos
        if objetivo and fecha and hora_inicio and hora_fin:
            try:
                # 3. ¡Mágia! Guardamos la reserva en la base de datos
                ReservaObservacion.objects.create(
                    usuario=request.user, # Asignamos la reserva al estudiante que inició sesión
                    objetivo=objetivo,
                    fecha=fecha,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    comentarios=comentarios
                )
                
                # 4. Avisamos que todo salió perfecto
                messages.success(request, '✅ ¡Tu reserva ha sido guardada con éxito! Está en el Paso 1: Revisión de Administración.')
                
                # 5. Lo mandamos a su panel de perfil para que vea su nueva reserva
                return redirect('perfil') 
                
            except Exception as e:
                messages.error(request, f'❌ Hubo un error al guardar tu reserva: {e}')
        else:
            messages.warning(request, '⚠️ Por favor, completa todos los campos requeridos.')

    # Si es un GET (solo entra a ver la página), le mostramos el formulario normal
    return render(request, 'core/agendar.html')




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
    fecha = request.GET.get('fecha')
    hora = request.GET.get('hora', '18:00') # Si no han puesto hora, asumimos las 6:00 PM por defecto
    
    if not fecha:
        return JsonResponse({'mensaje': 'Esperando fecha...'})

    url = "https://api.windy.com/api/point-forecast/v2"
    
    datos_consulta = {
        "lat": 12.109,
        "lon": -86.257,
        "model": "gfs",
        "parameters": ["lclouds", "mclouds", "hclouds", "precip"],
        "levels": ["surface"],
        "key": settings.WINDY_API_KEY 
    }

    try:
        respuesta = requests.post(url, json=datos_consulta)
        
        if respuesta.status_code == 200:
            datos = respuesta.json() # Abrimos el paquete de datos de Windy
            
            # 1. Convertimos la fecha y hora del usuario a formato de milisegundos (Como lo usa Windy)
            try:
                fecha_hora_str = f"{fecha} {hora}"
                # Configuramos la zona horaria de Nicaragua (UTC -6)
                fecha_usuario = datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M')
                fecha_usuario = fecha_usuario.replace(tzinfo=timezone(timedelta(hours=-6)))
                timestamp_usuario = int(fecha_usuario.timestamp() * 1000) 
            except ValueError:
                return JsonResponse({'mensaje': '⚠️ Formato de fecha/hora inválido.'})

            # 2. Buscamos en qué momento del radar encaja la hora del usuario
            tiempos = datos.get('ts', [])
            if not tiempos:
                return JsonResponse({'mensaje': '⚠️ Radar sin datos de tiempo.'})

            # Encontramos el índice más cercano a la hora solicitada
            diferencias = [abs(t - timestamp_usuario) for t in tiempos]
            indice_exacto = diferencias.index(min(diferencias))

            # 3. EXTRAEMOS LOS DATOS DE FORMA SÚPER SEGURA
            # Creamos una lista llena de ceros del mismo tamaño que el radar de Windy
            # por si Windy decide no enviar algún dato (ej. si no hay lluvia).
            ceros = [0] * len(tiempos)

            # Buscamos las llaves con su nombre completo o resumido, si no existen, usamos los ceros.
            lista_bajas = datos.get('lclouds-surface') or datos.get('lclouds') or ceros
            lista_medias = datos.get('mclouds-surface') or datos.get('mclouds') or ceros
            lista_altas = datos.get('hclouds-surface') or datos.get('hclouds') or ceros
            lista_lluvia = datos.get('precip-surface') or datos.get('precip') or ceros

            # Ahora sí, extraemos el índice exacto sin miedo a salirnos del rango
            nubes_bajas = lista_bajas[indice_exacto]
            nubes_medias = lista_medias[indice_exacto]
            nubes_altas = lista_altas[indice_exacto]
            lluvia = lista_lluvia[indice_exacto]

            # Tomamos la capa de nubes más densa y redondeamos a 1 decimal para que se vea elegante
            nubosidad_maxima = round(max(nubes_bajas, nubes_medias, nubes_altas), 1)
            lluvia = round(lluvia, 2)

            # 🕵️‍♂️ PRINTS DETECTIVES: Para ver en la terminal el salto de horas
            tiempo_encontrado_ms = tiempos[indice_exacto]
            fecha_radar = datetime.fromtimestamp(tiempo_encontrado_ms / 1000.0, tz=timezone(timedelta(hours=-6)))
            
            print("\n🔍 --- INVESTIGACIÓN DE CLIMA ---")
            print(f"Hora que pediste en la web: {fecha_usuario.strftime('%Y-%m-%d %H:%M')}")
            print(f"Bloque del radar seleccionado: {fecha_radar.strftime('%Y-%m-%d %H:%M')}")
            print(f"Nubosidad: {nubosidad_maxima}% | Lluvia: {lluvia}mm")
            print("----------------------------------\n")

            # 4. APLICAMOS LAS REGLAS DEL OBSERVATORIO (Nubosidad > 20% o Lluvia > 2mm)
            if nubosidad_maxima > 20 or lluvia > 2:
                return JsonResponse({
                    'estado': 'rechazado',
                    'mensaje': f'❌ Día no factible: {nubosidad_maxima}% de nubosidad y {lluvia}mm de lluvia pronosticada. Por favor, elige otra fecha.'
                })
            else:
                return JsonResponse({
                    'estado': 'aprobado',
                    'mensaje': f'✅ ¡Cielo despejado! Condiciones óptimas: Nubosidad al {nubosidad_maxima}% y sin riesgo de lluvia.'
                })
                
        else:
            return JsonResponse({'mensaje': '⚠️ Error en el radar meteorológico.'})
            
    except Exception as e:
        # ¡Agregamos estos prints para descubrir al culpable!
        print("❌================ ERROR INTERNO ================❌")
        print(f"El error exacto es: {e}")
        import traceback
        traceback.print_exc()
        print("❌===============================================❌")
        
        return JsonResponse({'mensaje': '❌ Error de conexión con el satélite.'})
    