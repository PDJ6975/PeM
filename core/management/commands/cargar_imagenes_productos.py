import csv
import requests
from io import StringIO
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Producto


class Command(BaseCommand):
    help = "Asigna imágenes a productos desde un CSV local o remoto (GitHub)."

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, help='Ruta local o URL del archivo CSV con columnas: nombre,archivo')
        parser.add_argument('--replace', action='store_true', help='Reemplazar imagen si ya existe.')
        parser.add_argument('--dry-run', action='store_true', help='Solo mostrar sin aplicar cambios.')

    def handle(self, *args, **options):
        csv_path = options['csv']
        replace = options['replace']
        dry_run = options['dry_run']

        base_url = getattr(settings, 'MEDIA_EXTERNAL_URL', '').rstrip('/')
        if not base_url:
            self.stderr.write(self.style.ERROR("❌ MEDIA_EXTERNAL_URL no está definido en settings.py"))
            return

        if not csv_path:
            self.stderr.write(self.style.ERROR("❌ No se ha proporcionado --csv"))
            return

        if csv_path.startswith("http"):
            self.stdout.write(f"🌐 Descargando CSV remoto desde {csv_path}...")
            resp = requests.get(csv_path)
            resp.raise_for_status()
            csvfile = StringIO(resp.text)
        else:
            csvfile = open(csv_path, newline='', encoding='utf-8')

        reader = csv.DictReader(csvfile)
        for row in reader:
            nombre = row['nombre'].strip()
            archivo = row['archivo'].strip()

            try:
                producto = Producto.objects.get(nombre=nombre)
            except Producto.DoesNotExist:
                self.stderr.write(self.style.WARNING(f"⚠️ Producto no encontrado: {nombre}"))
                continue

            if producto.imagen and not replace:
                self.stdout.write(f"⏭️ {nombre} ya tiene imagen, omitido.")
                continue

            image_url = f"{base_url}/{archivo}"
            if not dry_run:
                producto.imagen.name = image_url
                producto.save()

            self.stdout.write(self.style.SUCCESS(f"✅ {nombre} → {image_url}"))

        csvfile.close()
        self.stdout.write(self.style.SUCCESS("✨ Asignación de imágenes completada."))
