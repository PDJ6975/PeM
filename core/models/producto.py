from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Producto(models.Model):
    """
    Modelo para representar los productos de la tienda.
    """

    GENERO_CHOICES = [
        ('perro', 'Perro'),
        ('gato', 'Gato'),
        ('ambos', 'Ambos'),
        ('otro', 'Otro'),
    ]

    # Información básica
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()

    # Relaciones
    marca = models.ForeignKey('Marca', on_delete=models.PROTECT, related_name='productos')
    categoria = models.ForeignKey('Categoria', on_delete=models.PROTECT, related_name='productos')

    # Precios
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    precio_oferta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Precio especial si el producto está en oferta'
    )

    # Características
    genero = models.CharField(max_length=10, choices=GENERO_CHOICES, default='ambos')
    color = models.CharField(max_length=50, blank=True)
    material = models.CharField(max_length=100, blank=True)

    # Inventario
    stock = models.PositiveIntegerField(default=0)
    esta_disponible = models.BooleanField(
        default=True,
        help_text='Indica si el producto está disponible para la venta'
    )

    # Destacado
    es_destacado = models.BooleanField(
        default=False,
        help_text='Productos que aparecerán en la página principal'
    )

    # Imagen (Solo 1 imagen por producto)
    imagen = models.ImageField(
        upload_to='productos/',
        blank=True,
        null=True,
        help_text='Imagen principal del producto (máximo 1)'
    )

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['marca']),
            models.Index(fields=['categoria']),
            models.Index(fields=['esta_disponible']),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.marca.nombre}"

    def precio_actual(self):
        """Devuelve el precio actual (oferta si existe, sino precio normal)"""
        if self.precio_oferta and self.precio_oferta < self.precio:
            return self.precio_oferta
        return self.precio

    def tiene_oferta(self):
        """Verifica si el producto tiene una oferta activa"""
        return self.precio_oferta is not None and self.precio_oferta < self.precio

    def descuento_porcentaje(self):
        """Calcula el porcentaje de descuento si hay oferta"""
        if self.tiene_oferta():
            descuento = ((self.precio - self.precio_oferta) / self.precio) * 100
            return round(descuento, 2)
        return 0

    def esta_agotado(self):
        """Verifica si el producto está agotado (Requisito 011)"""
        return self.stock == 0 or not self.esta_disponible