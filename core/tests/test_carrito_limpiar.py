"""
Pruebas unitarias para la funcionalidad de limpiar carrito.
Casos de prueba CP-45 a CP-47 del Plan de Pruebas.
"""

from decimal import Decimal
from django.test import TestCase

from core.models import Producto, Marca, Categoria, Cliente, Carrito, ItemCarrito
from core.services.carrito import (
    agregar_producto,
    vaciar_carrito,
    obtener_o_crear_carrito,
    obtener_carrito_detallado
)


class LimpiarCarritoTestCase(TestCase):
    """Pruebas para la funcionalidad de limpiar/vaciar el carrito"""

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

    def test_cp45_limpiar_carrito_anonimo_con_productos(self):
        """
        CP-45: Limpiar carrito de usuario anónimo con productos
        """
        # Crear carrito anónimo
        carrito = obtener_o_crear_carrito(cliente=None)

        # Agregar varios productos
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto1.id, cantidad=2)
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto2.id, cantidad=3)
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto3.id, cantidad=1)

        # Verificar estado inicial
        resultado_antes = obtener_carrito_detallado(carrito.id)
        self.assertEqual(len(resultado_antes['items']), 3)
        self.assertEqual(resultado_antes['total_items'], 6)  # 2 + 3 + 1
        self.assertFalse(resultado_antes['esta_vacio'])
        self.assertGreater(resultado_antes['subtotal'], 0)

        # Contar items antes de limpiar
        items_count_antes = ItemCarrito.objects.filter(carrito=carrito).count()
        self.assertEqual(items_count_antes, 3)

        # Limpiar carrito
        resultado = vaciar_carrito(carrito_id=carrito.id)

        # Verificaciones del resultado
        self.assertIn('vaciado', resultado['mensaje'].lower())
        self.assertEqual(resultado['items_eliminados'], 3)

        # Verificar que todos los items fueron eliminados de la base de datos
        items_count_despues = ItemCarrito.objects.filter(carrito=carrito).count()
        self.assertEqual(items_count_despues, 0)

        # Verificar estado final del carrito
        resultado_despues = obtener_carrito_detallado(carrito.id)
        self.assertEqual(len(resultado_despues['items']), 0)
        self.assertEqual(resultado_despues['total_items'], 0)
        self.assertTrue(resultado_despues['esta_vacio'])
        self.assertEqual(resultado_despues['subtotal'], 0)

        # Verificar desde el modelo
        carrito.refresh_from_db()
        self.assertTrue(carrito.esta_vacio())
        self.assertEqual(carrito.total_items(), 0)
        self.assertEqual(carrito.subtotal(), 0)

    def test_cp46_limpiar_carrito_registrado_con_productos(self):
        """
        CP-46: Limpiar carrito de usuario registrado con productos
        """
        # Crear carrito de usuario registrado
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Verificar que el carrito pertenece al cliente
        self.assertEqual(carrito.cliente, self.cliente)

        # Agregar varios productos
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto1.id, cantidad=5)
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto2.id, cantidad=2)

        # Verificar estado inicial
        resultado_antes = obtener_carrito_detallado(carrito.id)
        self.assertEqual(len(resultado_antes['items']), 2)
        self.assertEqual(resultado_antes['total_items'], 7)  # 5 + 2
        self.assertFalse(resultado_antes['esta_vacio'])

        # Guardar subtotal inicial para verificación
        subtotal_inicial = resultado_antes['subtotal']
        self.assertGreater(subtotal_inicial, 0)

        # Limpiar carrito
        resultado = vaciar_carrito(carrito_id=carrito.id)

        # Verificaciones del resultado
        self.assertEqual(resultado['items_eliminados'], 2)
        self.assertIn('vaciado', resultado['mensaje'].lower())

        # Verificar que no hay items en la base de datos
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 0)

        # Verificar estado final
        resultado_despues = obtener_carrito_detallado(carrito.id)
        self.assertTrue(resultado_despues['esta_vacio'])
        self.assertEqual(resultado_despues['total_items'], 0)
        self.assertEqual(resultado_despues['subtotal'], 0)

        # Verificar que el carrito sigue existiendo y pertenece al cliente
        carrito.refresh_from_db()
        self.assertEqual(carrito.cliente, self.cliente)
        self.assertTrue(carrito.esta_vacio())

    def test_cp47_limpiar_carrito_vacio_operacion_idempotente(self):
        """
        CP-47: Limpiar carrito que ya está vacío (operación idempotente)
        """
        # Crear carrito vacío
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Verificar que el carrito está vacío
        self.assertTrue(carrito.esta_vacio())
        self.assertEqual(carrito.total_items(), 0)

        # Limpiar carrito vacío (operación idempotente)
        resultado = vaciar_carrito(carrito_id=carrito.id)

        # Verificaciones del resultado
        self.assertEqual(resultado['items_eliminados'], 0)
        self.assertIn('vaciado', resultado['mensaje'].lower())

        # Verificar que el carrito sigue vacío
        carrito.refresh_from_db()
        self.assertTrue(carrito.esta_vacio())
        self.assertEqual(carrito.total_items(), 0)
        self.assertEqual(carrito.subtotal(), 0)

        # Verificar que no hay items
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 0)

        # Limpiar por segunda vez (verificar que es idempotente)
        resultado2 = vaciar_carrito(carrito_id=carrito.id)

        # Verificar que la segunda operación también es exitosa
        self.assertEqual(resultado2['items_eliminados'], 0)
        self.assertTrue(carrito.esta_vacio())

    def test_limpiar_carrito_con_un_producto(self):
        """
        Limpiar carrito con un solo producto
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar un solo producto
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto1.id, cantidad=3)

        # Verificar estado inicial
        self.assertFalse(carrito.esta_vacio())
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 1)

        # Limpiar carrito
        resultado = vaciar_carrito(carrito_id=carrito.id)

        # Verificaciones
        self.assertEqual(resultado['items_eliminados'], 1)

        # Verificar que el carrito está vacío
        carrito.refresh_from_db()
        self.assertTrue(carrito.esta_vacio())
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 0)

    def test_limpiar_carrito_multiples_veces(self):
        """
        Limpiar carrito, agregar productos y volver a limpiar
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Primera ronda: agregar y limpiar
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto1.id, cantidad=2)
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto2.id, cantidad=1)

        resultado1 = vaciar_carrito(carrito_id=carrito.id)
        self.assertEqual(resultado1['items_eliminados'], 2)
        self.assertTrue(carrito.esta_vacio())

        # Segunda ronda: agregar productos diferentes y limpiar
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto3.id, cantidad=4)

        resultado2 = vaciar_carrito(carrito_id=carrito.id)
        self.assertEqual(resultado2['items_eliminados'], 1)
        self.assertTrue(carrito.esta_vacio())

        # Tercera ronda: limpiar carrito vacío
        resultado3 = vaciar_carrito(carrito_id=carrito.id)
        self.assertEqual(resultado3['items_eliminados'], 0)
        self.assertTrue(carrito.esta_vacio())
