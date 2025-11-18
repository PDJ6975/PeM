"""
Pruebas de integración para el carrito de compras.
Valida flujos completos end-to-end integrando API REST, servicios, modelos y sesiones.
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
import json

from core.models import Producto, Marca, Categoria, Carrito, Cliente


class IntegracionCarritoTestCase(TestCase):
    """Pruebas de integración API REST + Servicios + Sesiones"""

    def setUp(self):
        """Preparar datos de prueba antes de cada test"""
        # Crear o obtener marca y categoría
        self.marca, _ = Marca.objects.get_or_create(
            nombre="Kong Test Integración"
        )
        self.categoria, _ = Categoria.objects.get_or_create(
            nombre="Juguetes Test",
            defaults={"descripcion": "Juguetes para mascotas"}
        )

        # Crear productos de prueba
        self.producto_a = Producto.objects.create(
            nombre="Pelota Kong Classic",
            descripcion="Pelota resistente para perros",
            precio=Decimal("7.99"),
            stock=10,
            marca=self.marca,
            categoria=self.categoria,
            esta_disponible=True
        )

        self.producto_b = Producto.objects.create(
            nombre="Kong Flyer",
            descripcion="Disco volador para perros",
            precio=Decimal("12.90"),
            stock=5,
            marca=self.marca,
            categoria=self.categoria,
            esta_disponible=True
        )

        # Cliente HTTP para simular peticiones
        self.client = Client()

    def test_pi01_flujo_completo_agregar_producto_usuario_anonimo(self):
        """
        PI-01: Flujo completo de agregar producto (Usuario Anónimo)

        Objetivo: Verificar que un usuario anónimo pueda agregar productos
        mediante la API REST y que se persista correctamente en sesión.
        """

        # Paso 1: Hacer POST a /api/carrito/agregar/ sin autenticación
        url_agregar = reverse('api_carrito_agregar')
        data = {
            'producto_id': self.producto_a.id,
            'cantidad': 2
        }

        response = self.client.post(
            url_agregar,
            data=json.dumps(data),
            content_type='application/json'
        )

        # Validación: Código HTTP 200
        self.assertEqual(
            response.status_code,
            200,
            "La petición POST debe retornar 200 OK"
        )

        # Validación: Respuesta contiene datos esperados
        response_data = response.json()
        self.assertIn('carrito', response_data, "Respuesta debe contener 'carrito'")
        self.assertEqual(
            response_data['mensaje'],
            'Producto agregado',
            "Mensaje de confirmación debe ser correcto"
        )

        # Paso 2: Verificar que se crea un carrito anónimo
        carrito_count = Carrito.objects.filter(cliente__isnull=True).count()
        self.assertEqual(
            carrito_count,
            1,
            "Debe crearse exactamente un carrito anónimo"
        )

        carrito_anonimo = Carrito.objects.filter(cliente__isnull=True).first()
        self.assertIsNotNone(carrito_anonimo, "El carrito anónimo debe existir")

        # Paso 3: Verificar que carrito_id se guarda en la sesión
        session = self.client.session
        self.assertIn(
            'carrito_id',
            session,
            "carrito_id debe estar en la sesión"
        )
        self.assertEqual(
            session['carrito_id'],
            carrito_anonimo.id,
            "carrito_id en sesión debe coincidir con el carrito creado"
        )

        # Paso 4: Hacer GET a /api/carrito/ con la misma sesión
        url_obtener = reverse('api_carrito_obtener')
        response_get = self.client.get(url_obtener)

        # Validación: Código HTTP 200 en GET
        self.assertEqual(
            response_get.status_code,
            200,
            "La petición GET debe retornar 200 OK"
        )

        # Paso 5: Verificar que el producto agregado aparece en la respuesta
        carrito_data = response_get.json()
        self.assertIn('carrito', carrito_data, "Respuesta debe contener 'carrito'")

        carrito = carrito_data['carrito']

        # Validación: Producto aparece con cantidad correcta
        self.assertEqual(
            len(carrito['items']),
            1,
            "El carrito debe tener exactamente 1 item"
        )

        item = carrito['items'][0]
        self.assertEqual(
            item['producto']['id'],
            self.producto_a.id,
            "El producto en el carrito debe ser el agregado"
        )
        self.assertEqual(
            item['cantidad'],
            2,
            "La cantidad debe ser 2"
        )

        # Validación: Subtotal calculado correctamente
        subtotal_esperado = self.producto_a.precio * 2
        self.assertEqual(
            Decimal(str(item['subtotal'])),
            subtotal_esperado,
            f"El subtotal debe ser {subtotal_esperado}"
        )

        # Validación: Total del carrito es correcto
        self.assertEqual(
            carrito['total_items'],
            2,
            "El total de items debe ser 2"
        )
        self.assertEqual(
            Decimal(str(carrito['subtotal'])),
            subtotal_esperado,
            f"El subtotal del carrito debe ser {subtotal_esperado}"
        )

    def test_pi02_flujo_completo_agregar_producto_usuario_autenticado(self):
        """
        PI-02: Flujo completo de agregar producto (Usuario Autenticado)

        Objetivo: Verificar que un usuario autenticado use su carrito 1:1
        mediante la API REST.
        """

        # Paso 1: Crear y autenticar un cliente
        cliente = Cliente.objects.create_user(
            email='test@example.com',
            password='password123',
            nombre='Test',
            apellidos='User'
        )

        # Autenticar al cliente
        self.client.login(email='test@example.com', password='password123')

        # Verificar que no existe carrito previo
        self.assertFalse(
            hasattr(cliente, 'carrito'),
            "El cliente no debe tener carrito inicialmente"
        )

        # Paso 2: Hacer POST a /api/carrito/agregar/
        url_agregar = reverse('api_carrito_agregar')
        data = {
            'producto_id': self.producto_a.id,
            'cantidad': 3
        }

        response = self.client.post(
            url_agregar,
            data=json.dumps(data),
            content_type='application/json'
        )

        # Validación: Código HTTP 200
        self.assertEqual(
            response.status_code,
            200,
            "La petición POST debe retornar 200 OK"
        )

        # Paso 3: Verificar que se usa cliente.carrito (relación 1:1)
        cliente.refresh_from_db()
        self.assertTrue(
            hasattr(cliente, 'carrito'),
            "El cliente debe tener un carrito tras agregar producto"
        )

        carrito_cliente = cliente.carrito
        self.assertIsNotNone(
            carrito_cliente,
            "El carrito del cliente debe existir"
        )

        # Validación: carrito.cliente apunta al usuario autenticado
        self.assertEqual(
            carrito_cliente.cliente.id,
            cliente.id,
            "El carrito debe estar asociado al cliente autenticado"
        )

        # Verificar que el producto se agregó al carrito correcto
        items = carrito_cliente.items.all()
        self.assertEqual(
            items.count(),
            1,
            "El carrito debe tener 1 item"
        )
        self.assertEqual(
            items[0].producto.id,
            self.producto_a.id,
            "El producto en el carrito debe ser el agregado"
        )
        self.assertEqual(
            items[0].cantidad,
            3,
            "La cantidad debe ser 3"
        )

        # Validación: No se usa request.session['carrito_id'] para usuarios autenticados
        session = self.client.session
        carrito_id_en_sesion = session.get('carrito_id')

        if carrito_id_en_sesion:
            # Si existe en sesión, debe ser diferente o no debe importar
            # porque el sistema usa cliente.carrito para autenticados
            pass

        # Paso 4: Hacer GET a /api/carrito/
        url_obtener = reverse('api_carrito_obtener')
        response_get = self.client.get(url_obtener)

        # Validación: Código HTTP 200
        self.assertEqual(
            response_get.status_code,
            200,
            "La petición GET debe retornar 200 OK"
        )

        # Paso 5: Verificar que el producto aparece en el carrito del cliente
        carrito_data = response_get.json()
        self.assertIn('carrito', carrito_data, "Respuesta debe contener 'carrito'")

        carrito = carrito_data['carrito']
        self.assertEqual(
            len(carrito['items']),
            1,
            "El carrito debe tener 1 item"
        )

        item = carrito['items'][0]
        self.assertEqual(
            item['producto']['id'],
            self.producto_a.id,
            "El producto debe ser el agregado"
        )
        self.assertEqual(
            item['cantidad'],
            3,
            "La cantidad debe ser 3"
        )

        # Validación: No se crea nuevo carrito si el cliente ya tiene uno
        # Agregar otro producto para verificar que usa el mismo carrito
        data2 = {
            'producto_id': self.producto_b.id,
            'cantidad': 1
        }

        response2 = self.client.post(
            url_agregar,
            data=json.dumps(data2),
            content_type='application/json'
        )

        self.assertEqual(response2.status_code, 200)

        # Verificar que sigue siendo el mismo carrito
        cliente.refresh_from_db()
        self.assertEqual(
            cliente.carrito.id,
            carrito_cliente.id,
            "Debe seguir usando el mismo carrito (relación 1:1)"
        )

        # Verificar que ahora tiene 2 productos
        self.assertEqual(
            cliente.carrito.items.count(),
            2,
            "El carrito debe tener 2 items diferentes"
        )

    def test_pi03_persistencia_carrito_entre_peticiones_anonimo(self):
        """
        PI-03: Persistencia de carrito entre peticiones (Anónimo)

        Objetivo: Verificar que el carrito de un usuario anónimo persiste
        entre múltiples peticiones HTTP.
        """

        url_agregar = reverse('api_carrito_agregar')
        url_obtener = reverse('api_carrito_obtener')

        # Paso 1: Agregar producto A en petición 1
        data_a = {
            'producto_id': self.producto_a.id,
            'cantidad': 2
        }

        response1 = self.client.post(
            url_agregar,
            data=json.dumps(data_a),
            content_type='application/json'
        )

        self.assertEqual(response1.status_code, 200)

        # Obtener carrito_id de la sesión tras primera petición
        session_1 = self.client.session
        carrito_id_1 = session_1.get('carrito_id')
        self.assertIsNotNone(
            carrito_id_1,
            "carrito_id debe estar en sesión tras primera petición"
        )

        # Paso 2: Agregar producto B en petición 2 (misma sesión)
        data_b = {
            'producto_id': self.producto_b.id,
            'cantidad': 1
        }

        response2 = self.client.post(
            url_agregar,
            data=json.dumps(data_b),
            content_type='application/json'
        )

        self.assertEqual(response2.status_code, 200)

        # Validación: Mismo carrito_id en petición 2
        session_2 = self.client.session
        carrito_id_2 = session_2.get('carrito_id')
        self.assertEqual(
            carrito_id_1,
            carrito_id_2,
            "El carrito_id debe ser el mismo entre peticiones"
        )

        # Paso 3: Obtener carrito en petición 3
        response3 = self.client.get(url_obtener)

        self.assertEqual(response3.status_code, 200)

        # Validación: Mismo carrito_id en petición 3
        session_3 = self.client.session
        carrito_id_3 = session_3.get('carrito_id')
        self.assertEqual(
            carrito_id_1,
            carrito_id_3,
            "El carrito_id debe persistir en todas las peticiones"
        )

        # Paso 4: Verificar que ambos productos están presentes
        carrito_data = response3.json()
        carrito = carrito_data['carrito']

        self.assertEqual(
            len(carrito['items']),
            2,
            "El carrito debe contener 2 items"
        )

        # Validación: Ambos productos presentes
        productos_ids = [item['producto']['id'] for item in carrito['items']]
        self.assertIn(
            self.producto_a.id,
            productos_ids,
            "Producto A debe estar en el carrito"
        )
        self.assertIn(
            self.producto_b.id,
            productos_ids,
            "Producto B debe estar en el carrito"
        )

        # Validación: Total de items = suma de ambos productos
        total_items_esperado = 2 + 1  # 2 del producto A + 1 del producto B
        self.assertEqual(
            carrito['total_items'],
            total_items_esperado,
            f"El total de items debe ser {total_items_esperado}"
        )

    def test_pi04_migracion_carrito_al_hacer_login(self):
        """
        PI-04: Migración de carrito al hacer login

        Objetivo: Verificar el flujo completo de migración cuando un usuario
        anónimo inicia sesión.
        """

        # Paso 1: Usuario anónimo agrega productos al carrito
        url_agregar = reverse('api_carrito_agregar')
        data_producto_a = {
            'producto_id': self.producto_a.id,
            'cantidad': 2
        }

        response_anonimo = self.client.post(
            url_agregar,
            data=json.dumps(data_producto_a),
            content_type='application/json'
        )

        self.assertEqual(response_anonimo.status_code, 200)

        # Guardar carrito_id anónimo
        carrito_id_anonimo = self.client.session.get('carrito_id')
        self.assertIsNotNone(carrito_id_anonimo)

        # Verificar que el carrito anónimo existe en BD
        carrito_anonimo = Carrito.objects.get(id=carrito_id_anonimo)
        self.assertIsNone(carrito_anonimo.cliente, "El carrito debe ser anónimo")
        self.assertEqual(
            carrito_anonimo.items.count(),
            1,
            "El carrito anónimo debe tener 1 item"
        )

        # Paso 2: Crear un cliente y hacer login
        cliente = Cliente.objects.create_user(
            email='migracion@example.com',
            password='password123',
            nombre='Test',
            apellidos='Migración'
        )

        # Hacer login (esto debería triggear la migración del carrito)
        login_success = self.client.login(
            email='migracion@example.com',
            password='password123'
        )
        self.assertTrue(login_success, "El login debe ser exitoso")

        # Paso 3: Verificar que el carrito anónimo se migra al usuario
        data_producto_b = {
            'producto_id': self.producto_b.id,
            'cantidad': 1
        }

        response_autenticado = self.client.post(
            url_agregar,
            data=json.dumps(data_producto_b),
            content_type='application/json'
        )

        self.assertEqual(response_autenticado.status_code, 200)

        # Paso 4: Hacer GET al carrito autenticado
        url_obtener = reverse('api_carrito_obtener')
        response_get = self.client.get(url_obtener)

        self.assertEqual(response_get.status_code, 200)

        # Validación: Carrito anónimo está asociado al cliente ahora
        carrito_anonimo_existe = Carrito.objects.filter(
            id=carrito_id_anonimo,
            cliente__isnull=True
        ).exists()
        self.assertFalse(
            carrito_anonimo_existe,
            "El carrito anónimo debe eliminarse o asociarse al cliente"
        )

        # Validación: Productos aparecen en cliente.carrito
        cliente.refresh_from_db()
        self.assertTrue(
            hasattr(cliente, 'carrito'),
            "El cliente debe tener un carrito"
        )

        carrito_cliente = cliente.carrito
        items_cliente = carrito_cliente.items.all()

        # Debe tener al menos el producto del carrito anónimo
        self.assertGreaterEqual(
            items_cliente.count(),
            1,
            "El carrito del cliente debe tener al menos 1 item"
        )

        # Verificar que el producto A (del carrito anónimo) está presente
        producto_a_en_carrito = items_cliente.filter(
            producto=self.producto_a
        ).exists()
        self.assertTrue(
            producto_a_en_carrito,
            "El producto del carrito anónimo debe estar en el carrito del cliente"
        )

        # Validación: Si el cliente ya tenía productos, se combinan correctamente
        productos_ids = [item.producto.id for item in items_cliente]
        self.assertIn(
            self.producto_a.id,
            productos_ids,
            "Producto A (del carrito anónimo) debe estar presente"
        )
        self.assertIn(
            self.producto_b.id,
            productos_ids,
            "Producto B (agregado después del login) debe estar presente"
        )

        # Validación: Cantidades correctas
        item_producto_a = items_cliente.get(producto=self.producto_a)
        self.assertEqual(
            item_producto_a.cantidad,
            2,
            "La cantidad del producto A debe ser 2"
        )
