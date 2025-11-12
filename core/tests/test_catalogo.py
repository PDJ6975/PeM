from django.test import TestCase
from django.urls import reverse
from core.models import Marca, Categoria, Producto

class CatalogoViewTestCase(TestCase):
    def setUp(self):
        self.marca1, _ = Marca.objects.get_or_create(nombre="Kong")
        self.marca2, _ = Marca.objects.get_or_create(nombre="Trixie")

        self.categoria1, _ = Categoria.objects.get_or_create(nombre="Pelotas")
        self.categoria2, _ = Categoria.objects.get_or_create(nombre="Cuerdas")

        self.prod1 = Producto.objects.create(
            nombre="Pelota Kong",
            descripcion="Pelota resistente para perros",
            marca=self.marca1,
            categoria=self.categoria1,
            precio=10,
            stock=5,
            esta_disponible=True,
        )
        self.prod2 = Producto.objects.create(
            nombre="Mordedor fuerte",
            descripcion="Mordedor de goma Kong",
            marca=self.marca1,
            categoria=self.categoria2,
            precio=12,
            stock=5,
            esta_disponible=True,
        )
        self.prod3 = Producto.objects.create(
            nombre="Cuerda Trixie",
            descripcion="Cuerda de algodón Trixie",
            marca=self.marca2,
            categoria=self.categoria2,
            precio=8,
            stock=10,
            esta_disponible=True,
        )

    def test_busqueda_por_nombre(self):
        resp = self.client.get(reverse("catalogo"), {"q": "pelota"})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Pelota Kong", html)
        self.assertNotIn("Mordedor fuerte", html)
        self.assertNotIn("Cuerda Trixie", html)

    def test_filtrado_por_marca_y_categoria(self):
        resp = self.client.get(reverse("catalogo"), {
            "marca": self.marca1.id,
            "categoria": self.categoria1.id
        })
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Pelota Kong", html)
        self.assertNotIn("Cuerda Trixie", html)
        self.assertNotIn("Mordedor fuerte", html)
