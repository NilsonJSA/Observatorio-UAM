from django.test import TestCase

# Create your tests here.

from datetime import timedelta, time

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import ReservaObservacion


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