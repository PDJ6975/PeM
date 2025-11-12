"""
Pruebas unitarias para la funcionalidad de migración de carrito.
Casos de prueba CP-51 a CP-52 del Plan de Pruebas.
"""

from decimal import Decimal
from django.test import TestCase

from core.models import Producto, Marca, Categoria, Cliente, Carrito, ItemCarrito
from core.services.carrito import (
    agregar_producto,
    migrar_carrito,
    obtener_o_crear_carrito,
    obtener_carrito_detallado
)


class MigracionCarritoTestCase(TestCase):
    """Pruebas para la funcionalidad de migración de carrito anónimo a registrado"""

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

    def test_cp51_migrar_carrito_con_productos_a_usuario_con_carrito_vacio(self):
        """
        CP-51: Migrar carrito de sesión con productos a usuario recién registrado (carrito vacío)
        """
        # Crear carrito anónimo con productos
        carrito_anonimo = obtener_o_crear_carrito(cliente=None)
        self.assertIsNone(carrito_anonimo.cliente)

        # Agregar productos al carrito anónimo
        agregar_producto(carrito_id=carrito_anonimo.id, producto_id=self.producto1.id, cantidad=2)
        agregar_producto(carrito_id=carrito_anonimo.id, producto_id=self.producto2.id, cantidad=3)

        # Verificar estado inicial del carrito anónimo
        carrito_anonimo_detalle = obtener_carrito_detallado(carrito_anonimo.id)
        self.assertEqual(carrito_anonimo_detalle['total_items'], 5)  # 2 + 3
        self.assertEqual(len(carrito_anonimo_detalle['items']), 2)

        # Guardar ID del carrito anónimo
        carrito_anonimo_id = carrito_anonimo.id

        # Migrar carrito a usuario registrado
        resultado = migrar_carrito(
            carrito_anonimo_id=carrito_anonimo_id,
            cliente=self.cliente
        )

        # Verificaciones del resultado
        self.assertIn('migrado', resultado['mensaje'].lower())
        self.assertEqual(resultado['items_migrados'], 2)  # 2 productos migrados
        self.assertEqual(resultado['items_combinados'], 0)  # Ninguno combinado (carrito destino vacío)

        # Verificar que el carrito anónimo fue eliminado
        self.assertFalse(Carrito.objects.filter(id=carrito_anonimo_id).exists())

        # Verificar que el cliente tiene ahora un carrito con los productos
        carrito_cliente = Carrito.objects.get(cliente=self.cliente)
        self.assertEqual(carrito_cliente.id, resultado['carrito_id'])

        # Verificar contenido del carrito del cliente
        carrito_cliente_detalle = obtener_carrito_detallado(carrito_cliente.id)
        self.assertEqual(carrito_cliente_detalle['total_items'], 5)  # 2 + 3
        self.assertEqual(len(carrito_cliente_detalle['items']), 2)

        # Verificar productos específicos
        productos_ids = [item['producto']['id'] for item in carrito_cliente_detalle['items']]
        self.assertIn(self.producto1.id, productos_ids)
        self.assertIn(self.producto2.id, productos_ids)

        # Verificar cantidades
        items_por_producto = {item['producto']['id']: item for item in carrito_cliente_detalle['items']}
        self.assertEqual(items_por_producto[self.producto1.id]['cantidad'], 2)
        self.assertEqual(items_por_producto[self.producto2.id]['cantidad'], 3)

        # Verificar subtotal
        subtotal_esperado = (self.producto1.precio * 2) + (self.producto2.precio * 3)
        self.assertEqual(carrito_cliente_detalle['subtotal'], subtotal_esperado)

    def test_cp52_migrar_carrito_vacio_a_usuario_registrado(self):
        """
        CP-52: Migrar carrito vacío de sesión a usuario registrado
        """
        # Crear carrito anónimo vacío
        carrito_anonimo = obtener_o_crear_carrito(cliente=None)
        self.assertIsNone(carrito_anonimo.cliente)
        self.assertTrue(carrito_anonimo.esta_vacio())

        # Guardar ID del carrito anónimo
        carrito_anonimo_id = carrito_anonimo.id

        # Migrar carrito vacío
        resultado = migrar_carrito(
            carrito_anonimo_id=carrito_anonimo_id,
            cliente=self.cliente
        )

        # Verificaciones del resultado
        self.assertEqual(resultado['items_migrados'], 0)  # Sin items para migrar
        self.assertEqual(resultado['items_combinados'], 0)  # Sin items para combinar
        self.assertIn('migrado', resultado['mensaje'].lower())

        # Verificar que el carrito anónimo fue eliminado
        self.assertFalse(Carrito.objects.filter(id=carrito_anonimo_id).exists())

        # Verificar que el cliente tiene un carrito (vacío)
        carrito_cliente = Carrito.objects.get(cliente=self.cliente)
        self.assertEqual(carrito_cliente.id, resultado['carrito_id'])
        self.assertTrue(carrito_cliente.esta_vacio())

        # Verificar detalle del carrito
        carrito_cliente_detalle = obtener_carrito_detallado(carrito_cliente.id)
        self.assertEqual(carrito_cliente_detalle['total_items'], 0)
        self.assertEqual(len(carrito_cliente_detalle['items']), 0)
        self.assertTrue(carrito_cliente_detalle['esta_vacio'])

    def test_migracion_carrito_un_solo_producto(self):
        """
        Migrar carrito con un solo producto
        """
        # Crear carrito anónimo con un producto
        carrito_anonimo = obtener_o_crear_carrito(cliente=None)
        agregar_producto(carrito_id=carrito_anonimo.id, producto_id=self.producto1.id, cantidad=4)

        # Verificar estado inicial
        self.assertEqual(carrito_anonimo.total_items(), 4)

        # Migrar
        resultado = migrar_carrito(
            carrito_anonimo_id=carrito_anonimo.id,
            cliente=self.cliente
        )

        # Verificaciones
        self.assertEqual(resultado['items_migrados'], 1)
        self.assertEqual(resultado['items_combinados'], 0)

        # Verificar carrito del cliente
        carrito_cliente = Carrito.objects.get(cliente=self.cliente)
        self.assertEqual(carrito_cliente.total_items(), 4)

        # Verificar que el producto está en el carrito
        item = ItemCarrito.objects.get(carrito=carrito_cliente, producto=self.producto1)
        self.assertEqual(item.cantidad, 4)

    def test_migracion_preserva_cantidades_correctas(self):
        """
        Verificar que las cantidades se preservan correctamente durante la migración
        """
        # Crear carrito anónimo con cantidades específicas
        carrito_anonimo = obtener_o_crear_carrito(cliente=None)
        agregar_producto(carrito_id=carrito_anonimo.id, producto_id=self.producto1.id, cantidad=7)
        agregar_producto(carrito_id=carrito_anonimo.id, producto_id=self.producto2.id, cantidad=2)
        agregar_producto(carrito_id=carrito_anonimo.id, producto_id=self.producto3.id, cantidad=5)

        # Guardar cantidades para verificación
        cantidad_producto1 = 7
        cantidad_producto2 = 2
        cantidad_producto3 = 5

        # Migrar
        resultado = migrar_carrito(
            carrito_anonimo_id=carrito_anonimo.id,
            cliente=self.cliente
        )

        # Verificar que se migraron todos los productos
        self.assertEqual(resultado['items_migrados'], 3)

        # Verificar cantidades en el carrito del cliente
        carrito_cliente = Carrito.objects.get(cliente=self.cliente)

        item1 = ItemCarrito.objects.get(carrito=carrito_cliente, producto=self.producto1)
        item2 = ItemCarrito.objects.get(carrito=carrito_cliente, producto=self.producto2)
        item3 = ItemCarrito.objects.get(carrito=carrito_cliente, producto=self.producto3)

        self.assertEqual(item1.cantidad, cantidad_producto1)
        self.assertEqual(item2.cantidad, cantidad_producto2)
        self.assertEqual(item3.cantidad, cantidad_producto3)

        # Verificar total
        self.assertEqual(carrito_cliente.total_items(), 14)  # 7 + 2 + 5
