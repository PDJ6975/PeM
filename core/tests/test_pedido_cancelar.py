"""
Tests para la funcionalidad de Cancelar Pedido
Cubre: acceso, permisos, validaciones, cambio de estado
"""
from django.test import TestCase, Client
from django.urls import reverse
from core.models import Cliente, Pedido, ItemPedido, Producto, Marca, Categoria
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class PedidoCancelarAccessTestCase(TestCase):
    """Tests de control de acceso a la cancelación de pedidos"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = Client()
        
        # Clientes
        self.cliente = Cliente.objects.create_user(
            email='propietario@test.com',
            nombre='Propietario',
            apellidos='Test',
            telefono='600123456',
            password='testpass123'
        )
        
        self.otro_cliente = Cliente.objects.create_user(
            email='otro@test.com',
            nombre='Otro',
            apellidos='Usuario',
            telefono='600654321',
            password='testpass123'
        )
        
        self.staff = Cliente.objects.create_user(
            email='staff@test.com',
            nombre='Staff',
            apellidos='Admin',
            telefono='600111222',
            password='staffpass123',
            is_staff=True
        )
        
        # Productos
        marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        self.producto = Producto.objects.create(
            nombre='Test Producto',
            precio=Decimal('10.00'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        # Pedido cancelable
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Calle Test 123',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
    def test_metodo_get_no_permite_cancelacion(self):
        """GET en cancelar_pedido redirige sin cancelar"""
        self.client.login(email='propietario@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido])
        )
        
        # Debe redirigir a seguimiento
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.url.endswith(
                reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
            )
        )
        
        # Verificar que NO se canceló
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'confirmado')
        
    def test_propietario_autenticado_puede_cancelar(self):
        """Propietario autenticado puede cancelar su pedido"""
        self.client.login(email='propietario@test.com', password='testpass123')
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Verificar que se canceló
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'cancelado')
        
    def test_no_propietario_autenticado_sin_acceso(self):
        """Usuario autenticado NO propietario no puede cancelar pedido ajeno"""
        self.client.login(email='otro@test.com', password='testpass123')
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido]),
            follow=True
        )
        
        # Redirige con mensaje de error
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('No tienes acceso' in str(m) for m in messages))
        
        # Verificar que NO se canceló
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'confirmado')
        
    def test_staff_puede_cancelar_cualquier_pedido(self):
        """Staff puede cancelar cualquier pedido"""
        self.client.login(email='staff@test.com', password='staffpass123')
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 302)
        
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'cancelado')
        
    def test_usuario_anonimo_sin_token_no_tiene_acceso(self):
        """Usuario anónimo sin token temporal no puede cancelar"""
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido]),
            follow=True
        )
        
        # Redirige a ingreso de seguimiento
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/pedido_seguimiento_ingresar.html')
        
        # Verificar que NO se canceló
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'confirmado')
        
    def test_usuario_anonimo_con_token_valido_puede_cancelar(self):
        """Usuario anónimo con token temporal válido puede cancelar"""
        session = self.client.session
        session['pedido_acceso_temporal'] = {
            'numero_pedido': self.pedido.numero_pedido,
            'tracking_token': str(self.pedido.tracking_token),
            'timestamp': timezone.now().isoformat()
        }
        session.save()
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 302)
        
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'cancelado')
        
    def test_usuario_anonimo_con_token_expirado_sin_acceso(self):
        """Usuario anónimo con token expirado (>1h) no puede cancelar"""
        session = self.client.session
        session['pedido_acceso_temporal'] = {
            'numero_pedido': self.pedido.numero_pedido,
            'tracking_token': str(self.pedido.tracking_token),
            'timestamp': (timezone.now() - timedelta(hours=2)).isoformat()
        }
        session.save()
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido]),
            follow=True
        )
        
        # Redirige a ingreso
        self.assertEqual(response.status_code, 200)
        
        # Verificar que NO se canceló
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'confirmado')


class PedidoCancelarEstadosTestCase(TestCase):
    """Tests de restricciones por estado del pedido"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = Client()
        
        self.cliente = Cliente.objects.create_user(
            email='test@test.com',
            nombre='Test',
            apellidos='User',
            telefono='600123456',
            password='testpass123'
        )
        
        marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        self.producto = Producto.objects.create(
            nombre='Test',
            precio=Decimal('10.00'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        self.client.login(email='test@test.com', password='testpass123')
        
    def _crear_pedido_con_estado(self, estado):
        """Helper para crear pedido con estado específico"""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado=estado,
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Calle Test',
            telefono='600123456'
        )
        ItemPedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        return pedido
        
    def test_pedido_pendiente_puede_cancelarse(self):
        """Pedido en estado 'pendiente' puede cancelarse"""
        pedido = self._crear_pedido_con_estado('pendiente')
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[pedido.numero_pedido]),
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'cancelado')
        
    def test_pedido_confirmado_puede_cancelarse(self):
        """Pedido en estado 'confirmado' puede cancelarse"""
        pedido = self._crear_pedido_con_estado('confirmado')
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[pedido.numero_pedido]),
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'cancelado')
        
    def test_pedido_enviado_no_puede_cancelarse(self):
        """Pedido en estado 'enviado' NO puede cancelarse"""
        pedido = self._crear_pedido_con_estado('enviado')
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[pedido.numero_pedido]),
            follow=True
        )
        
        messages = list(response.context['messages'])
        self.assertTrue(any('ya no puede ser cancelado' in str(m) for m in messages))
        
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'enviado')  # NO cambió
        
    def test_pedido_entregado_no_puede_cancelarse(self):
        """Pedido en estado 'entregado' NO puede cancelarse"""
        pedido = self._crear_pedido_con_estado('entregado')
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[pedido.numero_pedido]),
            follow=True
        )
        
        messages = list(response.context['messages'])
        self.assertTrue(any('ya no puede ser cancelado' in str(m) for m in messages))
        
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'entregado')
        
    def test_pedido_ya_cancelado_no_puede_cancelarse_de_nuevo(self):
        """Pedido en estado 'cancelado' ya está cancelado"""
        pedido = self._crear_pedido_con_estado('cancelado')
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[pedido.numero_pedido]),
            follow=True
        )
        
        messages = list(response.context['messages'])
        self.assertTrue(any('ya no puede ser cancelado' in str(m) for m in messages))
        
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'cancelado')


class PedidoCancelarProcesoTestCase(TestCase):
    """Tests del proceso de cancelación"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = Client()
        
        self.cliente = Cliente.objects.create_user(
            email='test@test.com',
            nombre='Test',
            apellidos='User',
            telefono='600123456',
            password='testpass123'
        )
        
        marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        self.producto = Producto.objects.create(
            nombre='Test',
            precio=Decimal('10.00'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Calle Test',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
        self.client.login(email='test@test.com', password='testpass123')
        
    def test_cancelacion_cambia_estado_a_cancelado(self):
        """Cancelación cambia el estado del pedido a 'cancelado'"""
        self.assertEqual(self.pedido.estado, 'confirmado')
        
        self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido])
        )
        
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'cancelado')
        
    def test_cancelacion_mantiene_otros_campos_intactos(self):
        """Cancelación NO modifica otros campos del pedido"""
        total_original = self.pedido.total
        subtotal_original = self.pedido.subtotal
        direccion_original = self.pedido.direccion_envio
        telefono_original = self.pedido.telefono
        num_items_original = self.pedido.items.count()
        
        self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido])
        )
        
        self.pedido.refresh_from_db()
        
        # Verificar que solo cambió el estado
        self.assertEqual(self.pedido.total, total_original)
        self.assertEqual(self.pedido.subtotal, subtotal_original)
        self.assertEqual(self.pedido.direccion_envio, direccion_original)
        self.assertEqual(self.pedido.telefono, telefono_original)
        self.assertEqual(self.pedido.items.count(), num_items_original)
        
    def test_cancelacion_actualiza_fecha_actualizacion(self):
        """Cancelación actualiza el campo fecha_actualizacion"""
        fecha_original = self.pedido.fecha_actualizacion
        
        # Esperar un momento para que la fecha cambie
        import time
        time.sleep(0.1)
        
        self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido])
        )
        
        self.pedido.refresh_from_db()
        self.assertGreater(self.pedido.fecha_actualizacion, fecha_original)


class PedidoCancelarModalTestCase(TestCase):
    """Tests del modal de confirmación en la vista de seguimiento"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = Client()
        
        self.cliente = Cliente.objects.create_user(
            email='test@test.com',
            nombre='Test',
            apellidos='User',
            telefono='600123456',
            password='testpass123'
        )
        
        marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        producto = Producto.objects.create(
            nombre='Test',
            precio=Decimal('10.00'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Calle Test',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
        self.client.login(email='test@test.com', password='testpass123')
        
    def test_seguimiento_muestra_boton_cancelar_si_puede_cancelar(self):
        """Vista de seguimiento muestra botón de cancelar si el pedido puede cancelarse"""
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, 'Cancelar Pedido')
        self.assertContains(response, 'data-bs-toggle="modal"')
        self.assertContains(response, 'modalCancelar')
        
    def test_seguimiento_no_muestra_boton_cancelar_si_no_puede(self):
        """Vista de seguimiento NO muestra botón si el pedido no puede cancelarse"""
        self.pedido.estado = 'enviado'
        self.pedido.save()
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertNotContains(response, 'Cancelar Pedido')
        
    def test_modal_muestra_numero_pedido(self):
        """Modal de confirmación muestra el número de pedido"""
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, 'modalCancelar')
        self.assertContains(response, self.pedido.numero_pedido)
        
    def test_modal_tiene_formulario_con_csrf(self):
        """Modal contiene formulario con CSRF token"""
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, 'method="post"')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, reverse('pedido_cancelar', args=[self.pedido.numero_pedido]))
        
    def test_modal_tiene_botones_confirmar_y_cancelar(self):
        """Modal tiene botones de confirmación y cancelación"""
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, 'Sí, cancelar pedido')
        self.assertContains(response, 'No, volver')


class PedidoCancelarMensajesTestCase(TestCase):
    """Tests de mensajes de feedback al usuario"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = Client()
        
        self.cliente = Cliente.objects.create_user(
            email='test@test.com',
            nombre='Test',
            apellidos='User',
            telefono='600123456',
            password='testpass123'
        )
        
        marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        producto = Producto.objects.create(
            nombre='Test',
            precio=Decimal('10.00'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Calle Test',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
        self.client.login(email='test@test.com', password='testpass123')
        
    def test_cancelacion_exitosa_muestra_mensaje_success(self):
        """Cancelación exitosa muestra mensaje de éxito"""
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido]),
            follow=True
        )
        
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('cancelado correctamente', str(messages[0]))
        self.assertIn(self.pedido.numero_pedido, str(messages[0]))
        
    def test_pedido_no_cancelable_muestra_mensaje_warning(self):
        """Pedido en estado no cancelable muestra advertencia"""
        self.pedido.estado = 'enviado'
        self.pedido.save()
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido]),
            follow=True
        )
        
        messages = list(response.context['messages'])
        self.assertTrue(any('ya no puede ser cancelado' in str(m) for m in messages))
        
    def test_acceso_no_autorizado_muestra_mensaje_error(self):
        """Acceso no autorizado muestra mensaje de error"""
        self.client.logout()
        otro_cliente = Cliente.objects.create_user(
            email='otro@test.com',
            nombre='Otro',
            apellidos='Usuario',
            telefono='600654321',
            password='testpass123'
        )
        self.client.login(email='otro@test.com', password='testpass123')
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido]),
            follow=True
        )
        
        messages = list(response.context['messages'])
        self.assertTrue(any('No tienes acceso' in str(m) for m in messages))


class PedidoCancelarIntegracionTestCase(TestCase):
    """Tests de integración completos"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = Client()
        
        self.cliente = Cliente.objects.create_user(
            email='test@test.com',
            nombre='Test',
            apellidos='User',
            telefono='600123456',
            password='testpass123'
        )
        
        marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        producto = Producto.objects.create(
            nombre='Test',
            precio=Decimal('10.00'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Calle Test',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
    def test_flujo_completo_cancelacion_exitosa(self):
        """Test de flujo completo: login → ver pedido → cancelar → verificar"""
        # 1. Login
        self.client.login(email='test@test.com', password='testpass123')
        
        # 2. Ver pedido en seguimiento
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cancelar Pedido')
        
        # 3. Cancelar pedido
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido])
        )
        self.assertEqual(response.status_code, 302)
        
        # 4. Verificar en vista de seguimiento
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, 'Cancelado')
        self.assertNotContains(response, 'Cancelar Pedido')  # Botón ya no aparece
        
    def test_cancelacion_desde_mis_pedidos(self):
        """Test de cancelación desde la vista de mis pedidos"""
        self.client.login(email='test@test.com', password='testpass123')
        
        # 1. Ver mis pedidos
        response = self.client.get(reverse('mis_pedidos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pedido.numero_pedido)
        
        # 2. Ir a seguimiento desde mis pedidos
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        self.assertEqual(response.status_code, 200)
        
        # 3. Cancelar
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido]),
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # 4. Volver a mis pedidos y verificar estado
        response = self.client.get(reverse('mis_pedidos'))
        self.assertContains(response, 'Cancelado')
        
    def test_intento_doble_cancelacion(self):
        """Test de intento de cancelar un pedido ya cancelado"""
        self.client.login(email='test@test.com', password='testpass123')
        
        # Primera cancelación
        self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido])
        )
        
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'cancelado')
        
        # Intento de segunda cancelación
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido]),
            follow=True
        )
        
        messages = list(response.context['messages'])
        self.assertTrue(any('ya no puede ser cancelado' in str(m) for m in messages))
        
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'cancelado')


class PedidoCancelarMetodoPuedeTestCase(TestCase):
    """Tests del método puede_cancelar() del modelo Pedido"""
    
    def setUp(self):
        """Configuración inicial"""
        marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        self.producto = Producto.objects.create(
            nombre='Test',
            precio=Decimal('10.00'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        self.cliente = Cliente.objects.create_user(
            email='test@test.com',
            nombre='Test',
            apellidos='User',
            telefono='600123456',
            password='testpass123'
        )
        
    def test_puede_cancelar_pendiente_retorna_true(self):
        """puede_cancelar() retorna True para estado 'pendiente'"""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='pendiente',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Test',
            telefono='600123456'
        )
        
        self.assertTrue(pedido.puede_cancelar())
        
    def test_puede_cancelar_confirmado_retorna_true(self):
        """puede_cancelar() retorna True para estado 'confirmado'"""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Test',
            telefono='600123456'
        )
        
        self.assertTrue(pedido.puede_cancelar())
        
    def test_puede_cancelar_enviado_retorna_false(self):
        """puede_cancelar() retorna False para estado 'enviado'"""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='enviado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Test',
            telefono='600123456'
        )
        
        self.assertFalse(pedido.puede_cancelar())
        
    def test_puede_cancelar_entregado_retorna_false(self):
        """puede_cancelar() retorna False para estado 'entregado'"""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='entregado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Test',
            telefono='600123456'
        )
        
        self.assertFalse(pedido.puede_cancelar())
        
    def test_puede_cancelar_cancelado_retorna_false(self):
        """puede_cancelar() retorna False para estado 'cancelado'"""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='cancelado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Test',
            telefono='600123456'
        )
        
        self.assertFalse(pedido.puede_cancelar())


class PedidoCancelarRedireccionesTestCase(TestCase):
    """Tests de redirecciones tras cancelación"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = Client()
        
        self.cliente = Cliente.objects.create_user(
            email='test@test.com',
            nombre='Test',
            apellidos='User',
            telefono='600123456',
            password='testpass123'
        )
        
        marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        producto = Producto.objects.create(
            nombre='Test',
            precio=Decimal('10.00'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Calle Test',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
        self.client.login(email='test@test.com', password='testpass123')
        
    def test_cancelacion_exitosa_redirige_a_seguimiento(self):
        """Cancelación exitosa redirige a vista de seguimiento del pedido"""
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.url.endswith(
                reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
            )
        )
        
    def test_cancelacion_sin_acceso_redirige_a_mis_pedidos(self):
        """Usuario sin acceso redirige a mis_pedidos si está autenticado"""
        self.client.logout()
        otro_cliente = Cliente.objects.create_user(
            email='otro@test.com',
            nombre='Otro',
            apellidos='Usuario',
            telefono='600654321',
            password='testpass123'
        )
        self.client.login(email='otro@test.com', password='testpass123')
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse('mis_pedidos')))
        
    def test_cancelacion_anonimo_sin_token_redirige_a_ingresar(self):
        """Usuario anónimo sin token redirige a ingreso de seguimiento"""
        self.client.logout()
        
        response = self.client.post(
            reverse('pedido_cancelar', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse('pedido_seguimiento_ingresar')))