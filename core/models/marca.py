from django.db import models
from django.utils import timezone

class Marca(models.Model):
    """
    Modelo para representar las marcas/fabricantes de productos.
    """
    nombre = models.CharField(max_length=100, unique=True)
    imagen = models.ImageField(upload_to='marcas/', blank=True, null=True)

    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
