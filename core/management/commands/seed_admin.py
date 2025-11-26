import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Crea un superusuario por defecto si no existe (usando variables de entorno)"

    def handle(self, *args, **options):
        User = get_user_model()

        email = os.getenv("ADMIN_EMAIL", "admin@pem.com")
        password = os.getenv("ADMIN_PASSWORD", "admin123")
        nombre = os.getenv("ADMIN_NAME", "Administrador")

        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password=password,
                nombre=nombre
            )
            self.stdout.write(self.style.SUCCESS(f"Superusuario creado: {email}"))
        else:
            self.stdout.write(self.style.WARNING(f"El superusuario {email} ya existe"))
