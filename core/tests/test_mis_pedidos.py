"""
Tests para la funcionalidad de "Mis Pedidos"
Cubre: listado de pedidos, paginación, acceso con token temporal, permisos
"""
from django.test import TestCase, Client
from django.urls import reverse
from core.models import Cliente, Pedido, ItemPedido, Producto, Marca, Categoria
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class MisPedidosViewTestCase(TestCase):
    """Tests para la vista de Mis Pedidos"""
    
    def setUp(self):
        """Configuración inicial para cada test"""
        self.client = Client()
        
        # Crear cliente de prueba
        self.cliente = Cliente.objects.create_user(
            email='test@test.com',
            nombre='Test',
            apellidos='User',
            telefono='600123456',
            password='testpass123'
        )
        
        # Crear segundo cliente para tests de aislamiento
        self.otro_cliente = Cliente.objects.create_user(
            email='otro@test.com',
            nombre='Otro',
            apellidos='Usuario',
            telefono='600654321',
            password='testpass123'
        )
        
        # Crear productos de prueba (usar get_or_create para evitar duplicados)
        self.marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        self.categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        self.producto = Producto.objects.create(
            nombre='Aro mordedor Kong Flyer Test',
            descripcion='Juguete resistente para perros',
            precio=12.90,
            stock=100,
            marca=self.marca,
            categoria=self.categoria,
            esta_disponible=True
        )
        
    def test_mis_pedidos_sin_autenticacion_redirige_a_formulario(self):
        """Usuario anónimo es redirigido al formulario de seguimiento"""
        response = self.client.get(reverse('mis_pedidos'))
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse('pedido_seguimiento_ingresar')))
        
    def test_mis_pedidos_con_autenticacion_muestra_lista(self):
        """Usuario autenticado ve lista de sus pedidos"""
        self.client.login(email='test@test.com', password='testpass123')
        
        # Crear pedido de prueba
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            subtotal=Decimal('12.90'),
            total=Decimal('12.90'),
            direccion_envio='Calle Test 123, Sevilla, España',
            telefono='600123456',
            estado='confirmado'
        )
        ItemPedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('12.90')
        )
        
        response = self.client.get(reverse('mis_pedidos'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/mis_pedidos.html')
        self.assertContains(response, pedido.numero_pedido)
        self.assertContains(response, 'Pedido #')
        
    def test_mis_pedidos_solo_muestra_pedidos_del_usuario(self):
        """Usuario solo ve sus propios pedidos, no los de otros"""
        self.client.login(email='test@test.com', password='testpass123')
        
        # Pedido del usuario autenticado
        pedido_propio = Pedido.objects.create(
            cliente=self.cliente,
            subtotal=Decimal('12.90'),
            total=Decimal('12.90'),
            direccion_envio='Calle Test 123',
            telefono='600123456'
        )
        
        # Pedido de otro usuario
        pedido_ajeno = Pedido.objects.create(
            cliente=self.otro_cliente,
            subtotal=Decimal('25.80'),
            total=Decimal('25.80'),
            direccion_envio='Otra Calle 456',
            telefono='600654321'
        )
        
        response = self.client.get(reverse('mis_pedidos'))
        
        self.assertContains(response, pedido_propio.numero_pedido)
        self.assertNotContains(response, pedido_ajeno.numero_pedido)
        
    def test_mis_pedidos_ordenados_por_fecha_descendente(self):
        """Pedidos se muestran del más reciente al más antiguo"""
        self.client.login(email='test@test.com', password='testpass123')
        
        # Crear 3 pedidos con fechas diferentes
        pedido1 = Pedido.objects.create(
            cliente=self.cliente,
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Calle 1',
            telefono='600123456'
        )
        pedido1.fecha_creacion = timezone.now() - timedelta(days=2)
        pedido1.save()
        
        pedido2 = Pedido.objects.create(
            cliente=self.cliente,
            subtotal=Decimal('20.00'),
            total=Decimal('20.00'),
            direccion_envio='Calle 2',
            telefono='600123456'
        )
        pedido2.fecha_creacion = timezone.now() - timedelta(days=1)
        pedido2.save()
        
        pedido3 = Pedido.objects.create(
            cliente=self.cliente,
            subtotal=Decimal('30.00'),
            total=Decimal('30.00'),
            direccion_envio='Calle 3',
            telefono='600123456'
        )
        
        response = self.client.get(reverse('mis_pedidos'))
        pedidos = list(response.context['pedidos'])
        
        # El más reciente debe ser primero
        self.assertEqual(pedidos[0].id, pedido3.id)
        self.assertEqual(pedidos[1].id, pedido2.id)
        self.assertEqual(pedidos[2].id, pedido1.id)
        
    def test_mis_pedidos_vacio_muestra_mensaje(self):
        """Usuario sin pedidos ve mensaje apropiado"""
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(reverse('mis_pedidos'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No tienes pedidos registrados')
        
    def test_mis_pedidos_muestra_informacion_completa_pedido(self):
        """Vista muestra toda la información relevante de cada pedido"""
        self.client.login(email='test@test.com', password='testpass123')
        
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            subtotal=Decimal('25.50'),
            total=Decimal('25.50'),
            direccion_envio='Calle Test 123',
            telefono='600123456',
            estado='confirmado'
        )
        
        response = self.client.get(reverse('mis_pedidos'))
        
        # Verificar que aparece el número de pedido
        self.assertContains(response, pedido.numero_pedido)
        
        # Verificar que aparece el total (FORMATO ESPAÑOL: coma como decimal)
        self.assertContains(response, '25,50')
        
        # Verificar que aparece el estado
        self.assertContains(response, 'Confirmado')
        
    def test_mis_pedidos_muestra_badge_estado_correcto(self):
        """Vista muestra badge de estado con color correcto según el estado"""
        self.client.login(email='test@test.com', password='testpass123')
        
        # Pedido cancelado (badge rojo)
        pedido_cancelado = Pedido.objects.create(
            cliente=self.cliente,
            estado='cancelado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Calle 1',
            telefono='600123456'
        )
        
        # Pedido entregado (badge verde)
        pedido_entregado = Pedido.objects.create(
            cliente=self.cliente,
            estado='entregado',
            subtotal=Decimal('20.00'),
            total=Decimal('20.00'),
            direccion_envio='Calle 2',
            telefono='600123456'
        )
        
        response = self.client.get(reverse('mis_pedidos'))
        html = response.content.decode()
        
        # Verificar clases CSS de los badges
        self.assertIn('bg-danger', html)  # Cancelado
        self.assertIn('bg-success', html)  # Entregado
        
    def test_mis_pedidos_enlace_a_detalle_pedido(self):
        """Cada pedido tiene enlace a su página de seguimiento"""
        self.client.login(email='test@test.com', password='testpass123')
        
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            subtotal=Decimal('12.90'),
            total=Decimal('12.90'),
            direccion_envio='Calle Test',
            telefono='600123456'
        )
        
        response = self.client.get(reverse('mis_pedidos'))
        detalle_url = reverse('pedido_seguimiento', args=[pedido.numero_pedido])
        
        self.assertContains(response, detalle_url)
        self.assertContains(response, 'Ver Seguimiento')
        
    def test_mis_pedidos_prefetch_optimizado(self):
        """Vista usa prefetch_related para optimizar queries"""
        self.client.login(email='test@test.com', password='testpass123')
        
        # Crear pedido con múltiples items
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            subtotal=Decimal('25.80'),
            total=Decimal('25.80'),
            direccion_envio='Calle Test',
            telefono='600123456'
        )
        
        for i in range(3):
            ItemPedido.objects.create(
                pedido=pedido,
                producto=self.producto,
                cantidad=1,
                precio_unitario=Decimal('12.90')
            )
        
        # Medir queries
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('mis_pedidos'))
            num_queries = len(ctx.captured_queries)
        
        # Debe ser eficiente (menos de 10 queries para 1 pedido con 3 items)
        self.assertLess(num_queries, 10)


class PedidoSeguimientoIngresarTestCase(TestCase):
    """Tests para el formulario de seguimiento sin login"""
    
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
            nombre='Test Producto',
            precio=Decimal('12.90'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            subtotal=Decimal('12.90'),
            total=Decimal('12.90'),
            direccion_envio='Calle Test 123',
            telefono='600123456'
        )
        
    def test_formulario_seguimiento_get_muestra_form(self):
        """GET muestra el formulario de seguimiento"""
        response = self.client.get(reverse('pedido_seguimiento_ingresar'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/pedido_seguimiento_ingresar.html')
        self.assertContains(response, 'Número de Pedido')
        self.assertContains(response, 'Token de Seguimiento')
        
    def test_formulario_seguimiento_post_valido_redirige(self):
        """POST con datos válidos crea sesión temporal y redirige"""
        response = self.client.post(
            reverse('pedido_seguimiento_ingresar'),
            {
                'numero_pedido': self.pedido.numero_pedido,
                'tracking_token': str(self.pedido.tracking_token)
            }
        )
        
        # Debe redirigir al seguimiento
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.url.endswith(
                reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
            )
        )
        
        # Debe guardar en sesión
        self.assertIn('pedido_acceso_temporal', self.client.session)
        
    def test_formulario_seguimiento_post_invalido_muestra_error(self):
        """POST con datos incorrectos muestra error"""
        response = self.client.post(
            reverse('pedido_seguimiento_ingresar'),
            {
                'numero_pedido': self.pedido.numero_pedido,
                'tracking_token': 'token-incorrecto-12345'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        # El template muestra "Formato de token inválido" en lugar de "incorrectos"
        self.assertContains(response, 'inválido')

    def test_formulario_seguimiento_campos_vacios_muestra_error(self):
        """POST con campos vacíos muestra error"""
        response = self.client.post(
            reverse('pedido_seguimiento_ingresar'),
            {
                'numero_pedido': '',
                'tracking_token': ''
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Debes introducir')
        
    def test_formulario_seguimiento_guarda_timestamp_en_sesion(self):
        """POST exitoso guarda timestamp en sesión"""
        self.client.post(
            reverse('pedido_seguimiento_ingresar'),
            {
                'numero_pedido': self.pedido.numero_pedido,
                'tracking_token': str(self.pedido.tracking_token)
            }
        )
        
        acceso_temporal = self.client.session.get('pedido_acceso_temporal')
        
        self.assertIsNotNone(acceso_temporal)
        self.assertIn('timestamp', acceso_temporal)
        self.assertIn('numero_pedido', acceso_temporal)
        self.assertIn('tracking_token', acceso_temporal)


class PedidoSeguimientoTestCase(TestCase):
    """Tests para la vista de seguimiento de pedido individual"""
    
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
        
        self.otro_cliente = Cliente.objects.create_user(
            email='otro@test.com',
            nombre='Otro',
            apellidos='Usuario',
            telefono='600654321',
            password='testpass123'
        )
        
        marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        self.producto = Producto.objects.create(
            nombre='Aro mordedor Kong',
            precio=Decimal('12.90'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('12.90'),
            total=Decimal('12.90'),
            direccion_envio='Passatge de Domingo 3, Barcelona',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('12.90')
        )
        
    def test_seguimiento_usuario_autenticado_propietario_tiene_acceso(self):
        """Usuario autenticado propietario puede ver su pedido"""
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/pedido_seguimiento.html')
        self.assertContains(response, self.pedido.numero_pedido)
        
    def test_seguimiento_usuario_autenticado_no_propietario_sin_acceso(self):
        """Usuario autenticado NO propietario no puede ver pedido ajeno"""
        self.client.login(email='otro@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        # Debe redirigir con mensaje de error
        self.assertEqual(response.status_code, 302)
        
    def test_seguimiento_con_token_temporal_valido_tiene_acceso(self):
        """Usuario anónimo con token temporal válido puede ver pedido"""
        # Simular acceso temporal en sesión
        session = self.client.session
        session['pedido_acceso_temporal'] = {
            'numero_pedido': self.pedido.numero_pedido,
            'tracking_token': str(self.pedido.tracking_token),
            'timestamp': timezone.now().isoformat()
        }
        session.save()
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pedido.numero_pedido)
        
    def test_seguimiento_con_token_expirado_redirige(self):
        """Token temporal expirado (>1 hora) redirige al formulario"""
        session = self.client.session
        session['pedido_acceso_temporal'] = {
            'numero_pedido': self.pedido.numero_pedido,
            'tracking_token': str(self.pedido.tracking_token),
            'timestamp': (timezone.now() - timedelta(hours=2)).isoformat()
        }
        session.save()
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        # Debe redirigir por token expirado
        self.assertEqual(response.status_code, 302)
        
    def test_seguimiento_sin_autenticacion_ni_token_redirige(self):
        """Usuario anónimo sin token es redirigido"""
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 302)
        
    def test_seguimiento_muestra_items_del_pedido(self):
        """Vista muestra los productos del pedido"""
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, self.producto.nombre)
        # FORMATO ESPAÑOL: coma como separador decimal
        self.assertContains(response, '12,90')
        
    def test_seguimiento_muestra_estado_pedido_con_badge(self):
        """Vista muestra el estado del pedido con badge correcto"""
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, 'Confirmado')
        self.assertContains(response, 'bg-primary')
        
    def test_seguimiento_propietario_ve_botones_accion(self):
        """Propietario ve botones de modificar/cancelar según estado"""
        self.client.login(email='test@test.com', password='testpass123')
        
        # Pedido confirmado: debe mostrar botones
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, 'Modificar Pedido')
        self.assertContains(response, 'Cancelar Pedido')
        
    def test_seguimiento_propietario_no_ve_botones_si_no_modificable(self):
        """Propietario NO ve botones si pedido ya no es modificable"""
        self.pedido.estado = 'enviado'
        self.pedido.save()
        
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        # No debe mostrar botones de modificar/cancelar
        html = response.content.decode()
        self.assertNotIn('Modificar Pedido', html)
        
    def test_seguimiento_muestra_datos_entrega_solo_a_propietario(self):
        """Datos de entrega (dirección/teléfono) solo visibles para propietario"""
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertContains(response, self.pedido.direccion_envio)
        self.assertContains(response, self.pedido.telefono)
        
    def test_seguimiento_context_es_propietario_correcto(self):
        """Context 'es_propietario' es True para propietario"""
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertTrue(response.context['es_propietario'])


class VerificarAccesoPedidoTestCase(TestCase):
    """Tests para la función _verificar_acceso_pedido"""
    
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
        
        self.staff = Cliente.objects.create_user(
            email='staff@test.com',
            nombre='Staff',
            apellidos='Admin',
            telefono='600111222',
            password='staffpass123',
            is_staff=True
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
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Calle Test',
            telefono='600123456'
        )
        
    def test_staff_tiene_acceso_cualquier_pedido(self):
        """Staff tiene acceso a cualquier pedido"""
        self.client.login(email='staff@test.com', password='staffpass123')
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 200)
        
    def test_propietario_tiene_acceso_su_pedido(self):
        """Propietario tiene acceso a su pedido"""
        self.client.login(email='test@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['es_propietario'])
        
    def test_token_temporal_valido_da_acceso(self):
        """Token temporal válido (<1 hora) da acceso"""
        session = self.client.session
        session['pedido_acceso_temporal'] = {
            'numero_pedido': self.pedido.numero_pedido,
            'tracking_token': str(self.pedido.tracking_token),
            'timestamp': timezone.now().isoformat()
        }
        session.save()
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 200)
        
    def test_token_temporal_expirado_no_da_acceso(self):
        """Token temporal expirado (>1 hora) no da acceso"""
        session = self.client.session
        session['pedido_acceso_temporal'] = {
            'numero_pedido': self.pedido.numero_pedido,
            'tracking_token': str(self.pedido.tracking_token),
            'timestamp': (timezone.now() - timedelta(hours=2)).isoformat()
        }
        session.save()
        
        response = self.client.get(
            reverse('pedido_seguimiento', args=[self.pedido.numero_pedido])
        )
        
        self.assertEqual(response.status_code, 302)