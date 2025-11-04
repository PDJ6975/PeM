from django.db import models
from django.core.validators import MinValueValidator


class ItemCarrito(models.Model):
    """
    Modelo para representar un producto individual dentro del carrito.
    Vincula el carrito con productos específicos y sus cantidades.
    """

    carrito = models.ForeignKey(
        'Carrito',
        on_delete=models.CASCADE,
        related_name='items',
        help_text='Carrito al que pertenece este item'
    )

    producto = models.ForeignKey(
        'Producto',
        on_delete=models.CASCADE,
        related_name='items_carrito',
        help_text='Producto agregado al carrito'
    )

    cantidad = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Cantidad de unidades del producto'
    )

    class Meta:
        verbose_name = 'Item de Carrito'
        verbose_name_plural = 'Items de Carrito'
        ordering = ['id']
        unique_together = ['carrito', 'producto']
        indexes = [
            models.Index(fields=['carrito', 'producto']),
        ]

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} en {self.carrito}"

    def subtotal(self):
        """Calcula el subtotal de este item (precio_actual * cantidad)"""
        return self.producto.precio_actual() * self.cantidad

    def puede_agregar_cantidad(self, cantidad_adicional=1):
        """Verifica si hay stock suficiente para agregar más unidades"""
        return (self.cantidad + cantidad_adicional) <= self.producto.stock

    def precio_unitario(self):
        """Devuelve el precio unitario actual del producto"""
        return self.producto.precio_actual()
