import csv
import os
from django.core.management.base import BaseCommand
from core.models import Producto

class Command(BaseCommand):
    help = "Asigna imágenes a productos desde una carpeta y un CSV de mapeo."

    def add_arguments(self, parser):
        parser.add_argument('--folder', type=str, required=True, help='Ruta a la carpeta de imágenes.')
        parser.add_argument('--csv', type=str, required=True, help='Archivo CSV con columnas: nombre,archivo')
        parser.add_argument('--replace', action='store_true', help='Reemplazar imagen si ya existe.')
        parser.add_argument('--dry-run', action='store_true', help='Solo mostrar sin aplicar cambios.')

    def handle(self, *args, **options):
        folder = options['folder']
        csv_path = options['csv']
        replace = options['replace']
        dry_run = options['dry_run']

        if not os.path.exists(folder):
            self.stderr.write(self.style.ERROR(f"Carpeta no encontrada: {folder}"))
            return

        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                nombre = row['nombre'].strip()
                archivo = row['archivo'].strip()
                ruta = os.path.join(folder, archivo)

                try:
                    producto = Producto.objects.get(nombre=nombre)
                except Producto.DoesNotExist:
                    self.stderr.write(self.style.WARNING(f"⚠️ Producto no encontrado: {nombre}"))
                    continue

                if not os.path.exists(ruta):
                    self.stderr.write(self.style.WARNING(f"⚠️ Imagen no encontrada: {ruta}"))
                    continue

                if producto.imagen and not replace:
                    self.stdout.write(f"⏭️ {nombre} ya tiene imagen, omitido.")
                    continue

                rel_path = os.path.relpath(ruta, start=os.getcwd()).replace("\\", "/")
                if not dry_run:
                    producto.imagen.name = rel_path.replace('media/', '')
                    producto.save()

                self.stdout.write(self.style.SUCCESS(f"✅ {nombre} → {rel_path}"))

        self.stdout.write(self.style.SUCCESS("✨ Asignación de imágenes completada."))
