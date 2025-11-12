"""
Pruebas unitarias para la funcionalidad de eliminar productos del carrito.
Casos de prueba CP-37 a CP-40 del Plan de Pruebas.
"""

from decimal import Decimal
from django.test import TestCase

from core.models import Producto, Marca, Categoria, Cliente, Carrito, ItemCarrito
from core.services.carrito import (
    agregar_producto,
    eliminar_producto,
    obtener_o_crear_carrito,
    obtener_carrito_detallado,
    CarritoError
)


class EliminarProductoTestCase(TestCase):
    """Pruebas para la funcionalidad de eliminar productos del carrito"""

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

    def test_cp37_eliminar_producto_carrito_anonimo(self):
        """
        CP-37: Eliminar producto existente de carrito de usuario anónimo
        """
        # Crear carrito anónimo
        carrito = obtener_o_crear_carrito(cliente=None)

        # Agregar producto
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=3
        )

        # Verificar que el producto está en el carrito
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 1)
        resultado_antes = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado_antes['total_items'], 3)
        self.assertFalse(resultado_antes['esta_vacio'])

        # Eliminar producto
        resultado = eliminar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id
        )

        # Verificaciones del resultado
        self.assertEqual(resultado['producto_id'], self.producto1.id)
        self.assertIn('eliminado', resultado['mensaje'].lower())

        # Verificar que el producto ya no está en el carrito
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 0)
        self.assertFalse(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto1
        ).exists())

        # Verificar estado del carrito
        resultado_despues = obtener_carrito_detallado(carrito.id)
        self.assertEqual(resultado_despues['total_items'], 0)
        self.assertTrue(resultado_despues['esta_vacio'])

    def test_cp38_eliminar_producto_carrito_registrado(self):
        """
        CP-38: Eliminar producto existente de carrito de usuario registrado
        """
        # Crear carrito de usuario registrado
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Verificar que el carrito pertenece al cliente
        self.assertEqual(carrito.cliente, self.cliente)

        # Agregar producto
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=2
        )

        # Verificar que el producto está en el carrito
        self.assertTrue(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto1
        ).exists())

        # Eliminar producto
        resultado = eliminar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id
        )

        # Verificaciones del resultado
        self.assertEqual(resultado['producto_id'], self.producto1.id)
        self.assertIn(self.producto1.nombre, resultado['mensaje'])

        # Verificar que el producto ya no está en el carrito
        self.assertFalse(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto1
        ).exists())

        # Verificar que el carrito está vacío
        carrito.refresh_from_db()
        self.assertTrue(carrito.esta_vacio())

    def test_cp39_eliminar_unico_producto_carrito_queda_vacio(self):
        """
        CP-39: Eliminar el único producto del carrito (carrito queda vacío)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar solo un producto
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=5
        )

        # Verificar estado inicial
        resultado_antes = obtener_carrito_detallado(carrito.id)
        self.assertEqual(len(resultado_antes['items']), 1)
        self.assertEqual(resultado_antes['total_items'], 5)
        self.assertFalse(resultado_antes['esta_vacio'])

        # Eliminar el único producto
        eliminar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id
        )

        # Verificar que el carrito quedó vacío
        resultado_despues = obtener_carrito_detallado(carrito.id)
        self.assertEqual(len(resultado_despues['items']), 0)
        self.assertEqual(resultado_despues['total_items'], 0)
        self.assertTrue(resultado_despues['esta_vacio'])
        self.assertEqual(resultado_despues['subtotal'], 0)

        # Verificar que no hay items en la base de datos
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 0)

        # Verificar desde el modelo
        carrito.refresh_from_db()
        self.assertTrue(carrito.esta_vacio())
        self.assertEqual(carrito.total_items(), 0)
        self.assertEqual(carrito.subtotal(), 0)

    def test_cp40_eliminar_producto_carrito_con_varios_productos(self):
        """
        CP-40: Eliminar un producto de un carrito con varios productos
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar tres productos diferentes
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto1.id, cantidad=2)
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto2.id, cantidad=3)
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto3.id, cantidad=1)

        # Verificar estado inicial
        resultado_antes = obtener_carrito_detallado(carrito.id)
        self.assertEqual(len(resultado_antes['items']), 3)
        self.assertEqual(resultado_antes['total_items'], 6)  # 2 + 3 + 1
        subtotal_inicial = resultado_antes['subtotal']

        # Calcular subtotal esperado después de eliminar producto2
        subtotal_esperado = (self.producto1.precio * 2) + (self.producto3.precio * 1)
        self.assertEqual(subtotal_esperado, Decimal("41.98"))  # 31.98 + 10.00

        # Eliminar producto2 (el del medio)
        resultado = eliminar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto2.id
        )

        # Verificaciones del resultado
        self.assertEqual(resultado['producto_id'], self.producto2.id)

        # Verificar que solo se eliminó el producto2
        self.assertFalse(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto2
        ).exists())

        # Verificar que los otros productos siguen en el carrito
        self.assertTrue(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto1
        ).exists())
        self.assertTrue(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto3
        ).exists())

        # Verificar estado final
        resultado_despues = obtener_carrito_detallado(carrito.id)
        self.assertEqual(len(resultado_despues['items']), 2)  # Quedan 2 productos
        self.assertEqual(resultado_despues['total_items'], 3)  # 2 + 1 = 3 items
        self.assertEqual(resultado_despues['subtotal'], subtotal_esperado)
        self.assertFalse(resultado_despues['esta_vacio'])

        # Verificar cantidades de los productos restantes
        item1 = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        item3 = ItemCarrito.objects.get(carrito=carrito, producto=self.producto3)

        self.assertEqual(item1.cantidad, 2)  # Sin cambios
        self.assertEqual(item3.cantidad, 1)  # Sin cambios

        # Verificar que el subtotal disminuyó correctamente
        subtotal_producto2_eliminado = self.producto2.precio * 3  # 25.50 * 3 = 76.50
        self.assertEqual(
            resultado_antes['subtotal'] - resultado_despues['subtotal'],
            subtotal_producto2_eliminado
        )

    # --- CASOS LÍMITE ---

    def test_cp41_eliminar_producto_inexistente_operacion_idempotente(self):
        """
        CP-41: Eliminar producto inexistente del carrito (no debe fallar, operación idempotente)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar solo producto1
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=2
        )

        # Verificar estado inicial
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 1)

        # Intentar eliminar producto2 que NO está en el carrito
        # Debe lanzar CarritoError según la implementación actual
        with self.assertRaises(CarritoError) as context:
            eliminar_producto(
                carrito_id=carrito.id,
                producto_id=self.producto2.id
            )

        # Verificar mensaje de error
        self.assertIn('no se encuentra en el carrito', str(context.exception).lower())

        # Verificar que el carrito no cambió
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 1)
        self.assertTrue(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto1
        ).exists())

    def test_cp42_eliminar_producto_de_carrito_vacio(self):
        """
        CP-42: Eliminar producto de carrito vacío (no debe fallar)
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Verificar que el carrito está vacío
        self.assertTrue(carrito.esta_vacio())
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 0)

        # Intentar eliminar producto de carrito vacío
        # Debe lanzar CarritoError según la implementación actual
        with self.assertRaises(CarritoError) as context:
            eliminar_producto(
                carrito_id=carrito.id,
                producto_id=self.producto1.id
            )

        # Verificar mensaje de error
        self.assertIn('no se encuentra en el carrito', str(context.exception).lower())

        # Verificar que el carrito sigue vacío
        self.assertTrue(carrito.esta_vacio())
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 0)

    def test_cp43_eliminar_producto_carrito_inexistente(self):
        """
        CP-43: Eliminar producto de carrito inexistente (debe fallar)
        """
        # Usar ID de carrito que no existe
        carrito_id_inexistente = 99999

        # Verificar que el carrito no existe
        self.assertFalse(Carrito.objects.filter(id=carrito_id_inexistente).exists())

        # Intentar eliminar producto de carrito inexistente
        with self.assertRaises(CarritoError) as context:
            eliminar_producto(
                carrito_id=carrito_id_inexistente,
                producto_id=self.producto1.id
            )

        # Verificar mensaje de error
        self.assertIn('no se encuentra en el carrito', str(context.exception).lower())

    def test_cp44_eliminar_producto_inexistente_del_sistema(self):
        """
        CP-44: Eliminar producto que no existe en el sistema
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar un producto al carrito
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=3
        )

        # Usar ID de producto que no existe en el sistema
        producto_id_inexistente = 99999

        # Verificar que el producto no existe
        self.assertFalse(Producto.objects.filter(id=producto_id_inexistente).exists())

        # Intentar eliminar producto inexistente
        with self.assertRaises(CarritoError) as context:
            eliminar_producto(
                carrito_id=carrito.id,
                producto_id=producto_id_inexistente
            )

        # Verificar mensaje de error
        self.assertIn('no se encuentra en el carrito', str(context.exception).lower())

        # Verificar que el carrito no cambió
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 1)
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 3)

    def test_eliminar_mismo_producto_dos_veces(self):
        """
        Verificar comportamiento al eliminar el mismo producto dos veces
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=2
        )

        # Primera eliminación (debe funcionar)
        resultado1 = eliminar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id
        )

        self.assertEqual(resultado1['producto_id'], self.producto1.id)
        self.assertFalse(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto1
        ).exists())

        # Segunda eliminación (debe fallar)
        with self.assertRaises(CarritoError) as context:
            eliminar_producto(
                carrito_id=carrito.id,
                producto_id=self.producto1.id
            )

        # Verificar mensaje de error
        self.assertIn('no se encuentra en el carrito', str(context.exception).lower())
