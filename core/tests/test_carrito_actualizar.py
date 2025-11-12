"""
Pruebas unitarias para la funcionalidad de actualizar cantidad de productos en el carrito.
Casos de prueba CP-28 a CP-30 del Plan de Pruebas.
"""

from decimal import Decimal
from django.test import TestCase

from core.models import Producto, Marca, Categoria, Cliente, Carrito, ItemCarrito
from core.services.carrito import (
    agregar_producto,
    modificar_cantidad,
    obtener_o_crear_carrito,
    obtener_carrito_detallado
)


class ActualizarCantidadTestCase(TestCase):
    """Pruebas para la funcionalidad de actualizar cantidad de productos"""

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

    def test_cp28_actualizar_cantidad_a_valor_mayor(self):
        """
        CP-28: Actualizar cantidad de producto existente a valor mayor
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto con cantidad inicial de 2
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=2
        )

        # Verificar cantidad inicial
        resultado_inicial = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado_inicial['total_items'], 2)
        self.assertEqual(resultado_inicial['subtotal'], Decimal("31.98"))  # 15.99 * 2

        # Actualizar cantidad a valor mayor (5)
        resultado = modificar_cantidad(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            nueva_cantidad=5
        )

        # Verificaciones del resultado
        self.assertEqual(resultado['cantidad'], 5)
        self.assertEqual(resultado['subtotal'], Decimal("79.95"))  # 15.99 * 5
        self.assertEqual(resultado['mensaje'], 'Cantidad actualizada')

        # Verificar en el carrito
        resultado_actualizado = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado_actualizado['total_items'], 5)
        self.assertEqual(resultado_actualizado['subtotal'], Decimal("79.95"))

        # Verificar en el item directamente
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 5)

    def test_cp29_actualizar_cantidad_a_valor_menor(self):
        """
        CP-29: Actualizar cantidad de producto existente a valor menor
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto con cantidad inicial de 5
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=5
        )

        # Verificar cantidad inicial
        resultado_inicial = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado_inicial['total_items'], 5)
        self.assertEqual(resultado_inicial['subtotal'], Decimal("79.95"))  # 15.99 * 5

        # Actualizar cantidad a valor menor (2)
        resultado = modificar_cantidad(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            nueva_cantidad=2
        )

        # Verificaciones del resultado
        self.assertEqual(resultado['cantidad'], 2)
        self.assertEqual(resultado['subtotal'], Decimal("31.98"))  # 15.99 * 2
        self.assertEqual(resultado['mensaje'], 'Cantidad actualizada')

        # Verificar en el carrito
        resultado_actualizado = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado_actualizado['total_items'], 2)
        self.assertEqual(resultado_actualizado['subtotal'], Decimal("31.98"))

        # Verificar en el item directamente
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 2)

    def test_cp30_actualizar_cantidad_a_minimo_valido(self):
        """
        CP-30: Actualizar cantidad a 1 (mínimo válido)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto con cantidad inicial de 7
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=7
        )

        # Verificar cantidad inicial
        resultado_inicial = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado_inicial['total_items'], 7)

        # Actualizar cantidad al mínimo válido (1)
        resultado = modificar_cantidad(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            nueva_cantidad=1
        )

        # Verificaciones del resultado
        self.assertEqual(resultado['cantidad'], 1)
        self.assertEqual(resultado['subtotal'], Decimal("15.99"))  # 15.99 * 1
        self.assertEqual(resultado['mensaje'], 'Cantidad actualizada')

        # Verificar en el carrito
        resultado_actualizado = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado_actualizado['total_items'], 1)
        self.assertEqual(resultado_actualizado['subtotal'], Decimal("15.99"))

        # Verificar en el item directamente
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 1)

        # Verificar que el item aún existe en el carrito (no fue eliminado)
        self.assertTrue(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto1
        ).exists())

    def test_actualizar_cantidad_con_multiples_productos(self):
        """
        Verificar que actualizar un producto no afecta a otros productos
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar dos productos diferentes
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto1.id, cantidad=3)
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto2.id, cantidad=2)

        # Verificar estado inicial
        resultado_inicial = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado_inicial['total_items'], 5)  # 3 + 2

        # Actualizar solo el primer producto
        modificar_cantidad(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            nueva_cantidad=5
        )

        # Verificar que solo cambió el producto actualizado
        resultado_final = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado_final['total_items'], 7)  # 5 + 2

        # Verificar cantidades individuales
        item1 = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        item2 = ItemCarrito.objects.get(carrito=carrito, producto=self.producto2)

        self.assertEqual(item1.cantidad, 5)  # Actualizado
        self.assertEqual(item2.cantidad, 2)  # Sin cambios
