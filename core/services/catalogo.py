# core/services/catalogo.py
from django.db.models import Q
from core.models import Producto, ItemPedido
from django.db.models import F, Sum
from django.db.models import Sum, F, Q, IntegerField, Value
from django.db.models.functions import Coalesce
from django.db.models import Case, When
from core.models import Producto
def buscar_productos(q=None, marca_id=None, categoria_id=None, genero=None):
    qs = (Producto.objects
          .select_related("marca", "categoria")
          .filter(esta_disponible=True))

    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) |
            Q(descripcion__icontains=q) |
            Q(marca__nombre__icontains=q)
        )
    if marca_id:
        qs = qs.filter(marca_id=marca_id)
    if categoria_id:
        qs = qs.filter(categoria_id=categoria_id)
    if genero:
        qs = qs.filter(genero=genero)

    return qs.order_by("nombre")



def obtener_productos_destacados(limit=4):
    """
    Destacados automáticos:
    - En oferta (precio_oferta < precio)
    - O bien con ventas (> 0 unidades en ItemPedido)
    Orden: primero ofertas, luego más vendidos y más recientes.
    """
    qs = (
        Producto.objects.select_related("marca", "categoria")
        .filter(esta_disponible=True, stock__gt=0)
        .annotate(
            # ¡OJO! nombre correcto de la relación inversa: items_pedido
            total_vendidos=Coalesce(Sum("items_pedido__cantidad"), 0),
            es_oferta=Case(
                When(precio_oferta__isnull=False, precio_oferta__lt=F("precio"), then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        .filter(Q(es_oferta=1) | Q(total_vendidos__gt=0))
        .order_by("-es_oferta", "-total_vendidos", "-fecha_actualizacion", "-fecha_creacion")[:limit]
    )
    return qs
