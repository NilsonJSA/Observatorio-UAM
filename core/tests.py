from django.test import TestCase

# Create your tests here.

from datetime import timedelta, time

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import ReservaObservacion

from rest_framework.authtoken.models import Token

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