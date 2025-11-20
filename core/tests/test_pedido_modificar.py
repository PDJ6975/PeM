"""
Tests para la funcionalidad de Modificar Pedido
Cubre: acceso, permisos, validaciones, actualización de datos
"""
from django.test import TestCase, Client
from django.urls import reverse
from core.models import Cliente, Pedido, ItemPedido, Producto, Marca, Categoria
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class PedidoModificarAccessTestCase(TestCase):
    """Tests de control de acceso a la vista de modificación"""
    
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
        
        # Pedido modificable
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',  # Estado que permite modificación
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
        
    def test_propietario_autenticado_puede_acceder(self):
        """Propietario autenticado puede acceder a modificar su pedido"""
        self.client.login(email='propietario@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/pedido_modificar.html')
        self.assertContains(response, self.pedido.numero_pedido)
        
    def test_no_propietario_autenticado_sin_acceso(self):
        """Usuario autenticado NO propietario no puede modificar pedido ajeno"""
        self.client.login(email='otro@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        # Debe redirigir con mensaje de error
        self.assertEqual(response.status_code, 302)
        self.assertIn('mis-pedidos', response.url)
        
    def test_staff_puede_modificar_cualquier_pedido(self):
        """Staff puede modificar cualquier pedido"""
        self.client.login(email='staff@test.com', password='staffpass123')
        
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 200)
        
    def test_usuario_anonimo_sin_token_no_tiene_acceso(self):
        """Usuario anónimo sin token temporal no puede acceder"""
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse('pedido_seguimiento_ingresar')))
        
    def test_usuario_anonimo_con_token_valido_puede_modificar(self):
        """Usuario anónimo con token temporal válido puede modificar"""
        session = self.client.session
        session['pedido_acceso_temporal'] = {
            'numero_pedido': self.pedido.numero_pedido,
            'tracking_token': str(self.pedido.tracking_token),
            'timestamp': timezone.now().isoformat()
        }
        session.save()
        
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 200)
        
    def test_usuario_anonimo_con_token_expirado_sin_acceso(self):
        """Usuario anónimo con token expirado (>1h) no puede modificar"""
        session = self.client.session
        session['pedido_acceso_temporal'] = {
            'numero_pedido': self.pedido.numero_pedido,
            'tracking_token': str(self.pedido.tracking_token),
            'timestamp': (timezone.now() - timedelta(hours=2)).isoformat()
        }
        session.save()
        
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 302)


class PedidoModificarEstadosTestCase(TestCase):
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
        
    def test_pedido_pendiente_puede_modificarse(self):
        """Pedido en estado 'pendiente' puede modificarse"""
        pedido = self._crear_pedido_con_estado('pendiente')
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_modificar', args=[pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 200)
        
    def test_pedido_confirmado_puede_modificarse(self):
        """Pedido en estado 'confirmado' puede modificarse"""
        pedido = self._crear_pedido_con_estado('confirmado')
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_modificar', args=[pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 200)
        
    def test_pedido_enviado_no_puede_modificarse(self):
        """Pedido en estado 'enviado' NO puede modificarse"""
        pedido = self._crear_pedido_con_estado('enviado')
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_modificar', args=[pedido.numero_pedido])
        )
        
        # Redirige a seguimiento con mensaje
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.url.endswith(
                reverse('pedido_seguimiento', args=[pedido.numero_pedido])
            )
        )
        
    def test_pedido_entregado_no_puede_modificarse(self):
        """Pedido en estado 'entregado' NO puede modificarse"""
        pedido = self._crear_pedido_con_estado('entregado')
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_modificar', args=[pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 302)
        
    def test_pedido_cancelado_no_puede_modificarse(self):
        """Pedido en estado 'cancelado' NO puede modificarse"""
        pedido = self._crear_pedido_con_estado('cancelado')
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_modificar', args=[pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 302)


class PedidoModificarFormularioTestCase(TestCase):
    """Tests del formulario de modificación"""
    
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
            direccion_envio='Dirección Original 123',
            telefono='600111111'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
        self.client.login(email='test@test.com', password='testpass123')
        
    def test_formulario_muestra_datos_actuales(self):
        """Formulario muestra los datos actuales del pedido"""
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, 'Dirección Original 123')
        self.assertContains(response, '600111111')
        
    def test_modificar_direccion_actualiza_correctamente(self):
        """POST con nueva dirección actualiza el pedido"""
        nueva_direccion = 'Nueva Dirección 456, Barcelona'
        
        response = self.client.post(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido]),
            {
                'direccion_envio': nueva_direccion,
                'telefono': '600111111'
            }
        )
        
        # Redirige a seguimiento tras éxito
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.url.endswith(
                reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
            )
        )
        
        # Verificar actualización en BD
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.direccion_envio, nueva_direccion)
        
    def test_modificar_telefono_actualiza_correctamente(self):
        """POST con nuevo teléfono actualiza el pedido"""
        nuevo_telefono = '677888999'
        
        response = self.client.post(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido]),
            {
                'direccion_envio': 'Dirección Original 123',
                'telefono': nuevo_telefono
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.telefono, nuevo_telefono)
        
    def test_modificar_ambos_campos_actualiza_correctamente(self):
        """POST con dirección y teléfono nuevos actualiza ambos"""
        nueva_direccion = 'Calle Nueva 789'
        nuevo_telefono = '644555666'
        
        response = self.client.post(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido]),
            {
                'direccion_envio': nueva_direccion,
                'telefono': nuevo_telefono
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.direccion_envio, nueva_direccion)
        self.assertEqual(self.pedido.telefono, nuevo_telefono)
        
    def test_direccion_con_espacios_se_limpia(self):
        """POST con dirección con espacios extra se limpia"""
        response = self.client.post(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido]),
            {
                'direccion_envio': '   Dirección Limpia   ',
                'telefono': '600111111'
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.direccion_envio, 'Dirección Limpia')
        
    def test_campos_required_en_template(self):
        """Campos tienen atributo 'required' en el HTML"""
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        # Verificar que textarea tiene 'required'
        self.assertContains(response, 'name="direccion_envio"')
        self.assertContains(response, 'required>')
        
        # Verificar que input teléfono tiene 'required'
        self.assertContains(response, 'name="telefono"')
        self.assertContains(response, 'type="tel"')


class PedidoModificarTemplateTestCase(TestCase):
    """Tests de renderizado del template"""
    
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
            nombre='Aro Mordedor Test',
            precio=Decimal('15.50'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('31.00'),
            total=Decimal('31.00'),
            direccion_envio='Calle Test 123',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=2,
            precio_unitario=Decimal('15.50')
        )
        
        self.client.login(email='test@test.com', password='testpass123')
        
    def test_muestra_alerta_informativa(self):
        """Template muestra alerta sobre qué se puede modificar"""
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, 'Solo puedes modificar')
        self.assertContains(response, 'datos de entrega')
        
    def test_muestra_resumen_pedido(self):
        """Template muestra resumen con productos del pedido"""
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, 'Resumen del Pedido')
        self.assertContains(response, self.producto.nombre)
        self.assertContains(response, '2')  # Cantidad
        
    def test_muestra_total_pedido(self):
        """Template muestra el total del pedido (formato español)"""
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, '31,00')  # Total en formato español
        
    def test_muestra_botones_accion(self):
        """Template muestra botones de guardar y cancelar"""
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, 'Guardar Cambios')
        self.assertContains(response, 'Cancelar')
        
    def test_boton_cancelar_enlaza_a_seguimiento(self):
        """Botón Cancelar enlaza a la vista de seguimiento"""
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        
        seguimiento_url = reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        self.assertContains(response, seguimiento_url)


class PedidoModificarMensajesTestCase(TestCase):
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
            direccion_envio='Calle Original',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
        self.client.login(email='test@test.com', password='testpass123')
        
    def test_modificacion_exitosa_muestra_mensaje_success(self):
        """Modificación exitosa muestra mensaje de éxito"""
        response = self.client.post(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido]),
            {
                'direccion_envio': 'Nueva Dirección',
                'telefono': '677888999'
            },
            follow=True  # Seguir redirección para ver mensajes
        )
        
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('actualizado correctamente', str(messages[0]))
        
    def test_pedido_no_modificable_muestra_mensaje_warning(self):
        """Pedido en estado no modificable muestra advertencia"""
        self.pedido.estado = 'enviado'
        self.pedido.save()
        
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido]),
            follow=True
        )
        
        messages = list(response.context['messages'])
        self.assertTrue(any('no puede ser modificado' in str(m) for m in messages))
        
    def test_acceso_no_autorizado_muestra_mensaje_error(self):
        """Acceso no autorizado muestra mensaje de error"""
        # Logout y login como otro usuario
        self.client.logout()
        otro_cliente = Cliente.objects.create_user(
            email='otro@test.com',
            nombre='Otro',
            apellidos='Usuario',
            telefono='600654321',
            password='testpass123'
        )
        self.client.login(email='otro@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido]),
            follow=True
        )
        
        messages = list(response.context['messages'])
        self.assertTrue(any('No tienes acceso' in str(m) for m in messages))


class PedidoModificarIntegracionTestCase(TestCase):
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
            direccion_envio='Dirección Original',
            telefono='600111111'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
    def test_flujo_completo_modificacion_exitosa(self):
        """Test de flujo completo: login → modificar → ver cambios"""
        # 1. Login
        self.client.login(email='test@test.com', password='testpass123')
        
        # 2. Acceder a modificar
        response = self.client.get(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido])
        )
        self.assertEqual(response.status_code, 200)
        
        # 3. Enviar modificación
        nueva_direccion = 'Passatge de Domingo 3, Barcelona'
        nuevo_telefono = '644555666'
        
        response = self.client.post(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido]),
            {
                'direccion_envio': nueva_direccion,
                'telefono': nuevo_telefono
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        # 4. Verificar en vista de seguimiento
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, nueva_direccion)
        self.assertContains(response, nuevo_telefono)
        
    def test_no_se_modifican_productos_ni_totales(self):
        """Modificar NO cambia productos, cantidades ni totales"""
        self.client.login(email='test@test.com', password='testpass123')
        
        total_original = self.pedido.total
        subtotal_original = self.pedido.subtotal
        num_items_original = self.pedido.items.count()
        
        self.client.post(
            reverse('pedido_modificar', args=[self.pedido.numero_pedido]),
            {
                'direccion_envio': 'Nueva Dirección',
                'telefono': '677888999'
            }
        )
        
        self.pedido.refresh_from_db()
        
        # Verificar que totales no cambiaron
        self.assertEqual(self.pedido.total, total_original)
        self.assertEqual(self.pedido.subtotal, subtotal_original)
        
        # Verificar que items no cambiaron
        self.assertEqual(self.pedido.items.count(), num_items_original)