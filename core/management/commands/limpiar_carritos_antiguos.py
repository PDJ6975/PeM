"""
Management command para limpiar carritos anónimos antiguos/abandonados.

Uso:
    python manage.py limpiar_carritos_antiguos
    python manage.py limpiar_carritos_antiguos --dias 7
    python manage.py limpiar_carritos_antiguos --dry-run
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Carrito


class Command(BaseCommand):
    help = 'Elimina carritos anónimos antiguos que no han sido actualizados recientemente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=30,
            help='Número de días de inactividad antes de eliminar (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué carritos serían eliminados sin eliminarlos realmente'
        )

    def handle(self, *args, **options):
        dias = options['dias']
        dry_run = options['dry_run']

        # Calcular fecha límite
        fecha_limite = timezone.now() - timedelta(days=dias)

        # Buscar carritos anónimos antiguos
        carritos_antiguos = Carrito.objects.filter(
            cliente__isnull=True,
            fecha_actualizacion__lt=fecha_limite
        )

        total = carritos_antiguos.count()

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS(f'No hay carritos anónimos con más de {dias} días de inactividad.')
            )
            return

        # Mostrar información
        self.stdout.write(f'\nCarritos anónimos encontrados: {total}')
        self.stdout.write(f'Fecha límite: {fecha_limite.strftime("%Y-%m-%d %H:%M:%S")}')

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\n[DRY RUN] Se eliminarían {total} carritos anónimos.')
            )
            # Mostrar algunos ejemplos
            for carrito in carritos_antiguos[:5]:
                self.stdout.write(
                    f'  - Carrito #{carrito.id}: {carrito.total_items()} items, '
                    f'última actualización: {carrito.fecha_actualizacion.strftime("%Y-%m-%d")}'
                )
            if total > 5:
                self.stdout.write(f'  ... y {total - 5} más')
        else:
            # Confirmar eliminación
            self.stdout.write(
                self.style.WARNING(f'\n¿Eliminar {total} carritos anónimos? (y/N): '),
                ending=''
            )

            # En producción, usar confirmación automática con --no-input
            if options.get('verbosity', 1) > 0:
                confirmacion = input().lower()
                if confirmacion != 'y':
                    self.stdout.write(self.style.ERROR('Operación cancelada.'))
                    return

            # Eliminar carritos
            carritos_eliminados, detalles = carritos_antiguos.delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Eliminados {total} carritos anónimos antiguos correctamente.'
                )
            )

            # Mostrar detalles de eliminación
            if detalles:
                self.stdout.write('\nDetalles de la eliminación:')
                for modelo, cantidad in detalles.items():
                    self.stdout.write(f'  - {modelo}: {cantidad}')
