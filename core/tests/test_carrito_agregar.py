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

    # --- CASOS LÍMITE ---

    def test_cp06_agregar_producto_cantidad_cero(self):
        """
        CP-06: Agregar producto con cantidad = 0 (debe rechazarse)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Intentar agregar producto con cantidad 0
        with self.assertRaises(ValidationError) as context:
            agregar_producto(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                cantidad=0
            )

        # Verificar mensaje de error
        self.assertIn('cantidad debe ser al menos 1', str(context.exception).lower())

        # Verificar que el carrito sigue vacío
        self.assertTrue(carrito.esta_vacio())
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 0)

    def test_cp07_agregar_producto_cantidad_negativa(self):
        """
        CP-07: Agregar producto con cantidad negativa (debe rechazarse)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Intentar agregar producto con cantidad negativa
        with self.assertRaises(ValidationError) as context:
            agregar_producto(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                cantidad=-5
            )

        # Verificar mensaje de error
        self.assertIn('cantidad debe ser al menos 1', str(context.exception).lower())

        # Verificar que el carrito sigue vacío
        self.assertTrue(carrito.esta_vacio())
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 0)

    def test_cp08_agregar_producto_cantidad_mayor_a_stock(self):
        """
        CP-08: Agregar producto con cantidad mayor al stock disponible (debe rechazarse)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # El producto1 tiene stock=10
        self.assertEqual(self.producto1.stock, 10)

        # Intentar agregar más del stock disponible
        with self.assertRaises(StockInsuficienteError) as context:
            agregar_producto(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                cantidad=15
            )

        # Verificar mensaje de error
        self.assertIn('stock insuficiente', str(context.exception).lower())
        self.assertIn('disponible: 10', str(context.exception).lower())
        self.assertIn('solicitado: 15', str(context.exception).lower())

        # Verificar que el carrito sigue vacío
        self.assertTrue(carrito.esta_vacio())

    def test_cp09_agregar_producto_agotado(self):
        """
        CP-09: Agregar producto agotado (stock = 0) (debe rechazarse)
        """
        # Crear producto agotado
        producto_agotado = Producto.objects.create(
            nombre="Juguete Agotado",
            descripcion="Sin stock",
            precio=Decimal("20.00"),
            stock=0,
            esta_disponible=True,
            marca=self.marca,
            categoria=self.categoria
        )

        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Intentar agregar producto agotado
        with self.assertRaises(ProductoNoDisponibleError) as context:
            agregar_producto(
                carrito_id=carrito.id,
                producto_id=producto_agotado.id,
                cantidad=1
            )

        # Verificar mensaje de error
        self.assertIn('no está disponible', str(context.exception).lower())

        # Verificar que el carrito sigue vacío
        self.assertTrue(carrito.esta_vacio())

    def test_cp10_agregar_producto_inexistente(self):
        """
        CP-10: Agregar producto inexistente (producto_id no válido)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Usar ID de producto que no existe
        producto_id_inexistente = 99999

        # Verificar que el producto no existe
        self.assertFalse(Producto.objects.filter(id=producto_id_inexistente).exists())

        # Intentar agregar producto inexistente
        with self.assertRaises(CarritoError) as context:
            agregar_producto(
                carrito_id=carrito.id,
                producto_id=producto_id_inexistente,
                cantidad=1
            )

        # Verificar mensaje de error
        self.assertIn('producto', str(context.exception).lower())
        self.assertIn('no encontrado', str(context.exception).lower())

        # Verificar que el carrito sigue vacío
        self.assertTrue(carrito.esta_vacio())

    def test_cp11_agregar_producto_carrito_inexistente(self):
        """
        CP-11: Agregar producto a carrito inexistente (debe fallar)
        """
        # Usar ID de carrito que no existe
        carrito_id_inexistente = 99999

        # Verificar que el carrito no existe
        self.assertFalse(Carrito.objects.filter(id=carrito_id_inexistente).exists())

        # Intentar agregar producto a carrito inexistente
        with self.assertRaises(CarritoError) as context:
            agregar_producto(
                carrito_id=carrito_id_inexistente,
                producto_id=self.producto1.id,
                cantidad=1
            )

        # Verificar mensaje de error
        self.assertIn('carrito', str(context.exception).lower())
        self.assertIn('no encontrado', str(context.exception).lower())

    # --- CASOS DE VALIDACIÓN DE STOCK ---

    def test_cp13_agregar_producto_stock_justo_suficiente(self):
        """
        CP-13: Agregar producto que tiene stock justo suficiente (cantidad = stock)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # El producto1 tiene stock=10
        self.assertEqual(self.producto1.stock, 10)

        # Agregar exactamente el stock disponible
        resultado = agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=10
        )

        # Verificaciones
        self.assertEqual(resultado['cantidad'], 10)
        self.assertEqual(resultado['subtotal'], Decimal("15.99") * 10)

        # Verificar en el carrito
        carrito.refresh_from_db()
        self.assertEqual(carrito.total_items(), 10)

        # Verificar que el producto está en el carrito
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 10)

    def test_cp14_agregar_mas_unidades_agota_stock(self):
        """
        CP-14: Intentar agregar más unidades cuando ya hay items en el carrito que agotan el stock
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # El producto1 tiene stock=10
        self.assertEqual(self.producto1.stock, 10)

        # Agregar 7 unidades primero
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=7
        )

        # Verificar que hay 7 unidades en el carrito
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 7)

        # Intentar agregar 5 más (total sería 12, excede el stock de 10)
        with self.assertRaises(StockInsuficienteError) as context:
            agregar_producto(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                cantidad=5
            )

        # Verificar mensaje de error
        self.assertIn('stock insuficiente', str(context.exception).lower())
        self.assertIn('disponible: 10', str(context.exception).lower())
        self.assertIn('solicitado: 12', str(context.exception).lower())

        # Verificar que la cantidad en el carrito no cambió
        item.refresh_from_db()
        self.assertEqual(item.cantidad, 7)

        # Verificar que agregar 3 más sí funciona (total 10 = stock)
        resultado = agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=3
        )

        self.assertEqual(resultado['cantidad'], 10)
        self.assertEqual(resultado['mensaje'], 'Cantidad actualizada')
