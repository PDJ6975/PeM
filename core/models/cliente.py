from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

from core.managers import ClienteManager

class Cliente(AbstractUser):
    
    username = None
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=10)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellidos']

    objects = ClienteManager()

    def __str__(self):
        tipo = "Administrador" if self.is_staff else "Cliente"
        return f"{self.email} ({tipo})"
