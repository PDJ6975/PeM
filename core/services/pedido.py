from core.models.pedido import Pedido

def view_order(email, order_code):
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
