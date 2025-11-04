from django.contrib.auth import authenticate
from core.models.cliente import Cliente
from django.contrib.auth.hashers import make_password

def register(email, password, nombre, apellidos, **extra_fields):
    if not email:
        raise ValueError("El email es obligatorio")
    if not password:
        raise ValueError("La contraseña es obligatoria")
    if Cliente.objects.filter(email=email).exists():
        raise ValueError("Ya existe un cliente con este email")
    
    cliente = Cliente(
        email=email,
        nombre=nombre,
        apellidos=apellidos,
        password=make_password(password),
        **extra_fields
    )
    cliente.save()
    return cliente

def login(email, password):
    if not email or not password:
        return None
    return authenticate(email=email, password=password)