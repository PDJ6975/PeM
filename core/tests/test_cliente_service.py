from django.test import TestCase
from core.services.cliente import register, login
from core.models.cliente import Cliente


class ClienteServiceTest(TestCase):

    def setUp(self):
        # Crea cliente base
        self.cliente = register(
            email="test@example.com",
            password="securepassword",
            nombre="Test",
            apellidos="User"
        )

    def test_register_success(self):
        self.assertIsInstance(self.cliente, Cliente)
        self.assertEqual(self.cliente.email, "test@example.com")
        self.assertEqual(self.cliente.nombre, "Test")
        self.assertEqual(self.cliente.apellidos, "User")
        self.assertTrue(self.cliente.check_password("securepassword"))

    def test_register_missing_email(self):
        with self.assertRaises(ValueError) as context:
            register(
                email="",
                password="securepassword",
                nombre="Test",
                apellidos="User"
            )
        self.assertEqual(str(context.exception), "El email es obligatorio")

    def test_register_existing_email(self):
        with self.assertRaises(ValueError) as context:
            register(
                email="test@example.com",
                password="securepassword",
                nombre="Test",
                apellidos="User"
            )
        self.assertEqual(str(context.exception), "Ya existe un cliente con este email")

    def test_login_success(self):
        cliente = login(email="test@example.com", password="securepassword")
        self.assertIsNotNone(cliente)
        self.assertEqual(cliente.email, "test@example.com")

    def test_login_invalid_credentials(self):
        cliente = login(email="test@example.com", password="wrongpassword")
        self.assertIsNone(cliente)

    def test_login_missing_email(self):
        cliente = login(email="", password="securepassword")
        self.assertIsNone(cliente)

    def test_login_missing_password(self):
        cliente = login(email="test@example.com", password="")
        self.assertIsNone(cliente)
