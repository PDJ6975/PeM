from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import login as django_login

from core.services.catalogo import buscar_productos, obtener_productos_destacados
from core.models import Producto
from .models import Categoria, Marca
import json

from core.models.carrito import Carrito
from core.models.item_carrito import ItemCarrito
from core.models.pedido import Pedido
from core.models.item_pedido import ItemPedido
from core.models.cliente import Cliente
from core.models.producto import Producto

from core.services import carrito as carrito_service
from core.services.pedido import PedidoService
from django.conf import settings
from django.utils import timezone
from core.services.carrito import vaciar_carrito
from django.utils.crypto import get_random_string
from django.db import IntegrityError, transaction




def home(request):
    """Vista de la página de inicio"""
    return render(request, 'core/index.html')

def login_page(request):
    return render(request, 'core/login.html')

def register_page(request):
    return render(request, 'core/register.html')

def logout_view(request):
    logout(request)
    return redirect('home')

# ============================================
# API REST para el Carrito
# ============================================

class CarritoBaseView(View):
    """
    Vista base para endpoints del carrito.
    Proporciona utilidades comunes y manejo de errores.
    """

    def get_carrito_id(self, request):
        """
        Obtiene o crea el ID del carrito desde la sesión.

        Para carritos anónimos (sin registro), almacenamos el carrito_id
        en la sesión. Para usuarios autenticados, podemos usar su cliente.
        """
        if not request.session.session_key:
            request.session.create()

        carrito_id = request.session.get('carrito_id')

        if not carrito_id:
            # Crear nuevo carrito
            cliente = request.user if request.user.is_authenticated else None
            carrito = carrito_service.obtener_o_crear_carrito(cliente=cliente)
            carrito_id = carrito.id
            request.session['carrito_id'] = carrito_id

        return carrito_id

    def json_response(self, data, status=200):
        """Respuesta JSON estandarizada"""
        return JsonResponse(data, status=status, safe=False)

    def error_response(self, mensaje, status=400, **extra):
        """Respuesta de error estandarizada"""
        error_data = {
            'error': True,
            'mensaje': mensaje,
            **extra
        }
        return JsonResponse(error_data, status=status)


@method_decorator(csrf_exempt, name='dispatch')
class AgregarProductoView(CarritoBaseView):
    """
    POST /api/carrito/agregar/
    Agrega un producto al carrito o incrementa su cantidad.

    Body (JSON):
        {
            "producto_id": int,
            "cantidad": int (opcional, default: 1)
        }

    Respuesta exitosa (200):
        {
            "success": true,
            "mensaje": str,
            "item": {...},
            "carrito": {...}
        }

    Respuesta de error (400/404):
        {
            "error": true,
            "mensaje": str
        }
    """

    def post(self, request):
        try:
            # Parsear body JSON
            data = json.loads(request.body)
            producto_id = data.get('producto_id')
            cantidad = data.get('cantidad', 1)

            # Validaciones básicas
            if not producto_id:
                return self.error_response("producto_id es requerido")

            try:
                cantidad = int(cantidad)
            except (TypeError, ValueError):
                return self.error_response("cantidad debe ser un número entero")

            # Obtener carrito
            carrito_id = self.get_carrito_id(request)

            # Agregar producto usando el servicio
            resultado = carrito_service.agregar_producto(
                carrito_id=carrito_id,
                producto_id=producto_id,
                cantidad=cantidad
            )

            # Obtener estado actualizado del carrito
            carrito_detalle = carrito_service.obtener_carrito_detallado(carrito_id)

            return self.json_response({
                'success': True,
                'mensaje': resultado['mensaje'],
                'item': resultado,
                'carrito': carrito_detalle
            })

        except carrito_service.ProductoNoDisponibleError as e:
            return self.error_response(str(e), status=400)

        except carrito_service.StockInsuficienteError as e:
            return self.error_response(str(e), status=400)

        except ValidationError as e:
            return self.error_response(str(e), status=400)

        except carrito_service.CarritoError as e:
            return self.error_response(str(e), status=404)

        except json.JSONDecodeError:
            return self.error_response("JSON inválido", status=400)

        except Exception as e:
            # Log del error en producción
            return self.error_response(
                "Error interno del servidor",
                status=500,
                detalle=str(e) if request.user.is_staff else None
            )


@method_decorator(csrf_exempt, name='dispatch')
class ModificarCantidadView(CarritoBaseView):
    """
    PUT /api/carrito/modificar/
    Modifica la cantidad de un producto en el carrito.

    Body (JSON):
        {
            "producto_id": int,
            "cantidad": int
        }
    """

    def put(self, request):
        try:
            data = json.loads(request.body)
            producto_id = data.get('producto_id')
            cantidad = data.get('cantidad')

            if not producto_id or cantidad is None:
                return self.error_response("producto_id y cantidad son requeridos")

            try:
                cantidad = int(cantidad)
            except (TypeError, ValueError):
                return self.error_response("cantidad debe ser un número entero")

            carrito_id = self.get_carrito_id(request)

            resultado = carrito_service.modificar_cantidad(
                carrito_id=carrito_id,
                producto_id=producto_id,
                nueva_cantidad=cantidad
            )

            carrito_detalle = carrito_service.obtener_carrito_detallado(carrito_id)

            return self.json_response({
                'success': True,
                'mensaje': resultado['mensaje'],
                'item': resultado,
                'carrito': carrito_detalle
            })

        except carrito_service.StockInsuficienteError as e:
            return self.error_response(str(e), status=400)

        except ValidationError as e:
            return self.error_response(str(e), status=400)

        except carrito_service.CarritoError as e:
            return self.error_response(str(e), status=404)

        except json.JSONDecodeError:
            return self.error_response("JSON inválido", status=400)

        except Exception as e:
            return self.error_response(
                "Error interno del servidor",
                status=500,
                detalle=str(e) if request.user.is_staff else None
            )


@method_decorator(csrf_exempt, name='dispatch')
class EliminarProductoView(CarritoBaseView):
    """
    DELETE /api/carrito/eliminar/<producto_id>/
    Elimina un producto del carrito.
    """

    def delete(self, request, producto_id):
        try:
            carrito_id = self.get_carrito_id(request)

            resultado = carrito_service.eliminar_producto(
                carrito_id=carrito_id,
                producto_id=producto_id
            )

            carrito_detalle = carrito_service.obtener_carrito_detallado(carrito_id)

            return self.json_response({
                'success': True,
                'mensaje': resultado['mensaje'],
                'carrito': carrito_detalle
            })

        except carrito_service.CarritoError as e:
            return self.error_response(str(e), status=404)

        except Exception as e:
            return self.error_response(
                "Error interno del servidor",
                status=500,
                detalle=str(e) if request.user.is_staff else None
            )


class ObtenerCarritoView(CarritoBaseView):
    """
    GET /api/carrito/
    Obtiene el contenido completo del carrito.
    """

    def get(self, request):
        try:
            carrito_id = self.get_carrito_id(request)
            carrito_detalle = carrito_service.obtener_carrito_detallado(carrito_id)

            return self.json_response({
                'success': True,
                'carrito': carrito_detalle
            })

        except carrito_service.CarritoError as e:
            return self.error_response(str(e), status=404)

        except Exception as e:
            return self.error_response(
                "Error interno del servidor",
                status=500,
                detalle=str(e) if request.user.is_staff else None
            )


@method_decorator(csrf_exempt, name='dispatch')
class VaciarCarritoView(CarritoBaseView):
    """
    DELETE /api/carrito/vaciar/
    Elimina todos los productos del carrito.
    """

    def delete(self, request):
        try:
            carrito_id = self.get_carrito_id(request)
            resultado = carrito_service.vaciar_carrito(carrito_id)

            return self.json_response({
                'success': True,
                'mensaje': resultado['mensaje'],
                'items_eliminados': resultado['items_eliminados']
            })

        except carrito_service.CarritoError as e:
            return self.error_response(str(e), status=404)

        except Exception as e:
            return self.error_response(
                "Error interno del servidor",
                status=500,
                detalle=str(e) if request.user.is_staff else None
            )


# ============================================
# API REST para Gestión de Pedidos (Admin)
#
# COMENTADO POR AHORA HASTA QUE SEPAMOS QUE PANEL DE 
# ADMINISTRACIÓN QUIERE EL CLIENTE
# ============================================

'''
@staff_member_required
def admin_pedidos_lista(request):
    """
    GET /api/admin/pedidos/
    Lista todos los pedidos con filtros opcionales.
    
    Query params opcionales:
        - estado: filtrar por estado del pedido
        - fecha_desde: filtrar desde fecha
        - fecha_hasta: filtrar hasta fecha
        - cliente_email: filtrar por email del cliente
    """
    filtros = {
        'estado': request.GET.get('estado'),
        'fecha_desde': request.GET.get('fecha_desde'),
        'fecha_hasta': request.GET.get('fecha_hasta'),
        'cliente_email': request.GET.get('cliente_email'),
    }
    
    # Eliminar filtros vacíos
    filtros = {k: v for k, v in filtros.items() if v}
    
    pedidos = PedidoService.obtener_pedidos_admin(filtros)
    estadisticas = PedidoService.obtener_estadisticas_pedidos()
    
    context = {
        'pedidos': pedidos,
        'estadisticas': estadisticas,
        'filtros': filtros,
    }
    
    return render(request, 'core/admin/pedidos_lista.html', context)


@staff_member_required
def admin_pedido_detalle(request, pedido_id):
    """
    GET /api/admin/pedidos/<pedido_id>/
    Obtiene el detalle completo de un pedido específico.
    """
    pedido = PedidoService.obtener_detalle_pedido(pedido_id)
    
    if not pedido:
        messages.error(request, 'Pedido no encontrado')
        return redirect('admin_pedidos_lista')
    
    context = {
        'pedido': pedido,
    }
    
    return render(request, 'core/admin/pedido_detalle.html', context)


@staff_member_required
def admin_pedido_cambiar_estado(request, pedido_id):
    """
    POST /api/admin/pedidos/<pedido_id>/cambiar-estado/
    Cambia el estado de un pedido.
    
    POST params:
        - estado: nuevo estado del pedido (pendiente|procesando|enviado|entregado|cancelado)
    """
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        
        if not nuevo_estado:
            messages.error(request, 'Debe seleccionar un estado')
            return redirect('admin_pedido_detalle', pedido_id=pedido_id)
        
        exito, resultado = PedidoService.cambiar_estado_pedido(pedido_id, nuevo_estado)
        
        if exito:
            messages.success(request, f'Estado del pedido actualizado a {nuevo_estado}')
        else:
            messages.error(request, f'Error al cambiar estado: {resultado}')
        
        return redirect('admin_pedido_detalle', pedido_id=pedido_id)
    
    return redirect('admin_pedidos_lista')


@staff_member_required
def admin_pedido_cancelar(request, pedido_id):
    """
    POST /api/admin/pedidos/<pedido_id>/cancelar/
    Cancela un pedido y restaura el stock de los productos.
    
    POST params:
        - motivo: motivo de la cancelación (opcional)
    """
    if request.method == 'POST':
        motivo = request.POST.get('motivo', 'Cancelado por el administrador')
        exito, resultado = PedidoService.cancelar_pedido(pedido_id, motivo)
        
        if exito:
            messages.success(request, 'Pedido cancelado correctamente. Stock restaurado.')
        else:
            messages.error(request, f'Error al cancelar: {resultado}')
        
        return redirect('admin_pedidos_lista')
    
    return redirect('admin_pedido_detalle', pedido_id=pedido_id)


@staff_member_required
def admin_pedidos_estadisticas(request):
    """
    GET /api/admin/pedidos/estadisticas/
    Muestra las estadísticas de pedidos en formato HTML.
    """
    estadisticas = PedidoService.obtener_estadisticas_pedidos()
    
    # Si se solicita JSON (para APIs), devolver JSON
    if request.GET.get('format') == 'json':
        return JsonResponse(estadisticas)
    
    # Por defecto, mostrar HTML
    context = {
        'estadisticas': estadisticas,
    }
    
    return render(request, 'core/admin/pedidos_estadisticas.html', context)
'''

# ============================================
# API REST para Usuarios y Autenticación
# ============================================

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(View):
    """
    POST /api/auth/register/
    Registra un nuevo cliente.

    Body (JSON):
        {
            "email": "test@example.com",
            "password": "securepassword",
            "nombre": "Pablo",
            "apellidos": "Olivencia Moreno"
        }

    Respuesta (201):
        {
            "success": true,
            "mensaje": "Usuario registrado correctamente"
        }
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            email = data.get("email")
            password = data.get("password")
            nombre = data.get("nombre")
            apellidos = data.get("apellidos")

            if not email or not password:
                return JsonResponse({"error": "Email y contraseña son obligatorios"}, status=400)

            from core.services.cliente import register
            cliente = register(email=email, password=password, nombre=nombre, apellidos=apellidos)
            return JsonResponse({
                "success": True,
                "mensaje": "Usuario registrado correctamente",
                "cliente": {
                    "email": cliente.email,
                    "nombre": cliente.nombre,
                    "apellidos": cliente.apellidos
                }
            }, status=201)

        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"error": "Error interno del servidor", "detalle": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):
    """
    POST /api/auth/login/
    Inicia sesión con email y contraseña.

    Body (JSON):
        {
            "email": "test@example.com",
            "password": "securepassword"
        }

    Respuesta (200):
        {
            "success": true,
            "mensaje": "Inicio de sesión exitoso",
            "usuario": {...}
        }
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            email = data.get("email")
            password = data.get("password")

            if not email or not password:
                return JsonResponse({"error": "Email y contraseña son obligatorios"}, status=400)

            from core.services.cliente import login
            cliente = login(email=email, password=password)

            if not cliente:
                return JsonResponse({"error": "Credenciales inválidas"}, status=401)
            

            django_login(request, cliente)


            return JsonResponse({
                "success": True,
                "mensaje": "Inicio de sesión exitoso",
                "usuario": {
                    "email": cliente.email,
                    "nombre": cliente.nombre,
                    "apellidos": cliente.apellidos
                }
            })

        except Exception as e:
            return JsonResponse({"error": "Error interno del servidor", "detalle": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SeguimientoPedidoView(View):
    """
    Vista temporal para seguimiento de pedidos.
    Se reemplazará por una versión completa en una futura rama.
    """
    def get(self, request, tracking_token):
        return HttpResponse(f"Seguimiento temporal del pedido: {tracking_token}")

class CategoriasView(TemplateView):
    template_name = "core/categorias.html"

    def get(self, request, *args, **kwargs):
        categorias = Categoria.objects.order_by("nombre")
        destacados = {c.id: c.productos.filter(esta_disponible=True)[:8] for c in categorias}
        destacados_list = [(c, destacados[c.id]) for c in categorias]
        return render(request, self.template_name, {"categorias": categorias, "destacados_list": destacados_list})



class ProductosListView(TemplateView):
    template_name = "core/catalogo.html"

    def get(self, request, *args, **kwargs):
        q = request.GET.get("q") or ""
        marca_id = request.GET.get("marca") or None
        categoria_id = request.GET.get("categoria") or None
        genero = request.GET.get("genero") or None
        ordenar = request.GET.get("ordenar") or "nombre"  # nombre | precio | -precio

        qs = buscar_productos(q, marca_id, categoria_id, genero).order_by(ordenar)
        paginator = Paginator(qs, 12)  # 12 por página
        page_obj = paginator.get_page(request.GET.get("page"))

        destacados = obtener_productos_destacados(limit=4)
        contexto = {
            "page_obj": page_obj,
            "total": paginator.count,
            "marcas": Marca.objects.order_by("nombre"),
            "categorias": Categoria.objects.order_by("nombre"),
            "filtros": {"q": q, "marca": marca_id, "categoria": categoria_id, "genero": genero, "ordenar": ordenar},
            "destacados": destacados,
        }
        return render(request, self.template_name, contexto)



def api_categorias(request):
    data = list(Categoria.objects.order_by("nombre").values("id", "nombre"))
    return JsonResponse({"categorias": data}, status=200)


def api_productos(request):
    q = request.GET.get("q") or ""
    marca_id = request.GET.get("marca") or None
    categoria_id = request.GET.get("categoria") or None
    genero = request.GET.get("genero") or None
    ordenar = request.GET.get("ordenar") or "nombre"

    qs = buscar_productos(q, marca_id, categoria_id, genero).order_by(ordenar)
    paginator = Paginator(qs, int(request.GET.get("page_size") or 12))
    page_obj = paginator.get_page(request.GET.get("page"))

    items = [{
        "id": p.id,
        "nombre": p.nombre,
        "precio": str(p.precio_actual()),  # respeta lógica del modelo
        "tiene_oferta": p.tiene_oferta(),
        "marca": p.marca.nombre,
        "categoria": p.categoria.nombre,
        "genero": p.genero,
        "imagen": p.imagen.url if p.imagen else None,
        "stock": p.stock,
    } for p in page_obj.object_list]

    return JsonResponse({
        "count": paginator.count,
        "num_pages": paginator.num_pages,
        "page": page_obj.number,
        "results": items
    }, status=200)

import stripe
from core.models import Pedido

stripe.api_key = settings.STRIPE_SECRET_KEY
        
import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect
stripe.api_key = settings.STRIPE_SECRET_KEY

# views.py
import os
import stripe
from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch

from .models import Carrito, ItemCarrito  # ajusta import según tu estructura

stripe.api_key = settings.STRIPE_SECRET_KEY

def _build_line_items(carrito_id):
    """
    Convierte los ItemCarrito a line_items de Stripe.
    Usa Producto.precio_actual() para reflejar oferta si aplica.
    Acepta un ID de carrito (int) o instancia; aquí usamos ID.
    """
    items = (
        ItemCarrito.objects
        .select_related("producto")
        .filter(carrito=carrito_id)
    )
    line_items = []
    for it in items:
        producto = it.producto
        unit_amount = int(Decimal(producto.precio_actual()) * 100)  # céntimos
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": producto.nombre,
                },
                "unit_amount": unit_amount,
            },
            "quantity": it.cantidad,
        })
    return line_items

@csrf_exempt
def create_checkout_session(request):
    print("DEBUG [/api/carrito/procesar-pago/] method:", request.method)
    print("DEBUG user:", request.user, "is_auth:", request.user.is_authenticated)
    print("DEBUG cookies present?:", bool(request.COOKIES))
    print("DEBUG session_key BEFORE create():", request.session.session_key)

    if request.method != "POST":
        print("DEBUG método no permitido:", request.method)
        return HttpResponseBadRequest("Método no permitido")

    # --- Recuperar carrito de la sesión ---
    carrito_id = request.session.get("carrito_id")
    print(f"DEBUG carrito_id en sesión: {carrito_id} (tipo: {type(carrito_id)})")
    if not carrito_id:
        return HttpResponseBadRequest("No hay carrito en la sesión")

    # --- Verificar que hay items en el carrito ---
    items_qs = ItemCarrito.objects.filter(carrito=carrito_id)
    print("DEBUG num items en carrito:", items_qs.count())
    if not items_qs.exists():
        return HttpResponseBadRequest("El carrito está vacío")

    # --- Construir line_items para Stripe ---
    line_items = _build_line_items(carrito_id)
    print("DEBUG line_items construidos:", line_items)

    success_url = settings.STRIPE_SUCCESS_URL  # p.ej: ".../checkout/success?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = settings.STRIPE_CANCEL_URL

    # --- Metadata mínima para el webhook ---
    metadata = {
        "cart_id": str(carrito_id),  # OJO: usamos el entero directamente, no .id
    }
    if request.user.is_authenticated:
        metadata["user_id"] = str(request.user.id)

    session_kwargs = {
        "mode": "payment",
        "line_items": line_items,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(carrito_id),   # idem: ID directo
        "metadata": metadata,
        "allow_promotion_codes": True,
        "phone_number_collection": {"enabled": True},
        "billing_address_collection": "required",
        "shipping_address_collection": {
            "allowed_countries": ["ES"]
        },
    }

    if request.user.is_authenticated and getattr(request.user, "email", None):
        session_kwargs["customer_email"] = request.user.email

    try:
        session = stripe.checkout.Session.create(**session_kwargs)
    except stripe.error.StripeError as e:
        # Puedes loggear e.user_message / e.code para más detalle
        print("ERROR Stripe:", repr(e))
        return HttpResponseBadRequest(getattr(e, "user_message", "Error con Stripe"))

    request.session["stripe_session_id"] = session.id
    print("DEBUG stripe_session_id:", session.id)

    return JsonResponse({"id": session.id, "url": session.url})

def _split_nombre_apellidos(nombre_completo: str):
    """‘John A. Doe’ -> ('John A.', 'Doe') aprox."""
    if not nombre_completo:
        return ("Invitado", "SinDatos")
    partes = nombre_completo.strip().split()
    if len(partes) == 1:
        return (partes[0], "SinDatos")
    return (" ".join(partes[:-1]), partes[-1])


def _fmt_direccion(customer_details):
    """Devuelve una cadena con la dirección postal recibida desde Stripe."""
    if not customer_details or not customer_details.get("address"):
        return "Dirección no facilitada"
    a = customer_details["address"]
    lineas = [
        a.get("line1"),
        a.get("line2"),
        f'{a.get("postal_code","")} {a.get("city","")}'.strip(),
        a.get("state"),
        a.get("country"),
    ]
    return ", ".join([x for x in lineas if x])


def _precio_actual(producto: Producto) -> Decimal:
    """Refleja oferta si aplica (según tu modelo Producto)."""
    return producto.precio_actual()  # tu método del modelo


def _buscar_o_crear_cliente_desde_stripe(request, customer_details):
    if not customer_details:
        return request.user if request.user.is_authenticated else None

    raw_email = (customer_details.email or "").strip()
    if not raw_email:
        return request.user if request.user.is_authenticated else None

    # 1) Normaliza y baja a minúsculas (dominio y local-part)
    email = raw_email.lower()

    # Nombre y teléfonos desde Stripe
    nombre_completo = (customer_details.name or "").strip()
    partes = nombre_completo.split()
    nombre = partes[0] if partes else ""
    apellidos = " ".join(partes[1:]) if len(partes) > 1 else ""
    telefono = (customer_details.phone or "").strip()

    address = getattr(customer_details, "address", None) or {}
    direccion = (address.get("line1") or "").strip()
    ciudad = (address.get("city") or "").strip()
    cp = (address.get("postal_code") or "").strip()

    # 2) Si el user ya está logueado, úsalo y actualiza lo que falte
    if request.user.is_authenticated:
        cli = request.user
        cambios = False
        for campo, valor in [
            ("email", email),
            ("nombre", nombre),
            ("apellidos", apellidos),
            ("telefono", telefono),
            ("direccion", direccion),
            ("ciudad", ciudad),
            ("codigo_postal", cp),
        ]:
            if valor and getattr(cli, campo) != valor:
                setattr(cli, campo, valor); cambios = True
        if cambios:
            cli.save()
        return cli

    # 3) Intenta encontrar por email (case-insensitive)
    cli = Cliente.objects.filter(email__iexact=email).first()
    if cli:
        cambios = False
        for campo, valor in [
            ("nombre", nombre),
            ("apellidos", apellidos),
            ("telefono", telefono),
            ("direccion", direccion),
            ("ciudad", ciudad),
            ("codigo_postal", cp),
        ]:
            if valor and not getattr(cli, campo):
                setattr(cli, campo, valor); cambios = True
        if cambios:
            cli.save()
        return cli

    # 4) Crear invitado si no existe
    random_password = get_random_string(12)
    try:
        with transaction.atomic():
            cli = Cliente.objects.create_user(
                email=email,
                password=random_password,
                nombre=nombre,
                apellidos=apellidos,
            )
            # guarda extras opcionales
            cli.telefono = telefono or ""
            cli.direccion = direccion or ""
            cli.ciudad = ciudad or ""
            cli.codigo_postal = cp or ""
            cli.save(update_fields=["telefono", "direccion", "ciudad", "codigo_postal"])
            return cli
    except IntegrityError:
        # carrera o email ya creado en otra ruta: recupera y devuelve
        return Cliente.objects.get(email__iexact=email)


def _crear_pedido_desde_carrito(*, cliente: Cliente, carrito: Carrito, stripe_session, payment_intent):
    """Crea Pedido + sus líneas a partir del carrito."""
    # Totales básicos: de momento sin impuestos/envío/desc.
    subtotal = Decimal(0)
    items = ItemCarrito.objects.select_related("producto").filter(carrito=carrito)

    pedido = Pedido.objects.create(
        cliente=cliente,
        estado="confirmado",  # ya está pagado
        subtotal=Decimal("0.00"),  # provisional; se recalcula en save()
        impuestos=Decimal("0.00"),
        coste_entrega=Decimal("0.00"),
        descuento=Decimal("0.00"),
        total=Decimal("0.00"),     # el save() recalculará con calcular_total()
        direccion_envio=_fmt_direccion(getattr(stripe_session, "customer_details", None)),
        telefono=(getattr(stripe_session, "customer_details", {}) or {}).get("phone") or "600000000",
        stripe_session_id=stripe_session.id,
        stripe_payment_intent_id=getattr(payment_intent, "id", None),
    )

    # Insertar líneas y actualizar stock
    for it in items:
        prod = it.producto
        precio_u = _precio_actual(prod)
        ItemPedido.objects.create(
            pedido=pedido,
            producto=prod,
            cantidad=it.cantidad,
            precio_unitario=precio_u,
        )
        # Descontar stock básico
        if prod.stock is not None:
            prod.stock = max(0, prod.stock - it.cantidad)
            prod.save()

        subtotal += (precio_u * it.cantidad)

    # Actualizar importes y guardar (tu modelo recalcula total en save) :contentReference[oaicite:3]{index=3}
    pedido.subtotal = subtotal.quantize(Decimal("0.01"))
    pedido.save()

    return pedido


def _obtener_carrito_desde_session_o_django(request, stripe_session):
    """Preferimos metadata.cart_id; si no, la sesión de Django."""
    cart_id = None
    try:
        cart_id = int((stripe_session.metadata or {}).get("cart_id"))
    except Exception:
        pass
    if not cart_id:
        cart_id = request.session.get("carrito_id")
    if not cart_id:
        return None
    try:
        return Carrito.objects.get(id=cart_id)
    except Carrito.DoesNotExist:
        return None


def _vaciar_y_cerrar_carrito(request, carrito: Carrito):
    # Usa tu servicio
    try:
        vaciar_carrito(carrito.id)
    except Exception:
        pass
    # Limpia la session key de carrito
    if request.session.get("carrito_id") == carrito.id:
        del request.session["carrito_id"]


def checkout_success(request):
    """URL: /checkout/success?session_id=...  (sin webhook)
    Crea el pedido si el pago está OK y el carrito existe.
    """
    session_id = request.GET.get("session_id")
    if not session_id:
        return HttpResponseBadRequest("Falta session_id")

    # 1) Consultar Stripe para verificar el pago
    try:
        session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent"])
    except Exception as e:
        return HttpResponseBadRequest(f"No se pudo recuperar la sesión de Stripe: {e}")

    if session.payment_status != "paid":
        return HttpResponseBadRequest("El pago no está marcado como 'paid' por Stripe.")

    payment_intent = session.payment_intent

    # 2) Resolver carrito
    carrito = _obtener_carrito_desde_session_o_django(request, session)
    if not carrito:
        return HttpResponseBadRequest("No he encontrado el carrito de la compra.")

    # 3) Resolver cliente (logueado o invitado desde datos de Stripe)
    cliente = _buscar_o_crear_cliente_desde_stripe(request, getattr(session, "customer_details", None))

    # 4) Crear pedido y líneas
    pedido = _crear_pedido_desde_carrito(
        cliente=cliente,
        carrito=carrito,
        stripe_session=session,
        payment_intent=payment_intent,
    )

    # 5) Vaciar carrito
    _vaciar_y_cerrar_carrito(request, carrito)

    # 6) Mostrar pantalla de éxito / devolver JSON
    ctx = {
        "pedido": pedido,
        "tracking": pedido.tracking_token,  # para vista de seguimiento simple que ya tienes
        "session_id": session.id,
    }
    # Puedes renderizar un template bonito:
    return render(request, "core/checkout_success.html", ctx)

def checkout_cancelled(request):
    return HttpResponse("Pago cancelado. Puedes volver al carrito e intentarlo de nuevo.")

def tu_vista_del_carrito(request):
    ctx = {
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, "carrito_widget.html", ctx)

