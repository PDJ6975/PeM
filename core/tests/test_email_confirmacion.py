"""
Tests para el envío de emails de confirmación de pedido.
Cubre: envío básico, contenido, casos especiales, errores.
"""
from django.test import TestCase, override_settings
from django.core import mail
from django.conf import settings
from core.models import Cliente, Pedido, ItemPedido, Producto, Marca, Categoria
from decimal import Decimal
from unittest.mock import patch, MagicMock
import logging


class PedidoEmailEnvioBasicoTestCase(TestCase):
    """Tests básicos del envío de email de confirmación"""
    
    def setUp(self):
        """Configuración inicial"""
        self.cliente = Cliente.objects.create_user(
            email='cliente@test.com',
            nombre='Test',
            apellidos='Cliente',
            telefono='600123456',
            password='testpass123'
        )
        
        marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        self.producto = Producto.objects.create(
            nombre='Juguete Test',
            precio=Decimal('15.00'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('15.00'),
            total=Decimal('15.00'),
            direccion_envio='Calle Test 123, 41001 Sevilla',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('15.00')
        )
        
    def test_enviar_email_confirmacion_envia_correo(self):
        """enviar_correo_confirmacion() envía un email"""
        # Limpiar bandeja de salida
        mail.outbox = []
        
        resultado = self.pedido.enviar_correo_confirmacion()
        
        self.assertTrue(resultado)
        self.assertEqual(len(mail.outbox), 1)
        
    def test_email_enviado_a_direccion_correcta(self):
        """Email se envía al email del cliente"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        self.assertIn(self.cliente.email, email.to)
        
    def test_email_tiene_subject_correcto(self):
        """Email tiene asunto con número de pedido"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        self.assertIn('Confirmación de Pedido', email.subject)
        self.assertIn(self.pedido.numero_pedido, email.subject)
        self.assertIn('PeM', email.subject)
        
    def test_email_enviado_desde_remitente_correcto(self):
        """Email se envía desde DEFAULT_FROM_EMAIL configurado"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        # El from_email incluye el nombre: "PeM Store Notifications <no-reply@pem.com>"
        self.assertIn(settings.DEFAULT_FROM_EMAIL, email.from_email)
        
    def test_email_contiene_version_html_y_texto(self):
        """Email contiene versión HTML y texto plano"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        
        # Verificar que tiene contenido HTML
        self.assertTrue(len(email.alternatives) > 0)
        html_content = email.alternatives[0][0]
        self.assertIn('<!DOCTYPE html>', html_content)
        
        # Verificar que tiene texto plano
        self.assertTrue(len(email.body) > 0)


class PedidoEmailContenidoTestCase(TestCase):
    """Tests del contenido del email"""
    
    def setUp(self):
        """Configuración inicial"""
        self.cliente = Cliente.objects.create_user(
            email='cliente@test.com',
            nombre='Juan',
            apellidos='Pérez García',
            telefono='600123456',
            password='testpass123'
        )
        
        marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        
        self.producto1 = Producto.objects.create(
            nombre='Pelota de Goma',
            precio=Decimal('10.00'),
            stock=100,
            marca=marca,
            categoria=categoria
        )
        
        self.producto2 = Producto.objects.create(
            nombre='Cuerda para Morder',
            precio=Decimal('8.50'),
            stock=50,
            marca=marca,
            categoria=categoria
        )
        
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('28.50'),
            total=Decimal('28.50'),
            direccion_envio='Calle Falsa 123, 28001 Madrid',
            telefono='677888999'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=self.producto1,
            cantidad=2,
            precio_unitario=Decimal('10.00')
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=self.producto2,
            cantidad=1,
            precio_unitario=Decimal('8.50')
        )
        
    def test_email_contiene_nombre_cliente(self):
        """Email incluye el nombre del cliente en el saludo"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn('Juan', html_content)
        self.assertIn('Hola', html_content)
        
    def test_email_contiene_numero_pedido(self):
        """Email incluye el número de pedido"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn(self.pedido.numero_pedido, html_content)
        
    def test_email_contiene_tracking_token(self):
        """Email incluye el tracking token"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn(str(self.pedido.tracking_token), html_content)
        
    def test_email_contiene_lista_productos(self):
        """Email incluye la lista de productos con nombres, cantidades y precios"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        # Verificar productos
        self.assertIn('Pelota de Goma', html_content)
        self.assertIn('Cuerda para Morder', html_content)
        
        # Verificar cantidades
        self.assertIn('2', html_content)  # Cantidad del producto 1
        self.assertIn('1', html_content)  # Cantidad del producto 2
        
    def test_email_contiene_total_pedido(self):
        """Email incluye el total del pedido"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn('28,50', html_content)  # Total con formato español
        self.assertIn('€', html_content)
        
    def test_email_contiene_direccion_envio(self):
        """Email incluye la dirección de envío"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn('Calle Falsa 123', html_content)
        self.assertIn('28001 Madrid', html_content)
        
    def test_email_contiene_telefono_contacto(self):
        """Email incluye el teléfono de contacto"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn('677888999', html_content)
        
    def test_email_contiene_link_seguimiento(self):
        """Email incluye enlace para seguimiento del pedido"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        expected_url = f"/pedidos/seguimiento/{self.pedido.numero_pedido}/"
        self.assertIn(expected_url, html_content)
        
    def test_email_contiene_estado_confirmado(self):
        """Email muestra el estado del pedido como 'Confirmado'"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn('Confirmado', html_content)
        
    def test_email_contiene_fecha_pedido(self):
        """Email incluye la fecha de creación del pedido"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        # Verificar que contiene alguna parte de la fecha
        fecha_str = self.pedido.fecha_creacion.strftime('%d/%m/%Y')
        self.assertIn(fecha_str, html_content)
        
    def test_email_contiene_informacion_importante_token(self):
        """Email destaca la importancia del token de seguimiento"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn('importante', html_content.lower())
        self.assertIn('token', html_content.lower())


class PedidoEmailCasosEspecialesTestCase(TestCase):
    """Tests de casos especiales en el envío de email"""
    
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
        
    def test_email_se_envia_para_usuario_autenticado(self):
        """Email se envía correctamente para usuarios autenticados"""
        cliente = Cliente.objects.create_user(
            email='autenticado@test.com',
            nombre='Usuario',
            apellidos='Autenticado',
            telefono='600123456',
            password='testpass123'
        )
        
        pedido = Pedido.objects.create(
            cliente=cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Test',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
        mail.outbox = []
        resultado = pedido.enviar_correo_confirmacion()
        
        self.assertTrue(resultado)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('autenticado@test.com', mail.outbox[0].to)
        
    def test_email_se_envia_para_pedido_stripe(self):
        """Email se envía para pedidos pagados con Stripe"""
        cliente = Cliente.objects.create_user(
            email='stripe@test.com',
            nombre='Pago',
            apellidos='Stripe',
            telefono='600123456',
            password='testpass123'
        )
        
        pedido = Pedido.objects.create(
            cliente=cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Test',
            telefono='600123456',
            stripe_session_id='cs_test_123',
            stripe_payment_intent_id='pi_test_456'
        )
        
        ItemPedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
        mail.outbox = []
        resultado = pedido.enviar_correo_confirmacion()
        
        self.assertTrue(resultado)
        self.assertEqual(len(mail.outbox), 1)
        
    def test_email_se_envia_para_pedido_cod(self):
        """Email se envía para pedidos contrareembolso (sin Stripe)"""
        cliente = Cliente.objects.create_user(
            email='cod@test.com',
            nombre='Pago',
            apellidos='Contrareembolso',
            telefono='600123456',
            password='testpass123'
        )
        
        pedido = Pedido.objects.create(
            cliente=cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Test',
            telefono='600123456',
            stripe_session_id=None,
            stripe_payment_intent_id=None
        )
        
        ItemPedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
        mail.outbox = []
        resultado = pedido.enviar_correo_confirmacion()
        
        self.assertTrue(resultado)
        self.assertEqual(len(mail.outbox), 1)
        
    def test_solo_se_envia_un_email_por_pedido(self):
        """Solo se envía un email al llamar a enviar_correo_confirmacion()"""
        cliente = Cliente.objects.create_user(
            email='unico@test.com',
            nombre='Test',
            apellidos='Unico',
            telefono='600123456',
            password='testpass123'
        )
        
        pedido = Pedido.objects.create(
            cliente=cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Test',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
        mail.outbox = []
        
        pedido.enviar_correo_confirmacion()
        
        self.assertEqual(len(mail.outbox), 1)


class PedidoEmailErroresTestCase(TestCase):
    """Tests de manejo de errores en el envío de email"""
    
    def setUp(self):
        """Configuración inicial"""
        self.cliente = Cliente.objects.create_user(
            email='error@test.com',
            nombre='Test',
            apellidos='Error',
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
            direccion_envio='Test',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
    @patch('core.models.pedido.send_mail')
    def test_fallo_envio_email_retorna_false(self, mock_send_mail):
        """Fallo en envío de email retorna False"""
        mock_send_mail.side_effect = Exception('SMTP Error')
        
        resultado = self.pedido.enviar_correo_confirmacion()
        
        self.assertFalse(resultado)
        
    @patch('core.models.pedido.send_mail')
    def test_fallo_envio_email_se_loguea(self, mock_send_mail):
        """Fallo en envío de email se registra en logs"""
        mock_send_mail.side_effect = Exception('SMTP Error')
        
        with self.assertLogs('core.models.pedido', level='ERROR') as logs:
            self.pedido.enviar_correo_confirmacion()
            
        self.assertTrue(any('Error enviando email' in log for log in logs.output))
        self.assertTrue(any(self.pedido.numero_pedido in log for log in logs.output))
        
    @patch('core.models.pedido.send_mail')
    def test_fallo_envio_email_no_eleva_excepcion(self, mock_send_mail):
        """Fallo en envío de email no eleva excepción (fail gracefully)"""
        mock_send_mail.side_effect = Exception('SMTP Error')
        
        try:
            resultado = self.pedido.enviar_correo_confirmacion()
            self.assertFalse(resultado)
        except Exception:
            self.fail("enviar_correo_confirmacion() elevó una excepción cuando no debería")


class PedidoEmailTemplateTestCase(TestCase):
    """Tests del template HTML del email"""
    
    def setUp(self):
        """Configuración inicial"""
        self.cliente = Cliente.objects.create_user(
            email='template@test.com',
            nombre='Test',
            apellidos='Template',
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
            direccion_envio='Test',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
    def test_email_usa_template_html(self):
        """Email usa el template HTML confirmacion_pedido_email.html"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        # Verificar estructura HTML básica
        self.assertIn('<!DOCTYPE html>', html_content)
        self.assertIn('<html', html_content)
        self.assertIn('</html>', html_content)
        
    def test_email_tiene_estilos_css(self):
        """Email incluye estilos CSS inline"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn('<style', html_content)
        self.assertIn('</style>', html_content)
        
    def test_email_tiene_estructura_responsive(self):
        """Email tiene estructura responsive (viewport meta)"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn('viewport', html_content)
        self.assertIn('device-width', html_content)
        
    def test_email_tiene_header_con_logo(self):
        """Email incluye header con logo/branding"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn('header', html_content.lower())
        self.assertIn('PeM', html_content)
        
    def test_email_tiene_footer(self):
        """Email incluye footer con información de contacto"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn('footer', html_content.lower())
        self.assertIn('2025', html_content)
        
    def test_email_tiene_boton_cta_seguimiento(self):
        """Email incluye botón CTA para ver seguimiento"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn('Ver Seguimiento', html_content)
        self.assertIn('cta', html_content.lower())
        
    def test_email_tiene_tabla_productos(self):
        """Email usa tabla HTML para mostrar productos"""
        mail.outbox = []
        
        self.pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        self.assertIn('<table', html_content)
        self.assertIn('</table>', html_content)
        self.assertIn('<thead', html_content)
        self.assertIn('<tbody', html_content)


class PedidoEmailIntegracionTestCase(TestCase):
    """Tests de integración del envío de email en el flujo completo"""
    
    def setUp(self):
        """Configuración inicial"""
        self.cliente = Cliente.objects.create_user(
            email='integracion@test.com',
            nombre='Test',
            apellidos='Integración',
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
        
    def test_email_se_envia_al_crear_pedido_en_checkout_success(self):
        """Email se envía automáticamente al crear pedido (simulado)"""
        mail.outbox = []
        
        # Simular creación de pedido como en checkout_success
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Test',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
        # Llamar manualmente (en views.py se llama desde _crear_pedido_desde_carrito)
        pedido.enviar_correo_confirmacion()
        
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.cliente.email, mail.outbox[0].to)
        
    def test_email_incluye_todos_los_productos_del_pedido(self):
        """Email incluye todos los productos cuando hay múltiples items"""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('30.00'),
            total=Decimal('30.00'),
            direccion_envio='Test',
            telefono='600123456'
        )
        
        marca, _ = Marca.objects.get_or_create(nombre='Trixie')
        categoria, _ = Categoria.objects.get_or_create(nombre='Juguetes')
        
        productos = []
        for i in range(3):
            prod = Producto.objects.create(
                nombre=f'Producto {i+1}',
                precio=Decimal('10.00'),
                stock=100,
                marca=marca,
                categoria=categoria
            )
            productos.append(prod)
            
            ItemPedido.objects.create(
                pedido=pedido,
                producto=prod,
                cantidad=1,
                precio_unitario=Decimal('10.00')
            )
        
        mail.outbox = []
        pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        # Verificar que todos los productos aparecen
        for prod in productos:
            self.assertIn(prod.nombre, html_content)
            
    def test_contexto_email_tiene_todas_las_variables_necesarias(self):
        """Template recibe todas las variables de contexto necesarias"""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='confirmado',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            direccion_envio='Test',
            telefono='600123456'
        )
        
        ItemPedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('10.00')
        )
        
        mail.outbox = []
        pedido.enviar_correo_confirmacion()
        
        email = mail.outbox[0]
        html_content = email.alternatives[0][0]
        
        # Verificar variables del contexto renderizadas
        self.assertIn(pedido.numero_pedido, html_content)  # numero_pedido
        self.assertIn(str(pedido.tracking_token), html_content)  # tracking_token
        self.assertIn(self.cliente.nombre, html_content)  # cliente.nombre
        self.assertIn(settings.SITE_URL, html_content)  # site_url