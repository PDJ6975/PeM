from django.db import models
from django.utils import timezone


class Carrito(models.Model):
    """
    Modelo para representar el carrito de compras temporal de un cliente.
    Permite compras sin registro (carrito de sesión) o con cliente registrado.
    """

    cliente = models.ForeignKey(
        'Cliente',
        on_delete=models.CASCADE,
        related_name='carritos',
        null=True,
        blank=True,
        help_text='Cliente propietario del carrito (null para carritos de sesión anónima)'
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        help_text='Fecha de creación del carrito'
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        help_text='Última modificación del carrito'
    )

    class Meta:
        verbose_name = 'Carrito'
        verbose_name_plural = 'Carritos'
        ordering = ['-fecha_actualizacion']
        indexes = [
            models.Index(fields=['cliente']),
            models.Index(fields=['fecha_actualizacion']),
        ]

    def __str__(self):
        if self.cliente:
            return f"Carrito de {self.cliente.email}"
        return f"Carrito anónimo #{self.id}"

    def total_items(self):
        """Calcula el número total de productos en el carrito"""
        return sum(item.cantidad for item in self.items.all())

    def subtotal(self):
        """Calcula el subtotal del carrito (suma de todos los items)"""
        return sum(item.subtotal() for item in self.items.all())

    def esta_vacio(self):
        """Verifica si el carrito está vacío"""
        return not self.items.exists()
