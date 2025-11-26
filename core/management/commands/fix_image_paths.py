from django.core.management.base import BaseCommand
from core.models import Producto


class Command(BaseCommand):
    help = "Corrige las rutas de imágenes de productos eliminando '../media/' de las rutas"

    def handle(self, *args, **options):
        productos = Producto.objects.all()
        actualizados = 0

        for producto in productos:
            if producto.imagen and producto.imagen.name:
                ruta_original = producto.imagen.name
                
                if '../media/productos/' in ruta_original:
                    nueva_ruta = ruta_original.replace('../media/productos/', 'productos/')
                    producto.imagen.name = nueva_ruta
                    producto.save()
                    self.stdout.write(self.style.SUCCESS(f" {producto.nombre}: {ruta_original} -> {nueva_ruta}"))
                    actualizados += 1
                
                elif '../media/' in ruta_original:
                    nueva_ruta = ruta_original.replace('../media/', '')
                    producto.imagen.name = nueva_ruta
                    producto.save()
                    self.stdout.write(self.style.SUCCESS(f" {producto.nombre}: {ruta_original} -> {nueva_ruta}"))
                    actualizados += 1
                
                else:
                    self.stdout.write(f"⏭  {producto.nombre}: {ruta_original} (ya correcto)")

        self.stdout.write(self.style.SUCCESS(f"\n Actualizados: {actualizados} productos"))
