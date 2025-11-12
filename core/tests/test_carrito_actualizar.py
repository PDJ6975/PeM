"""
Pruebas unitarias para la funcionalidad de actualizar cantidad de productos en el carrito.
Casos de prueba CP-28 a CP-30 del Plan de Pruebas.
"""

from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError

from core.models import Producto, Marca, Categoria, Cliente, Carrito, ItemCarrito
from core.services.carrito import (
    agregar_producto,
    modificar_cantidad,
    obtener_o_crear_carrito,
    obtener_carrito_detallado,
    CarritoError,
    StockInsuficienteError
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

    # --- CASOS LÍMITE ---

    def test_cp31_actualizar_cantidad_a_cero_elimina_producto(self):
        """
        CP-31: Actualizar cantidad a 0 (debe eliminar el producto del carrito)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=5
        )

        # Verificar que el producto está en el carrito
        self.assertTrue(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto1
        ).exists())
        self.assertEqual(carrito.total_items(), 5)

        # Actualizar cantidad a 0 debe lanzar ValidationError
        with self.assertRaises(ValidationError) as context:
            modificar_cantidad(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                nueva_cantidad=0
            )

        # Verificar mensaje de error
        self.assertIn('cantidad debe ser al menos 1', str(context.exception).lower())

        # Verificar que el producto sigue en el carrito con la cantidad original
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 5)

    def test_cp32_actualizar_cantidad_a_valor_negativo(self):
        """
        CP-32: Actualizar cantidad a valor negativo (debe rechazarse)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=3
        )

        # Intentar actualizar a cantidad negativa
        with self.assertRaises(ValidationError) as context:
            modificar_cantidad(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                nueva_cantidad=-2
            )

        # Verificar mensaje de error
        self.assertIn('cantidad debe ser al menos 1', str(context.exception).lower())

        # Verificar que la cantidad no cambió
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 3)

    def test_cp33_actualizar_cantidad_producto_inexistente_en_carrito(self):
        """
        CP-33: Actualizar cantidad de producto inexistente en el carrito (debe fallar)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar solo producto1
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=2
        )

        # Intentar actualizar producto2 que NO está en el carrito
        with self.assertRaises(CarritoError) as context:
            modificar_cantidad(
                carrito_id=carrito.id,
                producto_id=self.producto2.id,
                nueva_cantidad=5
            )

        # Verificar mensaje de error
        self.assertIn('no se encuentra en el carrito', str(context.exception).lower())

        # Verificar que solo está producto1 en el carrito
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 1)
        self.assertTrue(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto1
        ).exists())
        self.assertFalse(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto2
        ).exists())

    def test_cp34_actualizar_cantidad_mayor_a_stock_disponible(self):
        """
        CP-34: Actualizar cantidad a valor mayor que el stock disponible (debe rechazarse)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto con cantidad inicial de 3
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=3
        )

        # El producto1 tiene stock=10
        self.assertEqual(self.producto1.stock, 10)

        # Intentar actualizar a cantidad mayor que el stock
        with self.assertRaises(StockInsuficienteError) as context:
            modificar_cantidad(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                nueva_cantidad=15
            )

        # Verificar mensaje de error
        self.assertIn('stock insuficiente', str(context.exception).lower())
        self.assertIn('disponible: 10', str(context.exception).lower())

        # Verificar que la cantidad no cambió
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 3)

        # Verificar que actualizar al stock máximo sí funciona
        resultado = modificar_cantidad(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            nueva_cantidad=10
        )

        self.assertEqual(resultado['cantidad'], 10)
        item.refresh_from_db()
        self.assertEqual(item.cantidad, 10)

    def test_cp35_actualizar_producto_carrito_inexistente(self):
        """
        CP-35: Actualizar producto en carrito inexistente (debe fallar)
        """
        # Usar ID de carrito que no existe
        carrito_id_inexistente = 99999

        # Verificar que el carrito no existe
        self.assertFalse(Carrito.objects.filter(id=carrito_id_inexistente).exists())

        # Intentar actualizar cantidad en carrito inexistente
        with self.assertRaises(CarritoError) as context:
            modificar_cantidad(
                carrito_id=carrito_id_inexistente,
                producto_id=self.producto1.id,
                nueva_cantidad=5
            )

        # Verificar mensaje de error
        self.assertIn('no se encuentra en el carrito', str(context.exception).lower())

    def test_cp36_actualizar_producto_inexistente(self):
        """
        CP-36: Actualizar producto inexistente (debe fallar)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar un producto al carrito
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=2
        )

        # Usar ID de producto que no existe
        producto_id_inexistente = 99999

        # Verificar que el producto no existe
        self.assertFalse(Producto.objects.filter(id=producto_id_inexistente).exists())

        # Intentar actualizar producto inexistente
        with self.assertRaises(CarritoError) as context:
            modificar_cantidad(
                carrito_id=carrito.id,
                producto_id=producto_id_inexistente,
                nueva_cantidad=5
            )

        # Verificar mensaje de error
        self.assertIn('no se encuentra en el carrito', str(context.exception).lower())

        # Verificar que el carrito no cambió
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 1)
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 2)
