"""
Pruebas unitarias para la funcionalidad de obtener carrito.
Casos de prueba CP-15 a CP-22 del Plan de Pruebas.
"""

from decimal import Decimal
from django.test import TestCase

from core.models import Producto, Marca, Categoria, Cliente, Carrito, ItemCarrito
from core.services.carrito import (
    agregar_producto,
    obtener_o_crear_carrito,
    obtener_carrito_detallado
)


class ObtenerCarritoTestCase(TestCase):
    """Pruebas para la funcionalidad de obtener información del carrito"""

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

        self.producto3 = Producto.objects.create(
            nombre="Juguete Test 3",
            descripcion="Descripción del juguete 3",
            precio=Decimal("10.00"),
            stock=8,
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

    def test_cp15_obtener_carrito_vacio_anonimo(self):
        """
        CP-15: Obtener carrito vacío de usuario anónimo
        """
        # Crear carrito anónimo vacío
        carrito = obtener_o_crear_carrito(cliente=None)

        # Obtener información del carrito
        resultado = obtener_carrito_detallado(carrito.id)

        # Verificaciones
        self.assertEqual(resultado['carrito_id'], carrito.id)
        self.assertEqual(resultado['items'], [])
        self.assertEqual(resultado['total_items'], 0)
        self.assertEqual(resultado['subtotal'], 0)
        self.assertTrue(resultado['esta_vacio'])

    def test_cp16_obtener_carrito_vacio_registrado(self):
        """
        CP-16: Obtener carrito vacío de usuario registrado
        """
        # Crear carrito de usuario registrado vacío
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Verificar que el carrito pertenece al cliente
        self.assertEqual(carrito.cliente, self.cliente)

        # Obtener información del carrito
        resultado = obtener_carrito_detallado(carrito.id)

        # Verificaciones
        self.assertEqual(resultado['carrito_id'], carrito.id)
        self.assertEqual(resultado['items'], [])
        self.assertEqual(resultado['total_items'], 0)
        self.assertEqual(resultado['subtotal'], 0)
        self.assertTrue(resultado['esta_vacio'])

    def test_cp17_obtener_carrito_un_producto_anonimo(self):
        """
        CP-17: Obtener carrito con un solo producto de usuario anónimo
        """
        # Crear carrito anónimo
        carrito = obtener_o_crear_carrito(cliente=None)

        # Agregar un producto
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=2
        )

        # Obtener información del carrito
        resultado = obtener_carrito_detallado(carrito.id)

        # Verificaciones
        self.assertEqual(resultado['carrito_id'], carrito.id)
        self.assertEqual(len(resultado['items']), 1)
        self.assertEqual(resultado['total_items'], 2)
        self.assertEqual(resultado['subtotal'], Decimal("31.98"))  # 15.99 * 2
        self.assertFalse(resultado['esta_vacio'])

        # Verificar el item
        item = resultado['items'][0]
        self.assertEqual(item['producto']['id'], self.producto1.id)
        self.assertEqual(item['producto']['nombre'], self.producto1.nombre)
        self.assertEqual(item['producto']['marca'], self.marca.nombre)
        self.assertEqual(item['producto']['precio_unitario'], Decimal("15.99"))
        self.assertEqual(item['cantidad'], 2)
        self.assertEqual(item['subtotal'], Decimal("31.98"))

    def test_cp18_obtener_carrito_un_producto_registrado(self):
        """
        CP-18: Obtener carrito con un solo producto de usuario registrado
        """
        # Crear carrito de usuario registrado
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar un producto
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=3
        )

        # Obtener información del carrito
        resultado = obtener_carrito_detallado(carrito.id)

        # Verificaciones
        self.assertEqual(resultado['carrito_id'], carrito.id)
        self.assertEqual(len(resultado['items']), 1)
        self.assertEqual(resultado['total_items'], 3)
        self.assertEqual(resultado['subtotal'], Decimal("47.97"))  # 15.99 * 3
        self.assertFalse(resultado['esta_vacio'])

        # Verificar el item
        item = resultado['items'][0]
        self.assertEqual(item['producto']['id'], self.producto1.id)
        self.assertEqual(item['cantidad'], 3)
        self.assertEqual(item['subtotal'], Decimal("47.97"))

    def test_cp19_obtener_carrito_multiples_productos(self):
        """
        CP-19: Obtener carrito con múltiples productos diferentes
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar tres productos diferentes
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto1.id, cantidad=2)
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto2.id, cantidad=1)
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto3.id, cantidad=4)

        # Obtener información del carrito
        resultado = obtener_carrito_detallado(carrito.id)

        # Verificaciones generales
        self.assertEqual(len(resultado['items']), 3)
        self.assertEqual(resultado['total_items'], 7)  # 2 + 1 + 4
        self.assertFalse(resultado['esta_vacio'])

        # Verificar que todos los productos están presentes
        productos_ids = [item['producto']['id'] for item in resultado['items']]
        self.assertIn(self.producto1.id, productos_ids)
        self.assertIn(self.producto2.id, productos_ids)
        self.assertIn(self.producto3.id, productos_ids)

        # Verificar cada item específicamente
        items_por_producto = {item['producto']['id']: item for item in resultado['items']}

        # Producto 1: 2 unidades x 15.99
        item1 = items_por_producto[self.producto1.id]
        self.assertEqual(item1['cantidad'], 2)
        self.assertEqual(item1['subtotal'], Decimal("31.98"))

        # Producto 2: 1 unidad x 25.50
        item2 = items_por_producto[self.producto2.id]
        self.assertEqual(item2['cantidad'], 1)
        self.assertEqual(item2['subtotal'], Decimal("25.50"))

        # Producto 3: 4 unidades x 10.00
        item3 = items_por_producto[self.producto3.id]
        self.assertEqual(item3['cantidad'], 4)
        self.assertEqual(item3['subtotal'], Decimal("40.00"))

    def test_cp20_calculo_subtotal_un_producto(self):
        """
        CP-20: Verificar cálculo correcto del subtotal con un producto
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto con cantidad específica
        cantidad = 5
        precio_esperado = self.producto1.precio * cantidad

        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=cantidad
        )

        # Obtener información del carrito
        resultado = obtener_carrito_detallado(carrito.id)

        # Verificar cálculo del subtotal
        self.assertEqual(resultado['subtotal'], precio_esperado)
        self.assertEqual(resultado['subtotal'], Decimal("79.95"))  # 15.99 * 5

        # Verificar que el subtotal del item coincide
        item = resultado['items'][0]
        self.assertEqual(item['subtotal'], precio_esperado)

        # Verificar también desde el modelo directamente
        carrito.refresh_from_db()
        self.assertEqual(carrito.subtotal(), precio_esperado)

    def test_cp21_calculo_subtotal_multiples_productos(self):
        """
        CP-21: Verificar cálculo correcto del subtotal con múltiples productos
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar múltiples productos con diferentes cantidades
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto1.id, cantidad=2)  # 15.99 * 2 = 31.98
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto2.id, cantidad=3)  # 25.50 * 3 = 76.50
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto3.id, cantidad=1)  # 10.00 * 1 = 10.00

        # Calcular subtotal esperado manualmente
        subtotal_esperado = (
            (self.producto1.precio * 2) +
            (self.producto2.precio * 3) +
            (self.producto3.precio * 1)
        )
        self.assertEqual(subtotal_esperado, Decimal("118.48"))

        # Obtener información del carrito
        resultado = obtener_carrito_detallado(carrito.id)

        # Verificar cálculo del subtotal total
        self.assertEqual(resultado['subtotal'], subtotal_esperado)
        self.assertEqual(resultado['subtotal'], Decimal("118.48"))

        # Verificar que la suma de subtotales individuales coincide
        suma_subtotales = sum(item['subtotal'] for item in resultado['items'])
        self.assertEqual(suma_subtotales, subtotal_esperado)

        # Verificar desde el modelo directamente
        carrito.refresh_from_db()
        self.assertEqual(carrito.subtotal(), subtotal_esperado)

    def test_cp22_calculo_total_items(self):
        """
        CP-22: Verificar cálculo correcto del total_items
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Caso 1: Carrito vacío
        resultado = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado['total_items'], 0)

        # Caso 2: Un producto con múltiples unidades
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto1.id, cantidad=5)
        resultado = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado['total_items'], 5)

        # Caso 3: Múltiples productos con diferentes cantidades
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto2.id, cantidad=3)
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto3.id, cantidad=2)

        resultado = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado['total_items'], 10)  # 5 + 3 + 2 = 10

        # Verificar desde el modelo directamente
        carrito.refresh_from_db()
        self.assertEqual(carrito.total_items(), 10)

        # Verificar que total_items es la suma de cantidades, no el número de productos
        self.assertEqual(len(resultado['items']), 3)  # 3 productos diferentes
        self.assertEqual(resultado['total_items'], 10)  # 10 items en total
