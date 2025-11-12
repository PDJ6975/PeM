"""
Servicio de lógica de negocio para el carrito de compras.

Este módulo centraliza toda la lógica relacionada con la gestión del carrito,
incluyendo agregar, modificar y eliminar productos.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from core.models import Carrito, ItemCarrito, Producto


class CarritoError(Exception):
    """Excepción base para errores relacionados con el carrito"""
    pass


class StockInsuficienteError(CarritoError):
    """Excepción cuando no hay stock suficiente"""
    pass


class ProductoNoDisponibleError(CarritoError):
    """Excepción cuando el producto no está disponible"""
    pass


def obtener_o_crear_carrito(cliente=None, carrito_id=None):
    """
    Obtiene un carrito existente o crea uno nuevo.

    Args:
        cliente: Instancia del modelo Cliente (opcional para carritos anónimos)
        carrito_id: ID del carrito existente (opcional)

    Returns:
        Carrito: Instancia del carrito

    Raises:
        Carrito.DoesNotExist: Si el carrito_id no existe
    """
    if carrito_id:
        return Carrito.objects.get(id=carrito_id)

    if cliente:
        # Buscar carrito activo del cliente
        carrito = Carrito.objects.filter(cliente=cliente).first()
        if carrito:
            return carrito

    # Crear nuevo carrito
    return Carrito.objects.create(cliente=cliente)


@transaction.atomic
def agregar_producto(carrito_id, producto_id, cantidad=1):
    """
    Agrega un producto al carrito o incrementa su cantidad si ya existe.

    Args:
        carrito_id: ID del carrito
        producto_id: ID del producto a agregar
        cantidad: Cantidad a agregar (default: 1)

    Returns:
        dict: Información del item agregado con estructura:
            {
                'item_id': int,
                'producto': {
                    'id': int,
                    'nombre': str,
                    'precio_unitario': Decimal
                },
                'cantidad': int,
                'subtotal': Decimal,
                'mensaje': str
            }

    Raises:
        ProductoNoDisponibleError: Si el producto no está disponible
        StockInsuficienteError: Si no hay stock suficiente
        ValidationError: Si la cantidad es inválida
    """
    # Validaciones de entrada
    if cantidad < 1:
        raise ValidationError("La cantidad debe ser al menos 1")

    # Obtener carrito y producto
    try:
        carrito = Carrito.objects.select_related('cliente').get(id=carrito_id)
        producto = Producto.objects.select_related('marca', 'categoria').get(id=producto_id)
    except Carrito.DoesNotExist:
        raise CarritoError(f"Carrito con ID {carrito_id} no encontrado")
    except Producto.DoesNotExist:
        raise CarritoError(f"Producto con ID {producto_id} no encontrado")

    # Validar disponibilidad del producto
    if not producto.esta_disponible or producto.esta_agotado():
        raise ProductoNoDisponibleError(
            f"El producto '{producto.nombre}' no está disponible"
        )

    # Buscar si el producto ya existe en el carrito
    item, created = ItemCarrito.objects.get_or_create(
        carrito=carrito,
        producto=producto,
        defaults={'cantidad': 0}
    )

    # Calcular nueva cantidad
    nueva_cantidad = item.cantidad + cantidad

    # Validar stock disponible
    if nueva_cantidad > producto.stock:
        raise StockInsuficienteError(
            f"Stock insuficiente para '{producto.nombre}'. "
            f"Disponible: {producto.stock}, Solicitado: {nueva_cantidad}"
        )

    # Actualizar cantidad
    item.cantidad = nueva_cantidad
    item.save()

    # Preparar respuesta
    return {
        'item_id': item.id,
        'producto': {
            'id': producto.id,
            'nombre': producto.nombre,
            'precio_unitario': producto.precio_actual(),
            'imagen': producto.imagen.url if producto.imagen else None,
        },
        'cantidad': item.cantidad,
        'subtotal': item.subtotal(),
        'mensaje': 'Producto agregado' if created else 'Cantidad actualizada'
    }


@transaction.atomic
def modificar_cantidad(carrito_id, producto_id, nueva_cantidad):
    """
    Modifica la cantidad de un producto en el carrito.

    Args:
        carrito_id: ID del carrito
        producto_id: ID del producto
        nueva_cantidad: Nueva cantidad deseada

    Returns:
        dict: Información actualizada del item

    Raises:
        ValidationError: Si la cantidad es inválida
        StockInsuficienteError: Si no hay stock suficiente
        ItemCarrito.DoesNotExist: Si el producto no está en el carrito
    """
    # Validaciones
    if nueva_cantidad < 1:
        raise ValidationError("La cantidad debe ser al menos 1")

    # Obtener item del carrito
    try:
        item = ItemCarrito.objects.select_related('producto', 'carrito').get(
            carrito_id=carrito_id,
            producto_id=producto_id
        )
    except ItemCarrito.DoesNotExist:
        raise CarritoError(
            f"El producto no se encuentra en el carrito"
        )

    # Validar stock
    if nueva_cantidad > item.producto.stock:
        raise StockInsuficienteError(
            f"Stock insuficiente. Disponible: {item.producto.stock}"
        )

    # Actualizar cantidad
    item.cantidad = nueva_cantidad
    item.save()

    return {
        'item_id': item.id,
        'producto': {
            'id': item.producto.id,
            'nombre': item.producto.nombre,
            'precio_unitario': item.producto.precio_actual(),
        },
        'cantidad': item.cantidad,
        'subtotal': item.subtotal(),
        'mensaje': 'Cantidad actualizada'
    }


@transaction.atomic
def eliminar_producto(carrito_id, producto_id):
    """
    Elimina un producto del carrito.

    Args:
        carrito_id: ID del carrito
        producto_id: ID del producto a eliminar

    Returns:
        dict: Confirmación de la eliminación

    Raises:
        ItemCarrito.DoesNotExist: Si el producto no está en el carrito
    """
    try:
        item = ItemCarrito.objects.get(
            carrito_id=carrito_id,
            producto_id=producto_id
        )
        producto_nombre = item.producto.nombre
        item.delete()

        return {
            'mensaje': f"'{producto_nombre}' eliminado del carrito",
            'producto_id': producto_id
        }
    except ItemCarrito.DoesNotExist:
        raise CarritoError(
            f"El producto no se encuentra en el carrito"
        )


def obtener_carrito_detallado(carrito_id):
    """
    Obtiene el carrito con todos sus items y cálculos.

    Args:
        carrito_id: ID del carrito

    Returns:
        dict: Información completa del carrito con estructura:
            {
                'carrito_id': int,
                'items': list,
                'total_items': int,
                'subtotal': Decimal,
                'esta_vacio': bool
            }

    Raises:
        Carrito.DoesNotExist: Si el carrito no existe
    """
    try:
        carrito = Carrito.objects.prefetch_related(
            'items__producto__marca',
            'items__producto__categoria'
        ).get(id=carrito_id)
    except Carrito.DoesNotExist:
        raise CarritoError(f"Carrito con ID {carrito_id} no encontrado")

    # Construir lista de items
    items = []
    for item in carrito.items.all():
        items.append({
            'item_id': item.id,
            'producto': {
                'id': item.producto.id,
                'nombre': item.producto.nombre,
                'marca': item.producto.marca.nombre,
                'precio_unitario': item.producto.precio_actual(),
                'tiene_oferta': item.producto.tiene_oferta(),
                'imagen': item.producto.imagen.url if item.producto.imagen else None,
            },
            'cantidad': item.cantidad,
            'subtotal': item.subtotal(),
        })

    return {
        'carrito_id': carrito.id,
        'items': items,
        'total_items': carrito.total_items(),
        'subtotal': carrito.subtotal(),
        'esta_vacio': carrito.esta_vacio()
    }


@transaction.atomic
def vaciar_carrito(carrito_id):
    """
    Elimina todos los productos del carrito.

    Args:
        carrito_id: ID del carrito

    Returns:
        dict: Confirmación de la operación
    """
    try:
        carrito = Carrito.objects.get(id=carrito_id)
        items_eliminados = carrito.items.count()
        carrito.items.all().delete()

        return {
            'mensaje': 'Carrito vaciado',
            'items_eliminados': items_eliminados
        }
    except Carrito.DoesNotExist:
        raise CarritoError(f"Carrito con ID {carrito_id} no encontrado")


@transaction.atomic
def migrar_carrito(carrito_anonimo_id, cliente):
    """
    Migra los productos de un carrito anónimo a un carrito de usuario registrado.
    Si el usuario ya tiene un carrito, combina ambos carritos.

    Args:
        carrito_anonimo_id: ID del carrito anónimo
        cliente: Instancia del modelo Cliente

    Returns:
        dict: Información de la migración con estructura:
            {
                'carrito_id': int,
                'items_migrados': int,
                'items_combinados': int,
                'mensaje': str
            }

    Raises:
        CarritoError: Si el carrito anónimo no existe o ya tiene cliente
    """
    try:
        # Obtener carrito anónimo
        carrito_anonimo = Carrito.objects.prefetch_related('items__producto').get(
            id=carrito_anonimo_id
        )
    except Carrito.DoesNotExist:
        raise CarritoError(f"Carrito con ID {carrito_anonimo_id} no encontrado")

    # Validar que sea carrito anónimo
    if carrito_anonimo.cliente is not None:
        raise CarritoError("El carrito ya tiene un cliente asociado")

    # Obtener o crear carrito del cliente
    carrito_cliente = obtener_o_crear_carrito(cliente=cliente)

    items_migrados = 0
    items_combinados = 0

    # Migrar cada item del carrito anónimo
    for item_anonimo in carrito_anonimo.items.all():
        # Verificar si el producto ya existe en el carrito del cliente
        item_cliente = ItemCarrito.objects.filter(
            carrito=carrito_cliente,
            producto=item_anonimo.producto
        ).first()

        if item_cliente:
            # Producto ya existe, combinar cantidades
            nueva_cantidad = item_cliente.cantidad + item_anonimo.cantidad

            # Validar stock disponible
            if nueva_cantidad > item_anonimo.producto.stock:
                # Ajustar a stock máximo disponible
                nueva_cantidad = item_anonimo.producto.stock

            item_cliente.cantidad = nueva_cantidad
            item_cliente.save()
            items_combinados += 1
        else:
            # Producto no existe, migrar el item
            item_anonimo.carrito = carrito_cliente
            item_anonimo.save()
            items_migrados += 1

    # Eliminar el carrito anónimo
    carrito_anonimo.delete()

    return {
        'carrito_id': carrito_cliente.id,
        'items_migrados': items_migrados,
        'items_combinados': items_combinados,
        'mensaje': 'Carrito migrado exitosamente'
    }
