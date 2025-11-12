# core/tests/test_api.py
from django.test import TestCase
from django.urls import reverse
from core.models import Marca, Categoria, Producto
from uuid import uuid4

class ApiProductosTestCase(TestCase):
    def setUp(self):
        self.marca, _ = Marca.objects.get_or_create(nombre="Kong")
        self.categoria, _ = Categoria.objects.get_or_create(nombre="Pelotas")

        # Término único para evitar choques con datos semilla
        self.qterm = f"xq_{uuid4().hex[:8]}"

        # Producto que debe coincidir
        Producto.objects.create(
            nombre=f"Pelota {self.qterm}",
            descripcion=f"Pelota para perros {self.qterm}",
            marca=self.marca,
            categoria=self.categoria,
            precio=10,
            stock=5,
            esta_disponible=True,
        )

        # Producto que NO debe coincidir
        Producto.objects.create(
            nombre="Hueso mordedor",
            descripcion="Hueso resistente para perros",
            marca=self.marca,
            categoria=self.categoria,
            precio=5,
            stock=5,
            esta_disponible=True,
        )

    def test_api_filtra_por_q(self):
        url = reverse("api_productos")
        resp = self.client.get(url, {"q": self.qterm})
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertIn("count", data)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["nombre"], f"Pelota {self.qterm}")
