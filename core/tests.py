from django.test import TestCase

# Create your tests here.

from datetime import timedelta, time

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import ReservaObservacion

from rest_framework.authtoken.models import Token

from unittest.mock import patch
from datetime import datetime, timezone as zona_python

from django.urls import reverse
from .views import register_view

from django.test import SimpleTestCase, override_settings
from core.weather_policy import debe_bloquear_por_clima

from datetime import datetime
from zoneinfo import ZoneInfo
from core.weather_service import evaluar_datos_windy

from unittest.mock import patch
from core.weather_client import consultar_condiciones_windy

import requests

class DisponibilidadAPITests(APITestCase):

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="usuario_prueba",
            password="ClavePrueba123!"
        )

        self.fecha = timezone.localdate() + timedelta(days=7)
        self.url = "/api/disponibilidad/"

        ReservaObservacion.objects.create(
            usuario=self.usuario,
            objetivo="saturno",
            fecha=self.fecha,
            hora_inicio=time(19, 0),
            hora_fin=time(20, 0)
        )

    def consultar(self, inicio, fin):
        return self.client.get(self.url, {
            "fecha": self.fecha.isoformat(),
            "hora_inicio": inicio,
            "hora_fin": fin
        })

    def test_requiere_autenticacion(self):
        respuesta = self.consultar("19:00", "20:00")

        self.assertIn(respuesta.status_code, [401, 403])

    def test_detecta_solapamiento(self):
        self.client.force_authenticate(user=self.usuario)

        respuesta = self.consultar("19:30", "20:30")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.data["solicitudes_solapadas"], 1
        )

    def test_horarios_consecutivos(self):
        self.client.force_authenticate(user=self.usuario)

        respuesta = self.consultar("20:00", "21:00")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.data["solicitudes_solapadas"], 0
        )

    def test_rechaza_horas_invertidas(self):
        self.client.force_authenticate(user=self.usuario)

        respuesta = self.consultar("21:00", "19:00")

        self.assertEqual(respuesta.status_code, 400)

class CreacionReservaAPItests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.usuario = User.objects.create_user(
            username="creador_prueba",
            password="ClaveTemporal123!"
        )

        self.otro_usuario = User.objects.create_user(
            username="otro_usuario",
            password="ClaveTemporal123!"
        )

        self.url = "/api/reservas/"

        self.datos = {
            "objetivo": "saturno",
            "fecha": (
                timezone.localdate() + timedelta(days=7)
            ).isoformat(),
            "hora_inicio": "19:00",
            "hora_fin": "20:00",
            "comentarios": "Prueba automatizada"
        }

    def test_requiere_autenticacion(self):
        respuesta = self.client.post(
            self.url,
            self.datos,
            format="json"
            )

        self.assertIn(respuesta.status_code, [401, 403])
        self.assertEqual(
            ReservaObservacion.objects.count(), 0
        )

    def test_crea_reserva_valida(self):
        self.client.force_authenticate(user=self.usuario)

        respuesta = self.client.post(
            self.url,
            self.datos,
            format="json"
        )

        self.assertEqual(respuesta.status_code, 201)

        reserva = ReservaObservacion.objects.get(
            id=respuesta.data["id"]
        )

        self.assertEqual(reserva.usuario, self.usuario)
        self.assertEqual(reserva.estado, "1_admin")

    def test_rechaza_horarios_invertidos(self):
        self.client.force_authenticate(user=self.usuario)

        datos = self.datos.copy()

        datos["hora_inicio"] = "21:00"
        datos["hora_fin"] = "19:00"

        respuesta = self.client.post(
            self.url,
            datos,
            format="json"
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            ReservaObservacion.objects.count(), 0
        )

    def test_rechaza_fechas_pasadas(self):
        self.client.force_authenticate(user=self.usuario)

        datos = self.datos.copy()

        datos["fecha"] = (
            timezone.localdate() - timedelta(days=1)
        ).isoformat()

        respuesta = self.client.post(
            self.url,
            datos,
            format="json"
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            ReservaObservacion.objects.count(), 0
        )

    def test_cliente_no_controla_usuario_ni_estado(self):
        self.client.force_authenticate(user=self.usuario)

        datos = self.datos.copy()
        datos["usuario"] = self.otro_usuario.id
        datos["estado"] = "aprobada"

        respuesta = self.client.post(
            self.url,
            datos,
            format="json"
        )

        self.assertEqual(respuesta.status_code, 201)

        reserva = ReservaObservacion.objects.get(
            id=respuesta.data["id"]
        )

        self.assertEqual(reserva.usuario, self.usuario)
        self.assertEqual(reserva.estado, "1_admin")

    def test_crea_reserva_grupal(self):
        self.client.force_authenticate(user=self.usuario)

        datos = self.datos.copy()
        datos["cantidad_asistentes"] = 5

        respuesta = self.client.post(
            self.url,
            datos,
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data
        )

        reserva = ReservaObservacion.objects.get(
            id=respuesta.data["id"]
        )

        self.assertEqual(reserva.cantidad_asistentes, 5)
        self.assertEqual(respuesta.data["cantidad_asistentes"], 5)

        # Comprobar que el GET también devuelve la cantidad
        consulta = self.client.get("/api/reservas/mias/")

        self.assertEqual(consulta.status_code, 200)
        self.assertEqual(
            consulta.data[0]["cantidad_asistentes"],
            5
        )

    def test_cantidad_predeterminada_es_uno(self):
        self.client.force_authenticate(user=self.usuario)

        respuesta = self.client.post(
            self.url,
            self.datos,
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data
        )

        reserva = ReservaObservacion.objects.get(
            id=respuesta.data["id"]
        )

        self.assertEqual(reserva.cantidad_asistentes, 1)

    def test_rechaza_cantidades_invalidas(self):
        self.client.force_authenticate(user=self.usuario)

        for cantidad in [0, -1]:
            with self.subTest(cantidad=cantidad):
                datos = self.datos.copy()
                datos["cantidad_asistentes"] = cantidad

                respuesta = self.client.post(
                    self.url,
                    datos,
                    format="json"
                )

                self.assertEqual(
                    respuesta.status_code,
                    400,
                    respuesta.data
                )

                self.assertIn(
                    "cantidad_asistentes",
                    respuesta.data
                )

        self.assertEqual(
            ReservaObservacion.objects.count(),
            0
        )

    def test_rechaza_cantidad_superior_limite_tecnico(self):
        self.client.force_authenticate(user=self.usuario)

        datos = self.datos.copy()
        datos["cantidad_asistentes"] = 32768

        respuesta = self.client.post(
            self.url,
            datos,
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            400,
            respuesta.data
        )

        self.assertIn(
            "cantidad_asistentes",
            respuesta.data
        )

    @override_settings(
        WEATHER_MODE="PRUEBAS",
        WINDY_REAL_VERIFIED=False,
        WEATHER_CRITERIA_APPROVED=False,
    )
    @patch("core.serializers.consultar_condiciones_windy")
    def test_modo_pruebas_no_consulta_windy_al_crear(self, mock_clima):
        self.client.force_authenticate(user=self.usuario)

        respuesta = self.client.post(
            self.url, self.datos, format="json"
        )

        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        mock_clima.assert_not_called()

    @override_settings(
        WEATHER_MODE="REAL_BLOQUEO",
        WINDY_REAL_VERIFIED=False,
        WEATHER_CRITERIA_APPROVED=False,
    )
    @patch("core.serializers.consultar_condiciones_windy")
    def test_bloqueo_no_habilitado_rechaza_solicitud(self, mock_clima):
        self.client.force_authenticate(user=self.usuario)

        respuesta = self.client.post(
            self.url, self.datos, format="json"
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(ReservaObservacion.objects.count(), 0)
        mock_clima.assert_not_called()

    @override_settings(
        WEATHER_MODE="REAL_BLOQUEO",
        WINDY_REAL_VERIFIED=True,
        WEATHER_CRITERIA_APPROVED=True,
    )
    @patch("core.serializers.consultar_condiciones_windy")
    def test_bloqueo_rechaza_clima_desfavorable(self, mock_clima):
        self.client.force_authenticate(user=self.usuario)

        mock_clima.return_value = {
            "estado": "desfavorable"
        }

        respuesta = self.client.post(
            self.url, self.datos, format="json"
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(ReservaObservacion.objects.count(), 0)
        mock_clima.assert_called_once()

    @override_settings(
        WEATHER_MODE="REAL_BLOQUEO",
        WINDY_REAL_VERIFIED=True,
        WEATHER_CRITERIA_APPROVED=True,
    )
    @patch("core.serializers.consultar_condiciones_windy")
    def test_bloqueo_permite_clima_favorable(self, mock_clima):
        self.client.force_authenticate(user=self.usuario)

        mock_clima.return_value = {
            "estado": "favorable"
        }

        respuesta = self.client.post(
            self.url, self.datos, format="json"
        )

        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertEqual(ReservaObservacion.objects.count(), 1)
        mock_clima.assert_called_once()


class ValidacionFechaActualAPITests(APITestCase):

    def test_no_permite_reservar_una_hora_pasada_hoy(self):
        usuario = get_user_model().objects.create_user(
            username="usuario_fecha",
            password="ClaveTemporal123!"
        )

        self.client.force_authenticate(user=usuario)

        respuesta = self.client.post(
            "/api/reservas/",
            {
                "objetivo": "luna",
                "fecha": timezone.localdate().isoformat(),
                "hora_inicio": "00:00",
                "hora_fin": "00:01",
                "comentarios": "Prueba de hora pasada"
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("hora_inicio", respuesta.data)

        self.assertEqual(
            ReservaObservacion.objects.count(), 0
        )

class PrivacidadReservasAPI(APITestCase):
    def test_usuario_solo_ve_sus_propias_reservas(self):
        User = get_user_model()

        usuario_a = User.objects.create_user(
            username="usuario_a",
            password="ClaveTemporal123!"
        )

        usuario_b = User.objects.create_user(
            username="usuario_b",
            password="ClaveTemporal123!"
        )

        fecha = timezone.localdate() + timedelta(days=7)

        reserva_a = ReservaObservacion.objects.create(
            usuario=usuario_a,
            objetivo="luna",
            fecha=fecha,
            hora_inicio=time(18, 0),
            hora_fin=time(19, 0)
        )

        ReservaObservacion.objects.create(
            usuario=usuario_b,
            objetivo="marte",
            fecha=fecha,
            hora_inicio=time(19, 0),
            hora_fin=time(20, 0)
        )

        self.client.force_authenticate(user=usuario_a)

        respuesta = self.client.get(
            "/api/reservas/mias/"
        )

        self.assertEqual(respuesta.status_code, 200)

        ids = {
            reserva["id"]
            for reserva in respuesta.data
        }

        self.assertEqual(ids, {reserva_a.id})

class AgendamientoWebTests(TestCase):

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="usuario_web",
            password="ClaveTemporal123!"
        )

        self.client.force_login(self.usuario)

        self.url = "/agendar/"

        self.datos = {
            "objetivo": "saturno",
            "fecha": (
                timezone.localdate() + timedelta(days=7)
            ).isoformat(),
            "hora_inicio": "19:00",
            "hora_fin": "20:00",
            "comentarios": "Prueba desde formulario web"
        }

    def test_web_crea_reserva_valida(self):
        respuesta = self.client.post(
            self.url,
            self.datos
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            ReservaObservacion.objects.count(), 1
        )

        reserva = ReservaObservacion.objects.first()

        self.assertEqual(reserva.usuario, self.usuario)
        self.assertEqual(reserva.estado, "1_admin")

    def test_web_rechaza_horario_invertido(self):
        datos = self.datos.copy()

        datos["hora_inicio"] = "21:00"
        datos["hora_fin"] = "19:00"

        respuesta = self.client.post(
            self.url,
            datos
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            ReservaObservacion.objects.count(), 0
        )

    def test_calendario_incluye_fecha_minima(self):
        hoy = timezone.localdate().isoformat()

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, f'min="{hoy}"')

    def test_web_rechaza_fecha_pasada(self):
        datos = self.datos.copy()

        datos["fecha"] = (
            timezone.localdate() - timedelta(days=1)
        ).isoformat()

        respuesta = self.client.post(
            self.url,
            datos
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            ReservaObservacion.objects.count(),
            0
        )

        self.assertContains(
            respuesta,
            "No se permiten reservas en fechas pasadas."
        )

    def test_web_conserva_datos_tras_error(self):
        datos = self.datos.copy()

        datos["objetivo"] = "marte"
        datos["hora_inicio"] = "21:00"
        datos["hora_fin"] = "19:00"
        datos["comentarios"] = "Prueba de conservación"

        respuesta = self.client.post(
            self.url,
            datos
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertContains(
            respuesta,
            'value="21:00"'
        )

        self.assertContains(
            respuesta,
            'value="19:00"'
        )

        self.assertContains(
            respuesta,
            "Prueba de conservación"
        )

        self.assertEqual(
            respuesta.context["datos_formulario"]["objetivo"],
            "marte"
        )

        self.assertEqual(
            ReservaObservacion.objects.count(),
            0
        )

    def test_web_registra_reserva_grupal(self):
        datos = self.datos.copy()
        datos["cantidad_asistentes"] = "5"

        respuesta = self.client.post(
            self.url,
            datos
        )

        self.assertEqual(respuesta.status_code, 302)

        reserva = ReservaObservacion.objects.get()

        self.assertEqual(
            reserva.cantidad_asistentes,
            5
        )

        self.assertEqual(
            reserva.usuario,
            self.usuario
        )

        self.assertEqual(
            reserva.estado,
            "1_admin"
        )

    @override_settings(
        WEATHER_MODE="REAL_BLOQUEO",
        WINDY_REAL_VERIFIED=True,
        WEATHER_CRITERIA_APPROVED=True,
    )
    @patch("core.serializers.consultar_condiciones_windy")
    def test_web_bloquea_reserva_por_clima_desfavorable(
        self, mock_clima
    ):
        self.client.force_login(self.usuario)

        mock_clima.return_value = {
            "estado": "desfavorable"
        }

        respuesta = self.client.post(
            self.url,
            self.datos
        )

        # La página vuelve a mostrar el formulario.
        self.assertEqual(respuesta.status_code, 200)

        # No se debe guardar ninguna reserva.
        self.assertFalse(
            ReservaObservacion.objects.exists()
        )

        # La validación debe haber consultado el clima.
        mock_clima.assert_called_once()

        # El usuario debe recibir una explicación.
        self.assertContains(
            respuesta,
            "Las condiciones meteorológicas previstas"
        )

class DetalleReservaAPITests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.usuario = User.objects.create_user(
            username="usuario_detalle",
            password="ClaveTemporal123!"
        )

        self.otro_usuario = User.objects.create_user(
            username="usuario_ajeno",
            password="ClaveTemporal123!"
        )

        fecha = timezone.localdate() + timedelta(days=7)

        self.reserva = ReservaObservacion.objects.create(
            usuario=self.usuario,
            objetivo="saturno",
            fecha=fecha,
            hora_inicio=time(19, 0),
            hora_fin=time(20, 0)
        )

        self.reserva_ajena = ReservaObservacion.objects.create(
            usuario=self.otro_usuario,
            objetivo="luna",
            fecha=fecha,
            hora_inicio=time(20, 0),
            hora_fin=time(21, 0)
        )

    def test_requiere_autenticacion(self):
        respuesta = self.client.get(
            f"/api/reservas/{self.reserva.id}/"
        )

        self.assertIn(respuesta.status_code, [401, 403])

    def test_consulta_reserva_propia(self):
        self.client.force_authenticate(user=self.usuario)

        respuesta = self.client.get(
            f"/api/reservas/{self.reserva.id}/"
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.data["id"],
            self.reserva.id
        )

    def test_no_consulta_reserva_ajena(self):
        self.client.force_authenticate(user=self.usuario)

        respuesta = self.client.get(
            f"/api/reservas/{self.reserva_ajena.id}/"
        )

        self.assertEqual(respuesta.status_code, 404)

class RegistroUsuarioAPITests(APITestCase):

    def setUp(self):
        self.url = "/api/registro/"

        self.datos = {
            "nombre": "Usuario Prueba",
            "email": "prueba@ejemplo.com",
            "password": "ClaveSegura123!"
        }

    def test_registro_correcto(self):
        respuesta = self.client.post(
            self.url,
            self.datos,
            format="json"
        )

        self.assertEqual(respuesta.status_code, 201)

        usuario = get_user_model().objects.get(
            username="prueba@ejemplo.com"
        )

        self.assertTrue(
            usuario.check_password("ClaveSegura123!")
        )

    def test_correo_duplicado(self):
        get_user_model().objects.create_user(
            username="prueba@ejemplo.com",
            email="prueba@ejemplo.com",
            password="ClaveSegura123!"
        )

        respuesta = self.client.post(
            self.url,
            self.datos,
            format="json"
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_rechaza_password_debil(self):
        datos = self.datos.copy()
        datos["password"] = "1234"

        respuesta = self.client.post(
            self.url,
            datos,
            format="json"
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_no_permite_privilegios_admin(self):
        datos = self.datos.copy()
        datos["is_staff"] = True
        datos["is_superuser"] = True

        respuesta = self.client.post(
            self.url,
            datos,
            format="json"
        )

        self.assertEqual(respuesta.status_code, 201)

        usuario = get_user_model().objects.get(
            username="prueba@ejemplo.com"
        )

        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)

class CierreSesionAPITests(APITestCase):

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="logout@ejemplo.com",
            email="logout@ejemplo.com",
            password="ClaveTemporal123!"
        )

        self.token, _ = Token.objects.get_or_create(
            user=self.usuario
        )

        self.url = "/api/logout/"

    def test_cierre_invalida_token(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 204)

        self.assertFalse(
            Token.objects.filter(
                key=self.token.key
            ).exists()
        )

        respuesta = self.client.get(
            "/api/reservas/mias/"
        )

        self.assertEqual(respuesta.status_code, 401)

    def test_requiere_autenticacion(self):
        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 401)

    def test_permite_login_despues_del_logout(self):
        token_anterior = self.token.key

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token_anterior}"
        )

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 204)

        self.client.credentials()

        respuesta = self.client.post(
            "/api/login/",
            {
                "email": "logout@ejemplo.com",
                "password": "ClaveTemporal123!"
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertNotEqual(
            respuesta.data["token"],
            token_anterior
        )

class ClimaWindyAPITests(TestCase):

    @patch("core.weather_client.requests.post")
    def test_rechaza_datos_meteorologicos_incompletos(
        self, post_simulado
    ):

        # Fecha futura para realizar la simulación
        fecha = timezone.localdate() + timedelta(days=1)

        instante = datetime.combine(
            fecha,
            time(19, 0),
            tzinfo=zona_python(timedelta(hours=-6))
        )

        timestamp = int(instante.timestamp() * 1000)

        # Simulamos una respuesta exitosa de Windy
        post_simulado.return_value.status_code = 200

        post_simulado.return_value.json.return_value = {
            "ts": [timestamp],
            "lclouds-surface": [10],
            "mclouds-surface": [15],
            "hclouds-surface": [5],

            # Intencionalmente falta precipitación
        }

        respuesta = self.client.get(
            "/api/consultar-clima/",
            {
                "fecha": fecha.isoformat(),
                "hora": "19:00"
            }
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertEqual(
            respuesta.json()["estado"],
            "sin_datos"
        )

        self.assertIn(
            "incompleta",
            respuesta.json()["mensaje"]
        )

        post_simulado.assert_called_once()

    @patch("core.weather_client.requests.post")
    def test_timeout_windy(self, post_simulado):

        from requests.exceptions import Timeout

        post_simulado.side_effect = Timeout(
            "Tiempo de espera agotado"
        )

        fecha = (
            timezone.localdate() + timedelta(days=1)
        ).isoformat()

        respuesta = self.client.get(
            "/api/consultar-clima/",
            {
                "fecha": fecha,
                "hora": "19:00"
            }
        )

        self.assertEqual(respuesta.status_code, 504)

        self.assertEqual(
            respuesta.json()["estado"],
            "error_servicio"
        )

    @patch("core.weather_client.requests.post")
    def test_precipitacion_con_clave_oficial(self, post_simulado):

        fecha = timezone.localdate() + timedelta(days=1)

        instante = datetime.combine(
            fecha,
            time(19, 0),
            tzinfo=zona_python(timedelta(hours=-6))
        )

        timestamp = int(instante.timestamp() * 1000)

        post_simulado.return_value.status_code = 200

        post_simulado.return_value.json.return_value = {
            "ts": [timestamp],
            "lclouds-surface": [10],
            "mclouds-surface": [15],
            "hclouds-surface": [5],
            "past3hprecip-surface": [0.5],
        }

        respuesta = self.client.get(
            "/api/consultar-clima/",
            {
                "fecha": fecha.isoformat(),
                "hora": "19:00"
            }
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.json()["estado"],
            "favorable"
        )

        post_simulado.assert_called_once()

    @patch("core.weather_client.requests.post")
    def test_clima_desfavorable(self, post_simulado):

        fecha = timezone.localdate() + timedelta(days=1)

        instante = datetime.combine(
            fecha,
            time(19, 0),
            tzinfo=zona_python(timedelta(hours=-6))
        )

        timestamp = int(instante.timestamp() * 1000)

        post_simulado.return_value.status_code = 200

        post_simulado.return_value.json.return_value = {
            "ts": [timestamp],
            "lclouds-surface": [75],
            "mclouds-surface": [30],
            "hclouds-surface": [15],
            "past3hprecip-surface": [0.5],
        }

        respuesta = self.client.get(
            "/api/consultar-clima/",
            {
                "fecha": fecha.isoformat(),
                "hora": "19:00"
            }
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertEqual(
            respuesta.json()["estado"],
            "desfavorable"
        )

        self.assertIn(
            "Datos meteorológicos de prueba",
            respuesta.json()["mensaje"]
        )

        post_simulado.assert_called_once()

class RegistroWebTests(TestCase):

    def setUp(self):
        self.url = reverse(register_view)

        self.datos = {
            "nombre": "Usuario de Prueba",
            "email": "prueba.registro@ejemplo.com",
            "password": "ClaveSegura123!"
        }

    def test_registro_web_correcto(self):
        datos = self.datos.copy()

        # Intentamos enviar privilegios no autorizados
        datos["rol"] = "administrador"
        datos["is_staff"] = "true"
        datos["is_superuser"] = "true"

        respuesta = self.client.post(
            self.url,
            datos
        )

        self.assertEqual(respuesta.status_code, 302)

        usuario = get_user_model().objects.get(
            username="prueba.registro@ejemplo.com"
        )

        self.assertTrue(
            usuario.check_password("ClaveSegura123!")
        )

        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)

    def test_rechaza_password_debil(self):
        datos = self.datos.copy()
        datos["password"] = "1234"

        respuesta = self.client.post(
            self.url,
            datos
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertFalse(
            get_user_model().objects.filter(
                username="prueba.registro@ejemplo.com"
            ).exists()
        )

    def test_rechaza_correo_duplicado(self):
        User = get_user_model()

        User.objects.create_user(
            username="prueba.registro@ejemplo.com",
            email="prueba.registro@ejemplo.com",
            password="ClaveSegura123!"
        )

        datos = self.datos.copy()
        datos["email"] = "PRUEBA.REGISTRO@EJEMPLO.COM"

        respuesta = self.client.post(
            self.url,
            datos
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_conserva_datos_tras_password_debil(self):
        datos = self.datos.copy()
        datos["password"] = "1234"

        respuesta = self.client.post(
            self.url,
            datos
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertContains(
            respuesta,
            'value="Usuario de Prueba"'
        )

        self.assertContains(
            respuesta,
            'value="prueba.registro@ejemplo.com"'
        )

        self.assertNotContains(
            respuesta,
            'value="1234"'
        )

class PoliticaClimaticaTests(SimpleTestCase):

    @override_settings(WEATHER_MODE="PRUEBAS")
    def test_pruebas_no_bloquea(self):
        resultado = debe_bloquear_por_clima(
            "desfavorable",
            fuente_real_verificada=False,
        )

        self.assertFalse(resultado)

    @override_settings(WEATHER_MODE="REAL_AVISO")
    def test_real_aviso_no_bloquea(self):
        resultado = debe_bloquear_por_clima(
            "desfavorable",
            fuente_real_verificada=True,
        )

        self.assertFalse(resultado)

    @override_settings(WEATHER_MODE="REAL_BLOQUEO")
    def test_real_bloqueo_rechaza_clima_desfavorable(self):
        resultado = debe_bloquear_por_clima(
            "desfavorable",
            fuente_real_verificada=True,
        )

        self.assertTrue(resultado)

    @override_settings(WEATHER_MODE="REAL_BLOQUEO")
    def test_fuente_no_verificada_no_bloquea(self):
        resultado = debe_bloquear_por_clima(
            "desfavorable",
            fuente_real_verificada=False,
        )

        self.assertFalse(resultado)

    @override_settings(WEATHER_MODE="REAL_BLOQUEO")
    def test_no_bloquea_por_datos_insuficientes(self):
        estados = [
            "favorable",
            "sin_datos",
            "fuera_de_rango",
            "error_servicio",
        ]

        for estado in estados:
            with self.subTest(estado=estado):
                resultado = debe_bloquear_por_clima(
                    estado,
                    fuente_real_verificada=True,
                )

                self.assertFalse(resultado)

class EvaluacionIntervaloClimaticoTests(SimpleTestCase):

    def setUp(self):
        zona = ZoneInfo("America/Managua")

        inicio = datetime(
            2026, 11, 20, 19, 0, tzinfo=zona
        )

        fin = datetime(
            2026, 11, 20, 21, 0, tzinfo=zona
        )

        self.datos = {
            "ts": [
                int(inicio.timestamp() * 1000),
                int(fin.timestamp() * 1000),
            ],
            "lclouds-surface": [10, 75],
            "mclouds-surface": [5, 15],
            "hclouds-surface": [5, 10],
            "past3hprecip-surface": [0, 0.5],
        }

    def test_detecta_clima_desfavorable_durante_intervalo(self):
        resultado = evaluar_datos_windy(
            self.datos,
            "2026-11-20",
            "19:00",
            "21:00",
        )

        self.assertEqual(
            resultado["estado"],
            "desfavorable"
        )

        self.assertEqual(
            resultado["nubosidad"],
            75
        )

        self.assertEqual(
            resultado["muestras_evaluadas"],
            2
        )

    def test_no_usa_pronostico_fuera_de_rango(self):
        resultado = evaluar_datos_windy(
            self.datos,
            "2026-11-20",
            "19:00",
            "23:00",
        )

        self.assertEqual(
            resultado["estado"],
            "fuera_de_rango"
        )

class ClienteWindyTests(SimpleTestCase):

    @override_settings(WINDY_API_KEY="clave_ficticia")
    @patch("core.weather_client.requests.post")
    def test_consulta_y_evalua_intervalo(self, mock_post):

        zona = ZoneInfo("America/Managua")

        inicio = datetime(
            2026, 11, 20, 19, 0, tzinfo=zona
        )

        fin = datetime(
            2026, 11, 20, 21, 0, tzinfo=zona
        )

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "ts": [
                int(inicio.timestamp() * 1000),
                int(fin.timestamp() * 1000),
            ],
            "lclouds-surface": [10, 75],
            "mclouds-surface": [5, 15],
            "hclouds-surface": [5, 10],
            "past3hprecip-surface": [0, 0.5],
        }

        resultado = consultar_condiciones_windy(
            "2026-11-20",
            "19:00",
            "21:00",
        )

        self.assertEqual(
            resultado["estado"],
            "desfavorable",
        )

        self.assertEqual(
            resultado["muestras_evaluadas"],
            2,
        )

        mock_post.assert_called_once()

        self.assertEqual(
            mock_post.call_args.kwargs["timeout"],
            10,
        )

    @override_settings(WINDY_API_KEY="clave_ficticia")
    @patch("core.weather_client.requests.post")
    def test_maneja_timeout_sin_crear_error_interno(self, mock_post):

        mock_post.side_effect = requests.exceptions.Timeout()

        resultado = consultar_condiciones_windy(
            "2026-11-20",
            "19:00",
            "21:00",
        )

        self.assertEqual(
            resultado["estado"],
            "error_servicio",
        )