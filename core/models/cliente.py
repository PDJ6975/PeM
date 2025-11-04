from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class Cliente(AbstractUser):
    
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=10)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'nombre', 'apellidos']


    def __str__(self):
        tipo = "Administrador" if self.is_staff else "Cliente"
        return f"{self.email} ({tipo})"
