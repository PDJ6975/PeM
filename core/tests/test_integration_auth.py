from django.test import TestCase, Client
from django.urls import reverse
from core.models.cliente import Cliente

class AuthIntegrationTest(TestCase):
    """Pruebas de integración para los endpoints de autenticación."""

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('api_auth_register')  # /api/auth/register/
        self.login_url = reverse('api_auth_login')        # /api/auth/login/
        self.valid_user_data = {
            "email": "integration@example.com",
            "password": "securepassword",
            "nombre": "Integration",
            "apellidos": "Test",
        }

    def test_register_success(self):
        """Debe registrar un usuario correctamente."""
        response = self.client.post(
            self.register_url,
            data=self.valid_user_data,
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("success", response.json())
        self.assertTrue(Cliente.objects.filter(email="integration@example.com").exists())

    def test_register_existing_email(self):
        """Debe devolver error si el email ya está registrado."""
        Cliente.objects.create_user(**self.valid_user_data)
        response = self.client.post(
            self.register_url,
            data=self.valid_user_data,
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_register_missing_email(self):
        """Debe fallar si falta el email."""
        data = self.valid_user_data.copy()
        data["email"] = ""
        response = self.client.post(
            self.register_url,
            data=data,
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_register_missing_password(self):
        """Debe fallar si falta la contraseña."""
        data = self.valid_user_data.copy()
        data["password"] = ""
        response = self.client.post(
            self.register_url,
            data=data,
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_login_success(self):
        """Debe permitir iniciar sesión con credenciales válidas."""
        Cliente.objects.create_user(**self.valid_user_data)
        response = self.client.post(
            self.login_url,
            data={
                "email": self.valid_user_data["email"],
                "password": self.valid_user_data["password"],
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn("success", json_data)
        self.assertIn("usuario", json_data)

    def test_login_invalid_credentials(self):
        """Debe fallar con credenciales incorrectas."""
        Cliente.objects.create_user(**self.valid_user_data)
        response = self.client.post(
            self.login_url,
            data={
                "email": self.valid_user_data["email"],
                "password": "wrongpassword",
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    def test_login_missing_fields(self):
        """Debe fallar si faltan email o password."""
        response = self.client.post(
            self.login_url,
            data={"email": "", "password": ""},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
