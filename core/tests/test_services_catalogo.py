# core/tests/test_services_catalogo.py
from django.test import TestCase
from decimal import Decimal
import uuid

from core.models import Marca, Categoria, Producto
from core.services.catalogo import buscar_productos


class CatalogoServiceUnitTests(TestCase):
    def setUp(self):
        # Usamos nombres únicos para no chocar con datos sembrados por migraciones
        self.pref = f"T-{uuid.uuid4().hex[:8]}"

        self.marca1 = Marca.objects.create(nombre=f"{self.pref}-Kong")
        self.marca2 = Marca.objects.create(nombre=f"{self.pref}-Trixie")

        self.cat_juguetes = Categoria.objects.create(
            nombre=f"{self.pref}-Juguetes", descripcion="Juguetes"
        )
        self.cat_comida = Categoria.objects.create(
            nombre=f"{self.pref}-Comida", descripcion="Comida"
        )

        # Productos base (todos disponibles)
        self.p1 = Producto.objects.create(
            nombre=f"{self.pref}-Pelota", descripcion="Pelota resistente",
            marca=self.marca1, categoria=self.cat_juguetes,
            precio=Decimal("9.99"), stock=10, esta_disponible=True, genero="ambos",
        )
        self.p2 = Producto.objects.create(
            nombre=f"{self.pref}-Mordedor", descripcion="Juguete de goma",
            marca=self.marca1, categoria=self.cat_juguetes,
            precio=Decimal("5.00"), stock=5, esta_disponible=True, genero="perro",
        )
        self.p3 = Producto.objects.create(
            nombre=f"{self.pref}-Comida Premium", descripcion="Alimento seco",
            marca=self.marca2, categoria=self.cat_comida,
            precio=Decimal("20.00"), stock=8, esta_disponible=True, genero="gato",
        )
        # No disponible (para probar filtro de disponibilidad)
        self.p4_no_dispo = Producto.objects.create(
            nombre=f"{self.pref}-Descatalogado", descripcion="Fuera de stock",
            marca=self.marca2, categoria=self.cat_comida,
            precio=Decimal("12.00"), stock=0, esta_disponible=False, genero="ambos",
        )

    def test_buscar_solo_devuelve_disponibles(self):
        qs = buscar_productos()
        ids = list(qs.values_list("id", flat=True))
        self.assertIn(self.p1.id, ids)
        self.assertIn(self.p2.id, ids)
        self.assertIn(self.p3.id, ids)
        self.assertNotIn(self.p4_no_dispo.id, ids)  # excluido por no disponible

    def test_buscar_por_texto_en_nombre(self):
        qs = buscar_productos(q="Pelota")
        self.assertIn(self.p1, qs)
        self.assertNotIn(self.p2, qs)
        self.assertNotIn(self.p3, qs)

    def test_buscar_por_texto_en_descripcion(self):
        qs = buscar_productos(q="goma")
        self.assertIn(self.p2, qs)       # "Juguete de goma"
        self.assertNotIn(self.p1, qs)
        self.assertNotIn(self.p3, qs)

    def test_buscar_por_texto_en_marca(self):
        # La marca aparece en el filtro (marca__nombre__icontains)
        qs = buscar_productos(q=self.marca2.nombre.split("-")[-1])  # parte final del nombre
        self.assertIn(self.p3, qs)
        self.assertNotIn(self.p1, qs)
        self.assertNotIn(self.p2, qs)

    def test_filtra_por_marca(self):
        qs = buscar_productos(marca_id=self.marca1.id)
        self.assertIn(self.p1, qs)
        self.assertIn(self.p2, qs)
        self.assertNotIn(self.p3, qs)

    def test_filtra_por_categoria(self):
        qs = buscar_productos(categoria_id=self.cat_comida.id)
        self.assertIn(self.p3, qs)
        self.assertNotIn(self.p1, qs)
        self.assertNotIn(self.p2, qs)

    def test_filtra_por_genero(self):
        qs_perro = buscar_productos(genero="perro")
        self.assertIn(self.p2, qs_perro)     # genero=perro
        self.assertNotIn(self.p1, qs_perro)  # ambos != perro
        self.assertNotIn(self.p3, qs_perro)  # gato != perro

        qs_ambos = buscar_productos(genero="ambos")
        self.assertIn(self.p1, qs_ambos)
        self.assertNotIn(self.p2, qs_ambos)
        self.assertNotIn(self.p3, qs_ambos)

    def test_orden_por_nombre_por_defecto(self):
        # buscar_productos() termina con .order_by("nombre")
        qs = list(buscar_productos().values_list("nombre", flat=True))
        # Asegura orden lexicográfico por nombre
        self.assertEqual(qs, sorted(qs))
