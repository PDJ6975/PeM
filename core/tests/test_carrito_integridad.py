"""
Pruebas unitarias para verificar la integridad de datos del carrito.
Casos de prueba CP-58 a CP-63 del Plan de Pruebas.
"""

from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError, transaction

from core.models import Producto, Marca, Categoria, Cliente, Carrito, ItemCarrito
from core.services.carrito import (
    agregar_producto,
    obtener_o_crear_carrito
)


class IntegridadDatosCarritoTestCase(TestCase):
    """Pruebas para verificar la integridad de datos y relaciones del carrito"""

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
            email="test@example.com",
            password="password123",
            nombre="Test",
            apellidos="User"
        )

    # --- VERIFICACIONES DE MODELO ---

    def test_cp58_carrito_anonimo_tiene_cliente_none(self):
        """
        CP-58: Verificar que Carrito para usuario anónimo tiene cliente=None
        """
        # Crear carrito anónimo
        carrito_anonimo = obtener_o_crear_carrito(cliente=None)

        # Verificar que el cliente es None
        self.assertIsNone(carrito_anonimo.cliente)

        # Agregar producto al carrito anónimo
        agregar_producto(
            carrito_id=carrito_anonimo.id,
            producto_id=self.producto1.id,
            cantidad=2
        )

        # Verificar el item del carrito
        item = ItemCarrito.objects.get(carrito=carrito_anonimo, producto=self.producto1)

        # Verificar que el carrito del item no tiene cliente
        self.assertIsNone(item.carrito.cliente)

        # Verificar en la base de datos
        carrito_db = Carrito.objects.get(id=carrito_anonimo.id)
        self.assertIsNone(carrito_db.cliente)

    def test_cp59_carrito_registrado_tiene_cliente(self):
        """
        CP-59: Verificar que Carrito para usuario registrado tiene cliente
        """
        # Crear carrito de usuario registrado
        carrito_registrado = obtener_o_crear_carrito(cliente=self.cliente)

        # Verificar que el cliente está asignado
        self.assertIsNotNone(carrito_registrado.cliente)
        self.assertEqual(carrito_registrado.cliente, self.cliente)

        # Agregar producto al carrito
        agregar_producto(
            carrito_id=carrito_registrado.id,
            producto_id=self.producto1.id,
            cantidad=3
        )

        # Verificar el item del carrito
        item = ItemCarrito.objects.get(carrito=carrito_registrado, producto=self.producto1)

        # Verificar que el carrito del item tiene el cliente correcto
        self.assertIsNotNone(item.carrito.cliente)
        self.assertEqual(item.carrito.cliente, self.cliente)

        # Verificar en la base de datos
        carrito_db = Carrito.objects.get(id=carrito_registrado.id)
        self.assertEqual(carrito_db.cliente, self.cliente)

    def test_cp60_unique_together_carrito_producto_usuario_registrado(self):
        """
        CP-60: Verificar restricción unique_together (carrito, producto) para usuarios registrados
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto al carrito
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=2
        )

        # Verificar que el item existe
        self.assertEqual(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto1
        ).count(), 1)

        # Intentar crear otro item con el mismo carrito y producto directamente
        # (esto debe fallar por unique_together)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ItemCarrito.objects.create(
                    carrito=carrito,
                    producto=self.producto1,
                    cantidad=5
                )

        # Verificar que sigue habiendo solo un item
        self.assertEqual(ItemCarrito.objects.filter(
            carrito=carrito,
            producto=self.producto1
        ).count(), 1)

    def test_cp61_unique_together_carrito_producto_usuario_anonimo(self):
        """
        CP-61: Verificar restricción unique_together (carrito, producto) para usuarios anónimos
        """
        carrito_anonimo = obtener_o_crear_carrito(cliente=None)

        # Verificar que es carrito anónimo
        self.assertIsNone(carrito_anonimo.cliente)

        # Agregar producto al carrito
        agregar_producto(
            carrito_id=carrito_anonimo.id,
            producto_id=self.producto1.id,
            cantidad=3
        )

        # Verificar que el item existe
        self.assertEqual(ItemCarrito.objects.filter(
            carrito=carrito_anonimo,
            producto=self.producto1
        ).count(), 1)

        # Intentar crear otro item con el mismo carrito y producto directamente
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ItemCarrito.objects.create(
                    carrito=carrito_anonimo,
                    producto=self.producto1,
                    cantidad=7
                )

        # Verificar que sigue habiendo solo un item
        self.assertEqual(ItemCarrito.objects.filter(
            carrito=carrito_anonimo,
            producto=self.producto1
        ).count(), 1)

    # --- VERIFICACIONES DE RELACIONES CASCADE ---

    def test_cp62_eliminar_producto_elimina_items_carrito_cascade(self):
        """
        CP-62: Verificar que al eliminar un producto, se eliminan sus ItemCarrito asociados (CASCADE)
        """
        # Crear varios carritos con el producto1
        carrito1 = obtener_o_crear_carrito(cliente=self.cliente)
        carrito2 = obtener_o_crear_carrito(cliente=None)

        # Agregar el producto1 a ambos carritos
        agregar_producto(carrito_id=carrito1.id, producto_id=self.producto1.id, cantidad=2)
        agregar_producto(carrito_id=carrito2.id, producto_id=self.producto1.id, cantidad=3)

        # Agregar también producto2 a carrito1 (para verificar que no se elimina)
        agregar_producto(carrito_id=carrito1.id, producto_id=self.producto2.id, cantidad=1)

        # Verificar items antes de eliminar
        items_producto1_antes = ItemCarrito.objects.filter(producto=self.producto1).count()
        items_producto2_antes = ItemCarrito.objects.filter(producto=self.producto2).count()

        self.assertEqual(items_producto1_antes, 2)  # En carrito1 y carrito2
        self.assertEqual(items_producto2_antes, 1)  # Solo en carrito1

        # Eliminar producto1
        producto1_id = self.producto1.id
        self.producto1.delete()

        # Verificar que se eliminaron todos los items del producto1 (CASCADE)
        items_producto1_despues = ItemCarrito.objects.filter(producto_id=producto1_id).count()
        self.assertEqual(items_producto1_despues, 0)

        # Verificar que los items del producto2 NO se eliminaron
        items_producto2_despues = ItemCarrito.objects.filter(producto=self.producto2).count()
        self.assertEqual(items_producto2_despues, 1)

        # Verificar que los carritos siguen existiendo
        self.assertTrue(Carrito.objects.filter(id=carrito1.id).exists())
        self.assertTrue(Carrito.objects.filter(id=carrito2.id).exists())

    def test_cp63_eliminar_cliente_elimina_carrito_y_items_cascade(self):
        """
        CP-63: Verificar que al eliminar un cliente, se eliminan su Carrito y sus ItemCarrito asociados (CASCADE)
        """
        # Crear carrito para el cliente
        carrito_cliente = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar productos al carrito
        agregar_producto(carrito_id=carrito_cliente.id, producto_id=self.producto1.id, cantidad=2)
        agregar_producto(carrito_id=carrito_cliente.id, producto_id=self.producto2.id, cantidad=3)

        # Crear un carrito anónimo (no debe eliminarse)
        carrito_anonimo = obtener_o_crear_carrito(cliente=None)
        agregar_producto(carrito_id=carrito_anonimo.id, producto_id=self.producto1.id, cantidad=1)

        # Verificar estado antes de eliminar
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito_cliente).count(), 2)
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito_anonimo).count(), 1)
        self.assertTrue(Carrito.objects.filter(id=carrito_cliente.id).exists())
        self.assertTrue(Carrito.objects.filter(id=carrito_anonimo.id).exists())

        # Guardar IDs para verificación posterior
        carrito_cliente_id = carrito_cliente.id
        carrito_anonimo_id = carrito_anonimo.id

        # Eliminar cliente
        self.cliente.delete()

        # Verificar que el carrito del cliente fue eliminado (CASCADE)
        self.assertFalse(Carrito.objects.filter(id=carrito_cliente_id).exists())

        # Verificar que los items del carrito del cliente fueron eliminados (CASCADE)
        self.assertEqual(ItemCarrito.objects.filter(carrito_id=carrito_cliente_id).count(), 0)

        # Verificar que el carrito anónimo NO fue eliminado
        self.assertTrue(Carrito.objects.filter(id=carrito_anonimo_id).exists())

        # Verificar que los items del carrito anónimo NO fueron eliminados
        self.assertEqual(ItemCarrito.objects.filter(carrito_id=carrito_anonimo_id).count(), 1)

        # Verificar que los productos siguen existiendo
        self.assertTrue(Producto.objects.filter(id=self.producto1.id).exists())
        self.assertTrue(Producto.objects.filter(id=self.producto2.id).exists())

    def test_relaciones_cascade_multiples_clientes(self):
        """
        Test adicional: Verificar CASCADE con múltiples clientes y carritos
        """
        # Crear otro cliente
        cliente2 = Cliente.objects.create_user(
            email="user2@example.com",
            password="password123",
            nombre="Usuario",
            apellidos="Dos"
        )

        # Crear carritos para ambos clientes
        carrito1 = obtener_o_crear_carrito(cliente=self.cliente)
        carrito2 = obtener_o_crear_carrito(cliente=cliente2)

        # Agregar productos a ambos carritos
        agregar_producto(carrito_id=carrito1.id, producto_id=self.producto1.id, cantidad=2)
        agregar_producto(carrito_id=carrito2.id, producto_id=self.producto1.id, cantidad=3)

        # Eliminar solo el primer cliente
        carrito1_id = carrito1.id
        self.cliente.delete()

        # Verificar que solo se eliminó el carrito del primer cliente
        self.assertFalse(Carrito.objects.filter(id=carrito1_id).exists())
        self.assertTrue(Carrito.objects.filter(id=carrito2.id).exists())

        # Verificar que el carrito del segundo cliente sigue con sus items
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito2).count(), 1)
