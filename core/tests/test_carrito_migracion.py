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
    obtener_carrito_detallado,
    CarritoError
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

    # --- CASOS LÍMITE ---

    def test_cp53_migrar_carrito_a_usuario_con_productos_existentes(self):
        """
        CP-53: Migrar carrito de sesión a usuario que ya tiene productos en su carrito (debe combinar)
        """
        # Crear carrito del usuario con productos
        carrito_usuario = obtener_o_crear_carrito(cliente=self.cliente)
        agregar_producto(carrito_id=carrito_usuario.id, producto_id=self.producto1.id, cantidad=3)
        agregar_producto(carrito_id=carrito_usuario.id, producto_id=self.producto2.id, cantidad=1)

        # Verificar estado inicial del carrito del usuario
        self.assertEqual(carrito_usuario.total_items(), 4)  # 3 + 1

        # Crear carrito anónimo con productos diferentes y uno común
        carrito_anonimo = obtener_o_crear_carrito(cliente=None)
        agregar_producto(carrito_id=carrito_anonimo.id, producto_id=self.producto2.id, cantidad=2)  # Producto común
        agregar_producto(carrito_id=carrito_anonimo.id, producto_id=self.producto3.id, cantidad=4)  # Producto nuevo

        # Migrar
        resultado = migrar_carrito(
            carrito_anonimo_id=carrito_anonimo.id,
            cliente=self.cliente
        )

        # Verificaciones
        self.assertEqual(resultado['items_migrados'], 1)  # producto3 es nuevo
        self.assertEqual(resultado['items_combinados'], 1)  # producto2 se combina

        # Verificar carrito final del usuario
        carrito_usuario.refresh_from_db()
        items_finales = obtener_carrito_detallado(carrito_usuario.id)

        # Producto1: sin cambios (3 unidades)
        item1 = ItemCarrito.objects.get(carrito=carrito_usuario, producto=self.producto1)
        self.assertEqual(item1.cantidad, 3)

        # Producto2: combinado (1 + 2 = 3 unidades)
        item2 = ItemCarrito.objects.get(carrito=carrito_usuario, producto=self.producto2)
        self.assertEqual(item2.cantidad, 3)

        # Producto3: migrado (4 unidades)
        item3 = ItemCarrito.objects.get(carrito=carrito_usuario, producto=self.producto3)
        self.assertEqual(item3.cantidad, 4)

        # Verificar total de items
        self.assertEqual(carrito_usuario.total_items(), 10)  # 3 + 3 + 4

        # Verificar que el carrito anónimo fue eliminado
        self.assertFalse(Carrito.objects.filter(id=carrito_anonimo.id).exists())

    def test_cp54_migrar_carrito_productos_duplicados_con_limite_stock(self):
        """
        CP-54: Migrar carrito con productos duplicados (mismo producto en sesión y en usuario)
        con validación de stock
        """
        # Crear carrito del usuario con producto1
        carrito_usuario = obtener_o_crear_carrito(cliente=self.cliente)
        agregar_producto(carrito_id=carrito_usuario.id, producto_id=self.producto1.id, cantidad=6)

        # Crear carrito anónimo con el mismo producto
        carrito_anonimo = obtener_o_crear_carrito(cliente=None)
        agregar_producto(carrito_id=carrito_anonimo.id, producto_id=self.producto1.id, cantidad=3)

        # El producto1 tiene stock=10
        self.assertEqual(self.producto1.stock, 10)

        # Migrar (debe combinar: 6 + 3 = 9, dentro del stock)
        resultado = migrar_carrito(
            carrito_anonimo_id=carrito_anonimo.id,
            cliente=self.cliente
        )

        # Verificaciones
        self.assertEqual(resultado['items_migrados'], 0)
        self.assertEqual(resultado['items_combinados'], 1)

        # Verificar cantidad combinada
        item = ItemCarrito.objects.get(carrito=carrito_usuario, producto=self.producto1)
        self.assertEqual(item.cantidad, 9)  # 6 + 3

    def test_cp54_migrar_productos_duplicados_excede_stock(self):
        """
        CP-54 variante: Migrar con productos duplicados que excederían el stock
        (debe ajustar al stock máximo)
        """
        # Crear carrito del usuario con producto1
        carrito_usuario = obtener_o_crear_carrito(cliente=self.cliente)
        agregar_producto(carrito_id=carrito_usuario.id, producto_id=self.producto1.id, cantidad=7)

        # Crear carrito anónimo con el mismo producto
        carrito_anonimo = obtener_o_crear_carrito(cliente=None)
        agregar_producto(carrito_id=carrito_anonimo.id, producto_id=self.producto1.id, cantidad=5)

        # El producto1 tiene stock=10
        # 7 + 5 = 12, excede el stock de 10
        self.assertEqual(self.producto1.stock, 10)

        # Migrar (debe ajustar a stock máximo de 10)
        resultado = migrar_carrito(
            carrito_anonimo_id=carrito_anonimo.id,
            cliente=self.cliente
        )

        # Verificaciones
        self.assertEqual(resultado['items_combinados'], 1)

        # Verificar que se ajustó al stock máximo
        item = ItemCarrito.objects.get(carrito=carrito_usuario, producto=self.producto1)
        self.assertEqual(item.cantidad, 10)  # Ajustado al stock máximo, no 12

    def test_cp55_migrar_desde_carrito_inexistente(self):
        """
        CP-55: Migrar desde carrito inexistente (debe fallar)
        """
        # Usar ID de carrito que no existe
        carrito_id_inexistente = 99999

        # Verificar que el carrito no existe
        self.assertFalse(Carrito.objects.filter(id=carrito_id_inexistente).exists())

        # Intentar migrar desde carrito inexistente
        with self.assertRaises(CarritoError) as context:
            migrar_carrito(
                carrito_anonimo_id=carrito_id_inexistente,
                cliente=self.cliente
            )

        # Verificar mensaje de error
        self.assertIn('no encontrado', str(context.exception).lower())

    def test_cp56_migrar_a_cliente_con_carrito_no_anonimo(self):
        """
        CP-56: Intentar migrar un carrito que ya tiene cliente asociado (debe fallar)
        """
        # Crear otro cliente
        otro_cliente = Cliente.objects.create_user(
            email="otro@example.com",
            password="password123",
            nombre="Otro",
            apellidos="Usuario"
        )

        # Crear carrito asociado a otro_cliente
        carrito_otro = obtener_o_crear_carrito(cliente=otro_cliente)
        agregar_producto(carrito_id=carrito_otro.id, producto_id=self.producto1.id, cantidad=2)

        # Intentar migrar ese carrito a self.cliente (debe fallar porque ya tiene cliente)
        with self.assertRaises(CarritoError) as context:
            migrar_carrito(
                carrito_anonimo_id=carrito_otro.id,
                cliente=self.cliente
            )

        # Verificar mensaje de error
        self.assertIn('ya tiene un cliente', str(context.exception).lower())

        # Verificar que el carrito original no cambió
        carrito_otro.refresh_from_db()
        self.assertEqual(carrito_otro.cliente, otro_cliente)
