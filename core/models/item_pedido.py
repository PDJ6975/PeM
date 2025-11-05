from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class ItemPedido(models.Model):
    """
    Modelo para representar un producto individual dentro de un pedido.
    Vincula el pedido con productos específicos y sus detalles al momento de la compra.
    """

    # Relaciones
    pedido = models.ForeignKey(
        'Pedido',
        on_delete=models.CASCADE,
        related_name='items',
        help_text='Pedido al que pertenece este item'
    )

    producto = models.ForeignKey(
        'Producto',
        on_delete=models.PROTECT,
        related_name='items_pedido',
        help_text='Producto incluido en el pedido'
    )

    # Información del producto al momento de la compra

    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text='Cantidad de unidades del producto'
    )

    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Precio unitario del producto al momento de la compra'
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Total de este item (precio_unitario * cantidad)'
    )

    class Meta:
        verbose_name = 'Item de Pedido'
        verbose_name_plural = 'Items de Pedido'
        ordering = ['id']
        indexes = [
            models.Index(fields=['pedido', 'producto']),
            models.Index(fields=['producto']),
        ]

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} - Pedido {self.pedido.numero_pedido}"

    def save(self, *args, **kwargs):
        """
        Calcula automáticamente el total al guardar.
        """
        self.total = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)

    def subtotal(self):
        """
        Calcula el subtotal de este item (precio_unitario * cantidad).
        """
        return self.precio_unitario * self.cantidad