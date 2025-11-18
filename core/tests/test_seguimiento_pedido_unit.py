from django.test import TestCase
from core.models import Pedido, Cliente
from core.services.pedido import PedidoService
from decimal import Decimal
import uuid


class PedidoServiceUnitTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create_user(
            email="cliente@correo.com",
            password="test1234",
            nombre="Test",
            apellidos="User"
        )

        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            subtotal=Decimal("50.00"),
            impuestos=Decimal("10.00"),
            coste_entrega=Decimal("5.00"),
            descuento=Decimal("0.00"),
            total=Decimal("65.00"),
            direccion_envio="Calle Ejemplo 123",
            telefono="+34123456789",
            estado="confirmado"
        )

    def test_view_order_returns_pedido_with_valid_email_and_code(self):
        """Debe devolver el pedido correcto si email y token son válidos"""
        result = PedidoService.view_order(
            email="cliente@correo.com",
            order_code=str(self.pedido.tracking_token)
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.pedido.id)

    def test_view_order_returns_none_if_email_invalid(self):
        """Debe devolver None si el email no coincide"""
        result = PedidoService.view_order(
            email="otro@correo.com",
            order_code=str(self.pedido.tracking_token)
        )
        self.assertIsNone(result)

    def test_view_order_returns_none_if_code_invalid(self):
        """Debe devolver None si el tracking_token no coincide"""
        result = PedidoService.view_order(
            email="cliente@correo.com",
            order_code=str(uuid.uuid4())
        )
        self.assertIsNone(result)

    def test_view_order_is_case_insensitive_for_email(self):
        """Debe funcionar aunque el email tenga mayúsculas"""
        result = PedidoService.view_order(
            email="CLIENTE@CORREO.COM",
            order_code=str(self.pedido.tracking_token)
        )
        self.assertIsNotNone(result)

    def test_view_order_raises_valueerror_if_missing_email(self):
        """Debe lanzar ValueError si falta el email"""
        with self.assertRaises(ValueError):
            PedidoService.view_order(email=None, order_code=str(self.pedido.tracking_token))

    def test_view_order_raises_valueerror_if_missing_code(self):
        """Debe lanzar ValueError si falta el código"""
        with self.assertRaises(ValueError):
            PedidoService.view_order(email="cliente@correo.com", order_code=None)
