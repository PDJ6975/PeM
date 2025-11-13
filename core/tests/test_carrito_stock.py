"""
Pruebas unitarias para la consistencia de stock en el carrito.
Casos de prueba CP-64 a CP-67 del Plan de Pruebas.
"""

from decimal import Decimal
from django.test import TestCase

from core.models import Producto, Marca, Categoria, Cliente, Carrito, ItemCarrito
from core.services.carrito import (
    agregar_producto,
    modificar_cantidad,
    obtener_o_crear_carrito,
    obtener_carrito_detallado,
    StockInsuficienteError,
    ProductoNoDisponibleError
)


class ConsistenciaStockCarritoTestCase(TestCase):
    """Pruebas para verificar la consistencia del stock en operaciones del carrito"""

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

    def test_cp64_no_agregar_mas_que_stock_disponible(self):
        """
        CP-64: Verificar que no se puede agregar más cantidad que el stock disponible
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # El producto1 tiene stock=10
        self.assertEqual(self.producto1.stock, 10)

        # Intentar agregar 15 unidades (excede stock)
        with self.assertRaises(StockInsuficienteError) as context:
            agregar_producto(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                cantidad=15
            )

        # Verificar mensaje de error
        error_msg = str(context.exception).lower()
        self.assertIn('stock insuficiente', error_msg)
        self.assertIn('disponible: 10', error_msg)
        self.assertIn('solicitado: 15', error_msg)

        # Verificar que el carrito está vacío (no se agregó nada)
        self.assertTrue(carrito.esta_vacio())
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 0)

        # Verificar que sí se puede agregar exactamente el stock disponible
        resultado = agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=10
        )

        self.assertEqual(resultado['cantidad'], 10)
        self.assertFalse(carrito.esta_vacio())

    def test_cp65_no_actualizar_excediendo_stock_disponible(self):
        """
        CP-65: Verificar que al actualizar, no se excede el stock disponible
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto con cantidad inicial
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=3
        )

        # El producto1 tiene stock=10
        self.assertEqual(self.producto1.stock, 10)

        # Intentar actualizar a 15 unidades (excede stock)
        with self.assertRaises(StockInsuficienteError) as context:
            modificar_cantidad(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                nueva_cantidad=15
            )

        # Verificar mensaje de error
        error_msg = str(context.exception).lower()
        self.assertIn('stock insuficiente', error_msg)
        self.assertIn('disponible: 10', error_msg)

        # Verificar que la cantidad no cambió
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 3)

        # Verificar que sí se puede actualizar al stock máximo
        resultado = modificar_cantidad(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            nueva_cantidad=10
        )

        self.assertEqual(resultado['cantidad'], 10)
        item.refresh_from_db()
        self.assertEqual(item.cantidad, 10)

    def test_cp66_comportamiento_cuando_stock_cambia_con_item_en_carrito(self):
        """
        CP-66: Verificar comportamiento cuando el stock del producto cambia después de estar en el carrito
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto con stock inicial de 10
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=8
        )

        # Verificar que se agregó correctamente
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 8)

        # ESCENARIO 1: El stock disminuye (ej: otro usuario compró)
        self.producto1.stock = 5
        self.producto1.save()

        # Intentar agregar más unidades (debería fallar porque ya hay 8 en carrito y stock es 5)
        with self.assertRaises(StockInsuficienteError):
            agregar_producto(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                cantidad=2  # 8 + 2 = 10, excede stock de 5
            )

        # Intentar actualizar a una cantidad mayor al nuevo stock
        with self.assertRaises(StockInsuficienteError):
            modificar_cantidad(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                nueva_cantidad=7  # Excede stock de 5
            )

        # Verificar que la cantidad original no cambió
        item.refresh_from_db()
        self.assertEqual(item.cantidad, 8)

        # ESCENARIO 2: Ajustar a cantidad válida según nuevo stock
        resultado = modificar_cantidad(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            nueva_cantidad=5  # Igual al stock actual
        )

        self.assertEqual(resultado['cantidad'], 5)
        item.refresh_from_db()
        self.assertEqual(item.cantidad, 5)

        # ESCENARIO 3: El stock aumenta
        self.producto1.stock = 20
        self.producto1.save()

        # Ahora sí se puede agregar más
        resultado = agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=10  # 5 + 10 = 15, dentro del nuevo stock de 20
        )

        self.assertEqual(resultado['cantidad'], 15)

    def test_cp67_no_agregar_productos_no_disponibles(self):
        """
        CP-67: Verificar que productos con esta_disponible=False no se pueden agregar
        """
        # Crear producto marcado como no disponible
        producto_no_disponible = Producto.objects.create(
            nombre="Producto No Disponible",
            descripcion="Este producto no está disponible",
            precio=Decimal("29.99"),
            stock=10,  # Tiene stock pero está marcado como no disponible
            esta_disponible=False,
            marca=self.marca,
            categoria=self.categoria
        )

        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Intentar agregar producto no disponible
        with self.assertRaises(ProductoNoDisponibleError) as context:
            agregar_producto(
                carrito_id=carrito.id,
                producto_id=producto_no_disponible.id,
                cantidad=2
            )

        # Verificar mensaje de error
        error_msg = str(context.exception).lower()
        self.assertIn('no está disponible', error_msg)
        self.assertIn(producto_no_disponible.nombre.lower(), error_msg.lower())

        # Verificar que el carrito sigue vacío
        self.assertTrue(carrito.esta_vacio())
        self.assertEqual(ItemCarrito.objects.filter(carrito=carrito).count(), 0)

    def test_producto_agotado_no_se_puede_agregar(self):
        """
        Test adicional: Verificar que producto con stock=0 no se puede agregar
        """
        # Crear producto agotado (stock=0, disponible=True)
        producto_agotado = Producto.objects.create(
            nombre="Producto Agotado",
            descripcion="Sin stock",
            precio=Decimal("19.99"),
            stock=0,
            esta_disponible=True,  # Marcado como disponible pero sin stock
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
        error_msg = str(context.exception).lower()
        self.assertIn('no está disponible', error_msg)

        # Verificar que el carrito sigue vacío
        self.assertTrue(carrito.esta_vacio())

    def test_validacion_stock_con_multiples_productos(self):
        """
        Test adicional: Verificar validación de stock con múltiples productos en el carrito
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto1 hasta casi agotar el stock
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto1.id, cantidad=9)

        # Agregar producto2
        agregar_producto(carrito_id=carrito.id, producto_id=self.producto2.id, cantidad=3)

        # Verificar estado del carrito
        self.assertEqual(carrito.total_items(), 12)  # 9 + 3

        # Intentar agregar más del producto1 (solo queda 1 en stock)
        with self.assertRaises(StockInsuficienteError):
            agregar_producto(carrito_id=carrito.id, producto_id=self.producto1.id, cantidad=2)

        # Pero sí se puede agregar 1 más del producto1
        resultado = agregar_producto(carrito_id=carrito.id, producto_id=self.producto1.id, cantidad=1)
        self.assertEqual(resultado['cantidad'], 10)

        # Verificar que producto2 sigue sin cambios
        item2 = ItemCarrito.objects.get(carrito=carrito, producto=self.producto2)
        self.assertEqual(item2.cantidad, 3)

    def test_producto_se_marca_no_disponible_con_item_en_carrito(self):
        """
        Test adicional: Verificar qué pasa si un producto se marca como no disponible
        después de estar en el carrito
        """
        carrito = obtener_o_crear_carrito(cliente=self.cliente)

        # Agregar producto cuando está disponible
        agregar_producto(
            carrito_id=carrito.id,
            producto_id=self.producto1.id,
            cantidad=5
        )

        # Verificar que está en el carrito
        item = ItemCarrito.objects.get(carrito=carrito, producto=self.producto1)
        self.assertEqual(item.cantidad, 5)

        # Marcar producto como no disponible
        self.producto1.esta_disponible = False
        self.producto1.save()

        # El item sigue en el carrito (no se elimina automáticamente)
        item.refresh_from_db()
        self.assertEqual(item.cantidad, 5)

        # Pero no se puede agregar más
        with self.assertRaises(ProductoNoDisponibleError):
            agregar_producto(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                cantidad=2
            )

        # Ni actualizar la cantidad
        with self.assertRaises(ProductoNoDisponibleError):
            modificar_cantidad(
                carrito_id=carrito.id,
                producto_id=self.producto1.id,
                nueva_cantidad=7
            )
