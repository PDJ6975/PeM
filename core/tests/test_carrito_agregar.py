"""
Pruebas unitarias para la funcionalidad de agregar productos al carrito.
Casos de prueba CP-01 a CP-05 del Plan de Pruebas.
"""

from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError

from core.models import Producto, Marca, Categoria, Cliente, Carrito, ItemCarrito
from core.services.carrito import (
    agregar_producto,
    obtener_o_crear_carrito,
    CarritoError,
    ProductoNoDisponibleError,
    StockInsuficienteError
)


class AgregarProductoTestCase(TestCase):
    """Pruebas para la funcionalidad de agregar productos al carrito"""

    def setUp(self):
        """Preparar datos de prueba antes de cada test"""
        # Crear marca y categoría
        self.marca = Marca.objects.create(
            nombre="Marca Test"
        )
        self.categoria = Categoria.objects.create(
            nombre="Categoría Test",
            descripcion="Descripción de prueba"
        )

        # Crear productos de prueba
        self.producto1 = Producto.objects.create(
            nombre="Juguete Test 1",
            descripcion="Descripción del juguete 1",
            precio=Decimal("15.99"),
            stock=10,
            esta_disponible=True,
            marca=self.marca,
            categoria=self.categoria
        )

        self.producto2 = Producto.objects.create(
            nombre="Juguete Test 2",
            descripcion="Descripción del juguete 2",
            precio=Decimal("25.50"),
            stock=5,
            esta_disponible=True,
            marca=self.marca,
            categoria=self.categoria
        )

        # Crear cliente de prueba
        self.cliente = Cliente.objects.create_user(
            username="test_user",
            email="test@example.com",
            password="password123",
            nombre="Test",
            apellidos="User"
        )

    def test_cp01_agregar_producto_carrito_vacio_anonimo(self):
        """
        CP-01: Agregar un producto con cantidad válida (1) a carrito vacío de usuario anónimo
        """
        # Crear carrito anónimo (sin cliente)
        carrito = obtener_o_crear_carrito(cliente=None)

        # Verificar que el carrito está vacío
        self.assertTrue(carrito.esta_vacio())
        self.assertEqual(carrito.total_items(), 0)

        # Agregar producto
        resultado = agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=1
        )

        # Verificaciones
        self.assertEqual(resultado['producto']['id'], self.producto1.id)
        self.assertEqual(resultado['producto']['nombre'], self.producto1.nombre)
        self.assertEqual(resultado['cantidad'], 1)
        self.assertEqual(resultado['subtotal'], Decimal("15.99"))
        self.assertEqual(resultado['mensaje'], 'Producto agregado')

        # Verificar que el carrito ya no está vacío
        carrito.refresh_from_db()
        self.assertFalse(carrito.esta_vacio())
        self.assertEqual(carrito.total_items(), 1)
        self.assertEqual(carrito.subtotal(), Decimal("15.99"))

        # Verificar que el item se creó en la base de datos
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 1)

    def test_cp02_agregar_producto_carrito_vacio_registrado(self):
        """
        CP-02: Agregar un producto con cantidad válida (1) a carrito vacío de usuario registrado
        """
        # Crear carrito de usuario registrado
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Verificar que el carrito está asociado al cliente
        self.assertEqual(carrito.cliente, self.cliente)
        self.assertTrue(carrito.esta_vacio())

        # Agregar producto
        resultado = agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=1
        )

        # Verificaciones
        self.assertEqual(resultado['producto']['id'], self.producto1.id)
        self.assertEqual(resultado['cantidad'], 1)
        self.assertEqual(resultado['subtotal'], Decimal("15.99"))
        self.assertEqual(resultado['mensaje'], 'Producto agregado')

        # Verificar el carrito
        carrito.refresh_from_db()
        self.assertFalse(carrito.esta_vacio())
        self.assertEqual(carrito.total_items(), 1)

        # Verificar que el item pertenece al carrito del cliente
        item = ItemCarrito.objects.get(carrito=carrito)
        self.assertEqual(item.producto, self.producto1)
        self.assertEqual(item.cantidad, 1)

    def test_cp03_agregar_multiples_unidades_carrito_vacio(self):
        """
        CP-03: Agregar múltiples unidades de un producto (cantidad > 1) a carrito vacío
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar 3 unidades del producto
        resultado = agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=3
        )

        # Verificaciones
        self.assertEqual(resultado['cantidad'], 3)
        self.assertEqual(resultado['subtotal'], Decimal("15.99") * 3)
        self.assertEqual(resultado['subtotal'], Decimal("47.97"))
        self.assertEqual(resultado['mensaje'], 'Producto agregado')

        # Verificar el carrito
        carrito.refresh_from_db()
        self.assertEqual(carrito.total_items(), 3)
        self.assertEqual(carrito.subtotal(), Decimal("47.97"))

        # Verificar el item
        item = ItemCarrito.objects.get(carrito=carrito)
        self.assertEqual(item.cantidad, 3)

    def test_cp04_agregar_mismo_producto_dos_veces_actualiza_cantidad(self):
        """
        CP-04: Agregar el mismo producto dos veces (debe actualizar cantidad, no duplicar)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Primera vez: agregar 2 unidades
        resultado1 = agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=2
        )

        self.assertEqual(resultado1['cantidad'], 2)
        self.assertEqual(resultado1['mensaje'], 'Producto agregado')

        # Verificar que solo hay un item en el carrito
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 1)

        # Segunda vez: agregar 3 unidades más del mismo producto
        resultado2 = agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=3
        )

        # Verificaciones de la segunda operación
        self.assertEqual(resultado2['cantidad'], 5)  # 2 + 3 = 5
        self.assertEqual(resultado2['subtotal'], Decimal("15.99") * 5)
        self.assertEqual(resultado2['mensaje'], 'Cantidad actualizada')

        # Verificar que sigue habiendo solo un item (no se duplicó)
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 1)

        # Verificar totales del carrito
        carrito.refresh_from_db()
        self.assertEqual(carrito.total_items(), 5)
        self.assertEqual(carrito.subtotal(), Decimal("79.95"))

        # Verificar el item directamente
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 5)

    def test_cp05_agregar_diferentes_productos_mismo_carrito(self):
        """
        CP-05: Agregar diferentes productos al mismo carrito
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar primer producto (2 unidades)
        resultado1 = agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=2
        )

        # Verificaciones del primer producto
        self.assertEqual(resultado1['producto']['id'], self.producto1.id)
        self.assertEqual(resultado1['cantidad'], 2)
        self.assertEqual(resultado1['subtotal'], Decimal("31.98"))

        # Agregar segundo producto (3 unidades)
        resultado2 = agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto2.id,
            cantidad=3
        )

        # Verificaciones del segundo producto
        self.assertEqual(resultado2['producto']['id'], self.producto2.id)
        self.assertEqual(resultado2['cantidad'], 3)
        self.assertEqual(resultado2['subtotal'], Decimal("76.50"))

        # Verificar que hay 2 items diferentes en el carrito
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 2)

        # Verificar totales del carrito
        carrito.refresh_from_db()
        self.assertEqual(carrito.total_items(), 5)  # 2 + 3 = 5 items en total
        self.assertEqual(carrito.subtotal(), Decimal("108.48"))  # 31.98 + 76.50

        # Verificar ambos items en el carrito
        item1 = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item1.cantidad, 2)

        item2 = ItemCarrito.objects.get(carrito=carrito, producto=self.producto2)
        self.assertEqual(item2.cantidad, 3)
