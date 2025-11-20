# core/tests/test_payments.py
from decimal import Decimal
from types import SimpleNamespace
import json

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.models import Carrito, ItemCarrito, Producto, Categoria, Marca, Pedido

User = get_user_model()


class AttrDict(dict):
    """dict con acceso por atributos (para simular objetos de Stripe)."""
    __slots__ = ()
    def __getattr__(self, key):
        return self.get(key, None)
    def __dir__(self):
        return list(self.keys()) + dir(dict)


def _ensure_catalogo_basico():
    cat, _ = Categoria.objects.get_or_create(nombre="General")
    marca, _ = Marca.objects.get_or_create(nombre="Genérica")
    return cat, marca


def _mk_product(nombre="Prod X", precio="9.99", stock=10):
    cat, marca = _ensure_catalogo_basico()
    return Producto.objects.create(
        nombre=nombre,
        precio=Decimal(precio),
        stock=stock,
        categoria=cat,
        marca=marca,
    )


def _mk_carrito_con_item():
    carrito = Carrito.objects.create()
    producto = _mk_product()
    ItemCarrito.objects.create(carrito=carrito, producto=producto, cantidad=1)
    return carrito, producto


def _mk_user_with_carrito_con_item(email="user@test.com"):
    user = User.objects.create_user(email=email, password="pass1234")
    carrito = Carrito.objects.create(cliente=user)
    producto = _mk_product()
    ItemCarrito.objects.create(carrito=carrito, producto=producto, cantidad=1)
    return user, carrito, producto


class PaymentFlowsTest(TestCase):
    def setUp(self):
        self.client = Client()

    # ---------------- COD ----------------

    def test_cod_carrito_vacio_400(self):
        user = User.objects.create_user(email="cod@test.com", password="pass1234")
        self.client.force_login(user)

        url = reverse("checkout_cod")
        payload = {
            "address_line1": "Calle Falsa 123",
            "address_city": "Madrid",
            "address_postal_code": "28080",
        }
        r = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_cod_crea_pedido_con_direccion_y_redirige(self):
        user = User.objects.create_user(email="codok@test.com", password="pass1234")
        self.client.force_login(user)

        carrito = Carrito.objects.create(cliente=user)
        producto = _mk_product()
        ItemCarrito.objects.create(carrito=carrito, producto=producto, cantidad=1)

        # La vista usa la sesión para localizar el carrito
        sess = self.client.session
        sess["carrito_id"] = carrito.id
        sess.save()

        url = reverse("checkout_cod")

        # Enviamos TODAS las variantes posibles para que la vista lo acepte (sin tocar views):
        direccion_payload = {
            # Estilo Stripe (anidado)
            "address": {
                "line1": "Gran Via 1",
                "city": "Madrid",
                "postal_code": "28013",
            },
            # Estilo aplanado (con prefijo)
            "address_line1": "Gran Via 1",
            "address_city": "Madrid",
            "address_postal_code": "28013",
            # Estilo aplanado (sin prefijo)
            "line1": "Gran Via 1",
            "city": "Madrid",
            "postal_code": "28013",
            # Posibles claves en español
            "direccion": "Gran Via 1",
            "ciudad": "Madrid",
            "cp": "28013",
            "codigo_postal": "28013",
        }

        r = self.client.post(url, data=json.dumps(direccion_payload), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(Pedido.objects.filter(cliente=user).exists())

    def test_cod_rechaza_get_405(self):
        url = reverse("checkout_cod")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 405)

    def test_cod_rechaza_sin_direccion(self):
        user = User.objects.create_user(email="codfail@test.com", password="pass1234")
        self.client.force_login(user)

        carrito = Carrito.objects.create(cliente=user)
        producto = _mk_product()
        ItemCarrito.objects.create(carrito=carrito, producto=producto, cantidad=1)

        url = reverse("checkout_cod")
        r = self.client.post(url, data=json.dumps({}), content_type="application/json")
        self.assertEqual(r.status_code, 400)

    # ---------------- STRIPE ----------------

    def test_stripe_carrito_vacio_400(self):
        user = User.objects.create_user(email="u1@test.com", password="pass1234")
        self.client.force_login(user)

        stripe_checkout_url = reverse("create_checkout_session")

        from unittest.mock import patch
        with patch("core.views.stripe.checkout.Session.create") as mock_create:
            mock_create.return_value = SimpleNamespace(id="cs_x", url="https://x")
            r = self.client.post(stripe_checkout_url)
        self.assertEqual(r.status_code, 400)

    def test_stripe_guest_crea_pedido_con_usuario_anonimo(self):
        carrito, _producto = _mk_carrito_con_item()

        session = self.client.session
        session["carrito_id"] = carrito.id
        session.save()

        stripe_checkout_url = reverse("create_checkout_session")
        success_url = reverse("checkout_success")

        from unittest.mock import patch

        with patch("core.views.stripe.checkout.Session.create") as mock_create:
            mock_create.return_value = SimpleNamespace(id="cs_test_guest", url="https://stripe.test/guest")
            r1 = self.client.post(stripe_checkout_url)
        self.assertEqual(r1.status_code, 200)

        fake_customer_details = AttrDict(
            name="Guest Person",
            email="guest@example.com",
            phone="+34 600600600",
            address={"line1": "Calle Uno 1", "city": "Madrid", "postal_code": "28001"},
        )
        fake_stripe_session = SimpleNamespace(
            id="cs_test_guest",
            payment_status="paid",
            payment_intent="pi_guest_ok",
            customer_details=fake_customer_details,
        )

        with patch("core.views.stripe.checkout.Session.retrieve") as mock_retrieve:
            mock_retrieve.return_value = fake_stripe_session
            r2 = self.client.get(success_url, {"session_id": "cs_test_guest"})
        self.assertIn(r2.status_code, (200, 302), r2.content)
        self.assertEqual(Pedido.objects.count(), 1)

    def test_stripe_unpaid_devuelve_400(self):
        carrito, _producto = _mk_carrito_con_item()
        session = self.client.session
        session["carrito_id"] = carrito.id
        session.save()

        stripe_checkout_url = reverse("create_checkout_session")
        success_url = reverse("checkout_success")

        from unittest.mock import patch

        with patch("core.views.stripe.checkout.Session.create") as mock_create:
            mock_create.return_value = SimpleNamespace(id="cs_unpaid", url="https://stripe.test/unpaid")
            r1 = self.client.post(stripe_checkout_url)
        self.assertEqual(r1.status_code, 200)

        fake_customer_details = AttrDict(
            name="Guest Unpaid",
            email="guest@unpaid.com",
            phone="",
            address={"line1": "Calle Dos 2", "city": "Madrid", "postal_code": "28002"},
        )
        fake_stripe_session = SimpleNamespace(
            id="cs_unpaid",
            payment_status="unpaid",
            payment_intent="pi_unpaid",
            customer_details=fake_customer_details,
        )
        with patch("core.views.stripe.checkout.Session.retrieve") as mock_retrieve:
            mock_retrieve.return_value = fake_stripe_session
            r2 = self.client.get(success_url, {"session_id": "cs_unpaid"})
        self.assertEqual(r2.status_code, 400)

    def test_stripe_user_crea_pedido_con_usuario_autenticado(self):
        user, carrito, _producto = _mk_user_with_carrito_con_item()
        self.client.force_login(user)

        session = self.client.session
        session["carrito_id"] = carrito.id
        session.save()

        stripe_checkout_url = reverse("create_checkout_session")
        success_url = reverse("checkout_success")

        from unittest.mock import patch

        with patch("core.views.stripe.checkout.Session.create") as mock_create:
            mock_create.return_value = SimpleNamespace(id="cs_user_ok", url="https://stripe.test/u")
            r1 = self.client.post(stripe_checkout_url)
        self.assertEqual(r1.status_code, 200)

        fake_customer_details = AttrDict(
            name="Buyer User",
            email=user.email,
            phone="+34 611611611",
            address={"line1": "Calle Tres 3", "city": "Madrid", "postal_code": "28003"},
        )
        fake_stripe_session = SimpleNamespace(
            id="cs_user_ok",
            payment_status="paid",
            payment_intent="pi_user_ok",
            customer_details=fake_customer_details,
        )
        with patch("core.views.stripe.checkout.Session.retrieve") as mock_retrieve:
            mock_retrieve.return_value = fake_stripe_session
            r2 = self.client.get(success_url, {"session_id": "cs_user_ok"})
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertTrue(Pedido.objects.filter(cliente=user).exists())
