from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal
import uuid
from django.core.mail import send_mail
from django.conf import settings


class Pedido(models.Model):
    """
    Modelo para representar los pedidos realizados por los clientes.
    """

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    # Relación con cliente
    cliente = models.ForeignKey(
        'Cliente',
        on_delete=models.PROTECT,
        related_name='pedidos',
        help_text='Cliente que realizó el pedido'
    )

    # Información del pedido
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        help_text='Fecha y hora de creación del pedido'
    )

    numero_pedido = models.CharField(
        max_length=50,
        unique=True,
        help_text='Número único del pedido para seguimiento'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        help_text='Estado actual del pedido'
    )

    # Montos
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Subtotal del pedido (sin impuestos ni envío)'
    )

    impuestos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Impuestos aplicados al pedido'
    )

    coste_entrega = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Coste de envío del pedido'
    )

    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Descuento aplicado al pedido'
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Total final del pedido'
    )

    # Campos específicos para Stripe
    stripe_payment_intent_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='ID del PaymentIntent de Stripe'
    )

    stripe_session_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='ID de la sesión de Checkout de Stripe'
    )

    # Información de envío
    direccion_envio = models.TextField(
        help_text='Dirección completa de envío del pedido'
    )

    telefono = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="El teléfono debe tener entre 9 y 15 dígitos."
        )],
        help_text='Teléfono de contacto para el envío'
    )

    tracking_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Token único para seguimiento de pedido sin cuenta"
    )

    # Auditoría
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        help_text='Última fecha de actualización del pedido'
    )

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['cliente']),
            models.Index(fields=['numero_pedido']),
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_creacion']),
        ]

    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.cliente.email}"

    def save(self, *args, **kwargs):
        """
        Genera automáticamente el número de pedido si no existe.
        Calcula automáticamente el total del pedido.
        """
        if not self.numero_pedido:
            self.numero_pedido = self.generar_numero_pedido()
        
        self.total = self.calcular_total()
        
        super().save(*args, **kwargs)

    def generar_numero_pedido(self):
        """
        Genera un número de pedido único.
        """
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4().hex)[:8].upper()
        return f"PED-{timestamp}-{unique_id}"

    def total_items(self):
        """
        Calcula el número total de productos en el pedido.
        """
        return sum(item.cantidad for item in self.items.all())

    def calcular_total(self):
        """
        Calcula el total del pedido: subtotal + impuestos + envío - descuento.
        """
        return self.subtotal + self.impuestos + self.coste_entrega - self.descuento

    def puede_cancelar(self):
        """
        Verifica si el pedido puede ser cancelado por el administrador.
        Solo los pedidos pendientes o confirmados pueden cancelarse.
        """
        return self.estado in ['pendiente', 'confirmado']

    def puede_modificar(self):
        """
        Verifica si el pedido puede ser modificado por el administrador.
        Solo los pedidos pendientes pueden modificarse.
        """
        return self.estado == 'pendiente'

    def cancelar_pedido(self):
        """
        Cancela el pedido si es posible.
        """
        if self.puede_cancelar():
            self.estado = 'cancelado'
            self.save()
            return True
        return False

    def confirmar_pedido(self):
        """
        Confirma el pedido si está pendiente.
        """
        if self.estado == 'pendiente':
            self.estado = 'confirmado'
            self.save()
            return True
        return False

    def marcar_como_enviado(self):
        """
        Marca el pedido como enviado si está confirmado.
        """
        if self.estado == 'confirmado':
            self.estado = 'enviado'
            self.save()
            return True
        return False

    def marcar_como_entregado(self):
        """
        Marca el pedido como entregado si está enviado.
        """
        if self.estado == 'enviado':
            self.estado = 'entregado'
            self.save()
            return True
        return False
    
    def get_tracking_url(self):
        """
        Devuelve la URL completa para el seguimiento del pedido.
        """
        base_url = getattr(settings, "SITE_URL", "http://localhost:8000")
        return f"{base_url}/seguimiento/{self.tracking_token}/"

    def enviar_correo_tracking(self):
        """
        Envía un correo con la información del pedido y el enlace de seguimiento.
        """
        asunto = f"Confirmación de tu pedido {self.numero_pedido}"
        mensaje = (
            f"¡Gracias por tu compra!\n\n"
            f"Tu pedido ha sido recibido correctamente.\n"
            f"Puedes consultar su estado en cualquier momento en el siguiente enlace:\n\n"
            f"{self.get_tracking_url()}\n\n"
            f"Resumen:\n"
            f"Estado: {self.estado}\n"
            f"Total: {self.total} €\n\n"
            f"PeM - Juguetes para Mascotas"
        )
        remitente = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pem.com")
        destinatario = [self.cliente.email]
        send_mail(asunto, mensaje, remitente, destinatario)
