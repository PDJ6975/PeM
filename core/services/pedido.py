from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta
from core.models.pedido import Pedido
from core.models.item_pedido import ItemPedido
from core.models.producto import Producto

class PedidoService:
    
    @staticmethod
    def view_order(email, order_code):
        """
        Verifica si un pedido existe con el email y código de pedido
        """
        if not email or not order_code:
            raise ValueError("El email y código de pedido son obligatorios")
        try:
            pedido = Pedido.objects.select_related('cliente').get(
                cliente__email=email,
                codigo=order_code
            )
            return pedido
        except Pedido.DoesNotExist:
            return None
    
    @staticmethod
    def obtener_pedidos_admin(filtros=None):
        """
        Obtiene todos los pedidos con filtros opcionales para el admin
        """
        queryset = Pedido.objects.select_related('cliente').prefetch_related('items__producto')
        
        if filtros:
            if filtros.get('estado'):
                queryset = queryset.filter(estado=filtros['estado'])
            if filtros.get('fecha_desde'):
                queryset = queryset.filter(fecha_creacion__gte=filtros['fecha_desde'])
            if filtros.get('fecha_hasta'):
                queryset = queryset.filter(fecha_creacion__lte=filtros['fecha_hasta'])
            if filtros.get('cliente_email'):
                queryset = queryset.filter(cliente__email__icontains=filtros['cliente_email'])
        
        return queryset.order_by('-fecha_creacion')
    
    @staticmethod
    def obtener_detalle_pedido(pedido_id):
        """
        Obtiene el detalle completo de un pedido
        """
        try:
            pedido = Pedido.objects.select_related('cliente').prefetch_related(
                'items__producto__categoria',
                'items__producto__marca'
            ).get(id=pedido_id)
            return pedido
        except Pedido.DoesNotExist:
            return None
    
    @staticmethod
    def cambiar_estado_pedido(pedido_id, nuevo_estado):
        """
        Cambia el estado de un pedido
        """
        try:
            pedido = Pedido.objects.get(id=pedido_id)
            
            # Validar que el nuevo estado es válido
            estados_validos = ['pendiente', 'procesando', 'enviado', 'entregado', 'cancelado']
            if nuevo_estado not in estados_validos:
                return False, "Estado no válido"
            
            estado_anterior = pedido.estado
            pedido.estado = nuevo_estado
            pedido.save()
            
            return True, pedido
        except Pedido.DoesNotExist:
            return False, "Pedido no encontrado"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def cancelar_pedido(pedido_id, motivo=None):
        """
        Cancela un pedido y restaura el stock de productos
        """
        try:
            pedido = Pedido.objects.get(id=pedido_id)
            
            # Validar que el pedido se puede cancelar
            if pedido.estado in ['entregado', 'cancelado']:
                return False, "No se puede cancelar un pedido en este estado"
            
            # Restaurar stock de productos
            for item in pedido.items.all():
                producto = item.producto
                producto.stock += item.cantidad
                producto.save()
            
            # Cambiar estado a cancelado
            pedido.estado = 'cancelado'
            pedido.save()
            
            return True, pedido
        except Pedido.DoesNotExist:
            return False, "Pedido no encontrado"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def obtener_estadisticas_pedidos():
        """
        Obtiene estadísticas generales de pedidos para el dashboard admin
        """
        hoy = timezone.now().date()
        hace_30_dias = hoy - timedelta(days=30)
        
        stats = {
            'total_pedidos': Pedido.objects.count(),
            'pedidos_pendientes': Pedido.objects.filter(estado='pendiente').count(),
            'pedidos_procesando': Pedido.objects.filter(estado='procesando').count(),
            'pedidos_enviados': Pedido.objects.filter(estado='enviado').count(),
            'pedidos_mes': Pedido.objects.filter(fecha_creacion__gte=hace_30_dias).count(),
            'ingresos_mes': Pedido.objects.filter(
                fecha_creacion__gte=hace_30_dias,
                estado__in=['procesando', 'enviado', 'entregado']
            ).aggregate(total=Sum('total'))['total'] or 0,
        }
        
        return stats