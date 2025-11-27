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
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from core.services.catalogo import buscar_productos, obtener_productos_destacados
from core.models import Producto
from .models import Categoria, Marca
import json
import logging

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

from decimal import Decimal

import stripe

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest
from django.utils.crypto import get_random_string

from core.models.carrito import Carrito
from core.models.item_carrito import ItemCarrito
from core.models.pedido import Pedido
from core.models.item_pedido import ItemPedido
from core.models.cliente import Cliente
from core.services import carrito as carrito_service
from core.services.carrito import vaciar_carrito





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

def sobre_nosotros(request):
    return render(request, 'core/sobre_nosotros.html')

def contacto(request):
    return render(request, 'core/contacto.html')

def catalogo_marcas(request):
    q = (request.GET.get("q") or "").strip()
    categoria_id = request.GET.get("categoria") or ""

    # Base: productos disponibles
    productos_qs = (
        Producto.objects
        .select_related("marca", "categoria")
        .filter(esta_disponible=True)
    )

    # Filtro por nombre / descripción / marca
    if q:
        productos_qs = productos_qs.filter(
            Q(nombre__icontains=q) |
            Q(descripcion__icontains=q) |
            Q(marca__nombre__icontains=q)
        )

    # Filtro por categoría (tipo)
    if categoria_id:
        productos_qs = productos_qs.filter(categoria_id=categoria_id)

    productos_qs = productos_qs.order_by("marca__nombre", "nombre")

    # Prefetch solo de los productos filtrados, agrupados por marca
    marcas = (
        Marca.objects
        .filter(productos__in=productos_qs)
        .distinct()
        .order_by("nombre")
        .prefetch_related(
            Prefetch("productos", queryset=productos_qs, to_attr="productos_filtrados")
        )
    )

    categorias = Categoria.objects.order_by("nombre")
    total_productos = productos_qs.count()

    contexto = {
        "marcas": marcas,
        "categorias": categorias,
        "total_productos": total_productos,
        "filtros": {
            "q": q,
            "categoria": categoria_id,
        },
    }
    return render(request, "core/catalogo_marcas.html", contexto)

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
        Obtiene o crea el ID del carrito con persistencia para usuarios registrados.

        Comportamiento:
        - Usuarios autenticados: carrito persistido en BD (no depende de sesión)
        - Usuarios anónimos: carrito almacenado en sesión
        - Al autenticarse, migra automáticamente carrito anónimo al registrado
        """
        if not request.session.session_key:
            request.session.create()

        # === USUARIOS AUTENTICADOS ===
        if request.user.is_authenticated:
            # 1. Buscar carrito del usuario registrado en BD
            carrito = Carrito.objects.filter(cliente=request.user).first()

            # 2. Verificar si hay carrito anónimo en sesión para migrar
            carrito_anonimo_id = request.session.get('carrito_id')

            if carrito_anonimo_id:
                try:
                    # Usar transacción atómica para PostgreSQL
                    with transaction.atomic():
                        # Bloquear el carrito anónimo para evitar race conditions
                        carrito_anonimo = Carrito.objects.select_for_update().get(
                            id=carrito_anonimo_id,
                            cliente__isnull=True
                        )

                        if carrito:
                            # Ya tiene carrito registrado: migrar productos del anónimo
                            carrito_service.migrar_carrito(carrito_anonimo_id, request.user)
                        else:
                            # No tiene carrito registrado: convertir el anónimo en suyo
                            carrito_anonimo.cliente = request.user
                            carrito_anonimo.save()
                            carrito = carrito_anonimo

                    # Limpiar carrito anónimo de la sesión
                    del request.session['carrito_id']

                except Carrito.DoesNotExist:
                    # El carrito de sesión ya no existe, limpiar referencia
                    del request.session['carrito_id']

            # 3. Si no tiene carrito, crear uno nuevo
            if not carrito:
                carrito = carrito_service.obtener_o_crear_carrito(cliente=request.user)

            return carrito.id

        # === USUARIOS ANÓNIMOS ===
        carrito_id = request.session.get('carrito_id')

        if not carrito_id:
            # Crear nuevo carrito anónimo
            carrito = carrito_service.obtener_o_crear_carrito(cliente=None)
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

            # Agregar producto
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
            # Log del error
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
# API REST para Usuarios y Autenticación
# ============================================

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(View):
    """
    POST /api/auth/register/
    Registra un nuevo cliente.
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

            # === MIGRACIÓN  DE CARRITO ===
            # Si el usuario tenía un carrito anónimo, migrarlo al carrito del usuario
            carrito_anonimo_id = request.session.get('carrito_id')

            if carrito_anonimo_id:
                try:
                    # Usar transacción atómica para PostgreSQL
                    with transaction.atomic():
                        # Bloquear el carrito anónimo para evitar race conditions
                        carrito_anonimo = Carrito.objects.select_for_update().get(
                            id=carrito_anonimo_id,
                            cliente__isnull=True
                        )

                        # Buscar si el usuario ya tiene un carrito
                        carrito_usuario = Carrito.objects.filter(cliente=cliente).first()

                        if carrito_usuario:
                            # Migrar productos del carrito anónimo al del usuario
                            carrito_service.migrar_carrito(carrito_anonimo_id, cliente)
                        else:
                            # Convertir el carrito anónimo en el carrito del usuario
                            carrito_anonimo.cliente = cliente
                            carrito_anonimo.save()

                    # Limpiar referencia del carrito anónimo en la sesión
                    del request.session['carrito_id']

                except Carrito.DoesNotExist:
                    # El carrito ya no existe, limpiar la sesión
                    if 'carrito_id' in request.session:
                        del request.session['carrito_id']
                except Exception as e:
                    # Error en migración, registrar pero no fallar el login
                    logger.error(f"Error migrando carrito en login: {e}", exc_info=True)

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


class SeguimientoPorTokenView(View):
    """
    Vista accesible desde el enlace enviado al correo.
    Muestra el estado del pedido usando su tracking_token.
    """
    template_name = "core/seguimiento_pedido.html"

    def get(self, request, tracking_token):
        pedido = get_object_or_404(Pedido, tracking_token=tracking_token)

        items = [
            {
                "producto": item.producto.nombre,
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
                "subtotal": item.precio_unitario * item.cantidad
            }
            for item in pedido.items.all()
        ]

        return render(request, self.template_name, {
            "pedido": pedido,
            "items": items,
            "success": True,
            "from_token": True
        })


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
        "precio": str(p.precio_actual()),  
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



stripe.api_key = settings.STRIPE_SECRET_KEY

def _build_line_items(carrito_id):
    """
    Convierte los ItemCarrito a line_items de Stripe.
    Usa Producto.precio_actual() para reflejar oferta si aplica.
    Incluye los gastos de envío como un line item adicional (aplicando lógica de envío gratuito).
    Acepta un ID de carrito (int) o instancia; aquí usamos ID.
    """
    items = (
        ItemCarrito.objects
        .select_related("producto")
        .filter(carrito=carrito_id)
    )

    line_items = []
    subtotal = Decimal('0.00')

    # Construir line items de productos y calcular subtotal
    for it in items:
        producto = it.producto
        precio_unitario = Decimal(producto.precio_actual())
        unit_amount = int(precio_unitario * 100)  # céntimos

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

        subtotal += precio_unitario * it.cantidad

    # Calcular coste de envío basándose en el subtotal 
    coste_envio = _calcular_coste_envio(subtotal)
    coste_estandar = getattr(settings, 'COSTE_ENVIO_ESTANDAR', Decimal('4.95'))
    importe_minimo = getattr(settings, 'IMPORTE_ENVIO_GRATUITO', Decimal('50.00'))

    nombre_envio = "Gastos de envío"

    line_items.append({
        "price_data": {
            "currency": "eur",
            "product_data": {
                "name": nombre_envio,
                "description": f"Envío estándar: {coste_estandar}€. Gratis a partir de {importe_minimo}€" if coste_envio == 0 else None,
            },
            "unit_amount": int(coste_envio * 100), 
        },
        "quantity": 1,
    })

    return line_items

@csrf_exempt
def create_checkout_session(request):
    logger.debug(
        f"[Stripe Checkout] Iniciando sesión de pago - "
        f"method={request.method}, user={request.user}, "
        f"authenticated={request.user.is_authenticated}"
    )

    if request.method != "POST":
        logger.warning(f"[Stripe Checkout] Método no permitido: {request.method}")
        return HttpResponseBadRequest("Método no permitido")

    # --- Recuperar carrito ---
    carrito_id = None

    if request.user.is_authenticated:
        # Usuario autenticado: obtener carrito desde relación
        try:
            carrito_id = request.user.carrito.id
            logger.debug(f"[Stripe Checkout] Carrito de usuario autenticado: {carrito_id}")
        except AttributeError:
            logger.warning("[Stripe Checkout] Usuario autenticado sin carrito")
            return HttpResponseBadRequest("No tienes un carrito")
    else:
        # Usuario anónimo: obtener carrito de la sesión
        carrito_id = request.session.get("carrito_id")
        logger.debug(f"[Stripe Checkout] Carrito ID en sesión (anónimo): {carrito_id}")

    if not carrito_id:
        logger.warning("[Stripe Checkout] No hay carrito disponible")
        return HttpResponseBadRequest("No hay carrito en la sesión")

    # --- Verificar que hay items en el carrito ---
    items_qs = ItemCarrito.objects.filter(carrito=carrito_id)
    num_items = items_qs.count()
    logger.debug(f"[Stripe Checkout] Número de items en carrito: {num_items}")

    if not items_qs.exists():
        logger.warning(f"[Stripe Checkout] Carrito {carrito_id} está vacío")
        return HttpResponseBadRequest("El carrito está vacío")

    # --- Construir line_items para Stripe ---
    line_items = _build_line_items(carrito_id)
    logger.debug(f"[Stripe Checkout] Line items construidos: {len(line_items)} items")

    success_url = settings.STRIPE_SUCCESS_URL
    cancel_url = settings.STRIPE_CANCEL_URL

    # --- Metadata mínima para el webhook ---
    metadata = {
        "cart_id": str(carrito_id),
    }
    if request.user.is_authenticated:
        metadata["user_id"] = str(request.user.id)

    session_kwargs = {
        "mode": "payment",
        "line_items": line_items,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(carrito_id),
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
        logger.error(
            f"[Stripe Checkout] Error creando sesión: {e.user_message or str(e)}",
            exc_info=True,
            extra={'stripe_code': getattr(e, 'code', None)}
        )
        return HttpResponseBadRequest(getattr(e, "user_message", "Error con Stripe"))

    request.session["stripe_session_id"] = session.id
    logger.info(f"[Stripe Checkout] Sesión creada exitosamente: {session.id}")

    return JsonResponse({"id": session.id, "url": session.url})

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
    return producto.precio_actual()


def _calcular_coste_envio(subtotal: Decimal) -> Decimal:
    """
    Calcula el coste de envío basándose en el subtotal del pedido.
    Envío gratuito si el subtotal supera el importe mínimo configurado.

    Args:
        subtotal: Subtotal del carrito/pedido (sin gastos de envío)

    Returns:
        Decimal: Coste de envío (0.00 si es gratuito)
    """
    importe_minimo = getattr(settings, 'IMPORTE_ENVIO_GRATUITO', Decimal('50.00'))
    coste_estandar = getattr(settings, 'COSTE_ENVIO_ESTANDAR', Decimal('4.95'))

    if subtotal >= importe_minimo:
        return Decimal('0.00')

    return coste_estandar 


def _buscar_o_crear_cliente_desde_stripe(request, customer_details):
    """
    Si el usuario está autenticado, seguimos usando su cuenta (y opcionalmente
    actualizamos campos con lo que devuelva Stripe, como hasta ahora).

    Si NO está autenticado, NO creamos cuentas nuevas con datos de Stripe.
    En su lugar, usamos una cuenta anónima única para todos los pedidos invitados.
    El email por defecto es settings.ANON_ORDER_EMAIL o 'anon@orders.local'.
    """
    # 1) Usuario autenticado: conservar el comportamiento actual (actualiza datos si vienen de Stripe)
    if request.user.is_authenticated:
        if customer_details:
            nombre_completo = (customer_details.name or "").strip()
            partes = nombre_completo.split()
            nombre = partes[0] if partes else ""
            apellidos = " ".join(partes[1:]) if len(partes) > 1 else ""
            telefono = (customer_details.phone or "").strip()

            address = getattr(customer_details, "address", None) or {}
            direccion = (address.get("line1") or "").strip()
            ciudad = (address.get("city") or "").strip()
            cp = (address.get("postal_code") or "").strip()

            cli = request.user
            cambios = False
            for campo, valor in [
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
        return request.user

    # 2) Usuario NO autenticado: usar/crear cuenta anónima fija
    anon_email = getattr(settings, "ANON_ORDER_EMAIL", "anon@orders.local")

    cli = Cliente.objects.filter(email__iexact=anon_email).first()
    if cli:
        return cli

    # Crear la cuenta anónima si no existe
    with transaction.atomic():
        cli = Cliente.objects.create_user(
            email=anon_email,
            password=get_random_string(32), 
            nombre="Anónimo",
            apellidos="Pedido",
        )
        # Opcional: desactivar login para esta cuenta
        try:
            cli.is_active = False
            cli.save(update_fields=["is_active"])
        except Exception:
            pass
        return cli

def _crear_pedido_desde_carrito(*,
                                cliente: Cliente,
                                carrito: Carrito,
                                stripe_session=None,
                                payment_intent=None,
                                direccion_envio_override: str | None = None,
                                telefono_override: str | None = None):
    """Crea Pedido + sus líneas a partir del carrito."""
    subtotal = Decimal(0)
    items = ItemCarrito.objects.select_related("producto").filter(carrito=carrito)

    direccion_envio = (
        direccion_envio_override
        or _fmt_direccion(getattr(stripe_session, "customer_details", None))
        or "Dirección no facilitada"
    )
    telefono = (
        (telefono_override or "").strip()
        or ((getattr(stripe_session, "customer_details", {}) or {}).get("phone") or "").strip()
        or "600000000"
    )

    # Calcular subtotal primero
    for it in items:
        prod = it.producto
        precio_u = _precio_actual(prod)
        subtotal += (precio_u * it.cantidad)

    # Calcular coste de envío basándose en el subtotal (puede ser 0 si es gratuito)
    coste_envio = _calcular_coste_envio(subtotal)

    pedido = Pedido.objects.create(
        cliente=cliente,
        estado="confirmado",
        subtotal=Decimal("0.00"),
        impuestos=Decimal("0.00"),
        coste_entrega=coste_envio,
        descuento=Decimal("0.00"),
        total=Decimal("0.00"),
        direccion_envio=direccion_envio,
        telefono=telefono,
        stripe_session_id=getattr(stripe_session, "id", None),
        stripe_payment_intent_id=getattr(payment_intent, "id", None),
    )

    # Crear items del pedido y descontar stock
    for it in items:
        prod = it.producto
        precio_u = _precio_actual(prod)
        ItemPedido.objects.create(
            pedido=pedido,
            producto=prod,
            cantidad=it.cantidad,
            precio_unitario=precio_u,
        )
        if prod.stock is not None:
            prod.stock = max(0, prod.stock - it.cantidad)
            prod.save()

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
    try:
        vaciar_carrito(carrito.id)
    except Exception:
        pass
    # Limpia la session key de carrito
    if request.session.get("carrito_id") == carrito.id:
        del request.session["carrito_id"]


def _enviar_email_confirmacion_async(pedido_id, email, is_authenticated):
    """
    Función auxiliar para enviar email de confirmación en segundo plano.
    Se ejecuta en un thread separado para no bloquear la respuesta HTTP.
    """
    try:
        from django.db import connection
        # Cerrar la conexión de DB heredada del thread principal
        connection.close()

        pedido = Pedido.objects.get(id=pedido_id)
        logger.info(f"[Email Async] Enviando email para pedido {pedido.numero_pedido} a {email}")

        # Enviar email con fail_silently=True dentro del método
        pedido.enviar_correo_confirmacion(email_stripe=email, request=None)

        logger.info(f"[Email Async] Email enviado exitosamente para pedido {pedido.numero_pedido}")
    except Pedido.DoesNotExist:
        logger.error(f"[Email Async] Pedido {pedido_id} no encontrado")
    except Exception as e:
        logger.error(f"[Email Async] Error enviando email para pedido {pedido_id}: {e}", exc_info=True)


def checkout_success(request):
    """URL: /checkout/success?session_id=...  (sin webhook)
    Crea el pedido si el pago está OK y el carrito existe.
    """
    session_id = request.GET.get("session_id")
    if not session_id:
        logger.warning("[Checkout Success] Falta session_id en la URL")
        return HttpResponseBadRequest("Falta session_id")

    logger.info(f"[Checkout Success] Procesando session_id: {session_id}")

    # 1) Consultar Stripe para verificar el pago
    try:
        session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent"])
        logger.info(f"[Checkout Success] Sesión recuperada. Payment status: {session.payment_status}")
    except Exception as e:
        logger.error(f"[Checkout Success] Error recuperando sesión de Stripe: {e}", exc_info=True)
        return HttpResponseBadRequest(f"No se pudo recuperar la sesión de Stripe: {e}")

    if session.payment_status != "paid":
        logger.warning(f"[Checkout Success] Pago no completado. Status: {session.payment_status}")
        return HttpResponseBadRequest("El pago no está marcado como 'paid' por Stripe.")

    payment_intent = session.payment_intent

    # 1.5) Verificar si ya existe un pedido con este stripe_session_id (prevenir duplicados)
    pedido_existente = Pedido.objects.filter(stripe_session_id=session_id).first()
    if pedido_existente:
        logger.info(f"[Checkout Success] Pedido ya existe: {pedido_existente.numero_pedido}. Mostrando pedido existente.")
        ctx = {
            "pedido": pedido_existente,
            "tracking": pedido_existente.tracking_token,
            "session_id": session.id,
        }
        return render(request, "core/checkout_success.html", ctx)

    # 2) Resolver carrito
    carrito = _obtener_carrito_desde_session_o_django(request, session)
    if not carrito:
        logger.error("[Checkout Success] No se encontró el carrito")
        return HttpResponseBadRequest("No he encontrado el carrito de la compra.")

    logger.info(f"[Checkout Success] Carrito encontrado: {carrito.id}")

    # 3) Resolver cliente (logueado o invitado desde datos de Stripe)
    cliente = _buscar_o_crear_cliente_desde_stripe(request, getattr(session, "customer_details", None))
    logger.info(f"[Checkout Success] Cliente: {cliente.email}")

    # 4) Crear pedido y líneas
    logger.info("[Checkout Success] Creando pedido...")
    pedido = _crear_pedido_desde_carrito(
        cliente=cliente,
        carrito=carrito,
        stripe_session=session,
        payment_intent=payment_intent
    )
    logger.info(f"[Checkout Success] Pedido creado: {pedido.numero_pedido}")

    # 5) Enviar email de confirmación
    raw_email = session.customer_details.email
    email = raw_email.lower()

    logger.info(f"[Checkout Success] Intentando enviar email a: {email}")

    # En tests, enviar email de forma síncrona para evitar problemas de concurrencia con SQLite
    # En producción, usar threading para no bloquear la respuesta
    import sys
    is_testing = 'test' in sys.argv or hasattr(settings, 'TESTING')

    if is_testing:
        # Modo test: envío síncrono
        try:
            pedido.enviar_correo_confirmacion(email_stripe=email, request=request)
            logger.info("[Checkout Success] Email enviado (modo test)")
        except Exception as e:
            logger.error(f"[Checkout Success] Error enviando email: {e}", exc_info=True)
    else:
        # Modo producción: envío asíncrono
        try:
            import threading
            email_thread = threading.Thread(
                target=_enviar_email_confirmacion_async,
                args=(pedido.id, email, request.user.is_authenticated)
            )
            email_thread.start()
            logger.info("[Checkout Success] Thread de email iniciado")
        except Exception as e:
            logger.error(f"[Checkout Success] Error iniciando thread de email: {e}", exc_info=True)

    # 6) Vaciar carrito
    logger.info("[Checkout Success] Vaciando carrito...")
    _vaciar_y_cerrar_carrito(request, carrito)

    if not request.user.is_authenticated:
        request.session['pedido_acceso_temporal'] = {
            'numero_pedido': pedido.numero_pedido,
            'tracking_token': str(pedido.tracking_token),
            'timestamp': timezone.now().isoformat()
        }
        logger.info(f"[Checkout Success] Acceso temporal guardado para pedido {pedido.numero_pedido}")

    # 7) Mostrar pantalla de éxito
    logger.info(f"[Checkout Success] Renderizando template de éxito para pedido {pedido.numero_pedido}")
    ctx = {
        "pedido": pedido,
        "tracking": pedido.tracking_token,
        "session_id": session.id,
    }
    return render(request, "core/checkout_success.html", ctx)

def checkout_cancelled(request):
    return HttpResponse("Pago cancelado. Puedes volver al carrito e intentarlo de nuevo.")

def tu_vista_del_carrito(request):
    ctx = {
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, "carrito_widget.html", ctx)

from django.views.decorators.http import require_POST
@require_POST
def checkout_cod(request):
    if not request.user.is_authenticated:
        return HttpResponseBadRequest("Inicia sesión para pagar contra reembolso.")

    # --- Leer JSON con dirección (enviado por el widget) ---
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        data = {}

    direccion = (data.get("direccion") or "").strip()
    ciudad    = (data.get("ciudad") or "").strip()
    cp        = (data.get("codigo_postal") or "").strip()
    telefono  = (data.get("telefono") or "").strip()

    # Validación mínima (ajusta a tu gusto)
    if not direccion or not ciudad or not cp:
        return HttpResponseBadRequest("Falta dirección, ciudad o código postal.")

    # --- Recuperar carrito ---
    carrito_id = None

    if request.user.is_authenticated:
        # Usuario autenticado: obtener carrito desde relación
        try:
            carrito_id = request.user.carrito.id
            logger.debug(f"[Stripe Checkout] Carrito de usuario autenticado: {carrito_id}")
        except AttributeError:
            logger.warning("[Stripe Checkout] Usuario autenticado sin carrito")
            return HttpResponseBadRequest("No tienes un carrito")
    else:
        # Usuario anónimo: obtener carrito de la sesión
        carrito_id = request.session.get("carrito_id")
        logger.debug(f"[Stripe Checkout] Carrito ID en sesión (anónimo): {carrito_id}")

    if not carrito_id:
        logger.warning("[Stripe Checkout] No hay carrito disponible")
        return HttpResponseBadRequest("No hay carrito en la sesión")

    try:
        carrito = Carrito.objects.get(pk=carrito_id)
    except Carrito.DoesNotExist:
        return HttpResponseBadRequest("Carrito no encontrado.")

    direccion_envio_str = ", ".join([x for x in [direccion, f"{cp} {ciudad}".strip()] if x])

    with transaction.atomic():
        pedido = _crear_pedido_desde_carrito(
            cliente=request.user,
            carrito=carrito,
            stripe_session=None,         
            payment_intent=None,
            direccion_envio_override=direccion_envio_str,   
            telefono_override=telefono or "600000000",       
        )

    email = request.user.email
    print("este es el correo")
    print(email)

    try:
        pedido.enviar_correo_confirmacion(email_stripe=email, request=request)
    except Exception as e:
        logger.error(f"No se pudo enviar email de confirmación: {e}")

    _vaciar_y_cerrar_carrito(request, carrito)

    # Devolvemos HTML
    ctx = {
        "pedido": pedido,
        "tracking": pedido.tracking_token,
        "pago_cod": True,
    }
    return render(request, "core/checkout_success.html", ctx)
    
def mis_pedidos(request):
    # Si no está logeado, pide número de pedido
    if not request.user.is_authenticated:
        return redirect('pedido_seguimiento_ingresar')

    pedidos = (Pedido.objects
               .filter(cliente=request.user)
               .order_by('-fecha_creacion')
               .prefetch_related('items__producto'))
    return render(request, 'core/mis_pedidos.html', {'pedidos': pedidos})

def pedido_seguimiento_ingresar(request):
    error = None
    if request.method == 'POST':
        numero_pedido = (request.POST.get('numero_pedido') or '').strip()
        tracking_token = (request.POST.get('tracking_token') or '').strip()
        
        if not numero_pedido or not tracking_token:
            error = 'Debes introducir tanto el número de pedido como el token de seguimiento.'
        else:
            # Validar que ambos coincidan con un pedido existente
            try:
                pedido = Pedido.objects.get(
                    numero_pedido=numero_pedido,
                    tracking_token=tracking_token
                )
                # Guardar en sesión para acceso temporal (sin login)
                request.session['pedido_acceso_temporal'] = {
                    'numero_pedido': numero_pedido,
                    'tracking_token': str(tracking_token),
                    'timestamp': timezone.now().isoformat()
                }
                return redirect('pedido_seguimiento', numero_pedido=numero_pedido)
            except Pedido.DoesNotExist:
                error = 'Número de pedido o token de seguimiento incorrectos.'
            except ValidationError:
                error = 'Formato de token inválido.'
                
    return render(request, 'core/pedido_seguimiento_ingresar.html', {'error': error})


def pedido_seguimiento(request, numero_pedido):
    pedido = get_object_or_404(Pedido.objects.prefetch_related('items__producto'), numero_pedido=numero_pedido)

    # Control de acceso
    es_propietario = False
    tiene_acceso = False
    
    if request.user.is_authenticated:
        # Usuario autenticado
        if request.user.is_staff or pedido.cliente_id == request.user.id:
            tiene_acceso = True
            es_propietario = (pedido.cliente_id == request.user.id)
        else:
            messages.error(request, 'No tienes acceso a este pedido.')
            return redirect('mis_pedidos')
    else:
        # Usuario anónimo: verificar acceso temporal
        acceso_temporal = request.session.get('pedido_acceso_temporal')
        
        if acceso_temporal:
            # Verificar que el acceso es para este pedido específico
            if (acceso_temporal.get('numero_pedido') == numero_pedido and 
                acceso_temporal.get('tracking_token') == str(pedido.tracking_token)):
                
                # Verificar que el acceso no ha expirado (opcional: 1 hora)
                try:
                    timestamp = timezone.datetime.fromisoformat(acceso_temporal['timestamp'])
                    if timezone.now() - timestamp < timezone.timedelta(hours=1):
                        tiene_acceso = True
                        es_propietario = True  # Tiene acceso completo con token válido
                    else:
                        messages.warning(request, 'Tu sesión de seguimiento ha expirado. Por favor, introduce los datos nuevamente.')
                        return redirect('pedido_seguimiento_ingresar')
                except (KeyError, ValueError):
                    pass
        
        if not tiene_acceso:
            messages.error(request, 'Debes proporcionar el número de pedido y el token de seguimiento.')
            return redirect('pedido_seguimiento_ingresar')

    return render(request, 'core/pedido_seguimiento.html', {
        'pedido': pedido,
        'items': pedido.items.all(),
        'es_propietario': es_propietario
    })


def _verificar_acceso_pedido(request, pedido):
    """
    Verifica si el usuario tiene acceso al pedido.
    Retorna (tiene_acceso: bool, es_propietario: bool)
    """
    if request.user.is_authenticated:
        if request.user.is_staff:
            return (True, False)
        if pedido.cliente_id == request.user.id:
            return (True, True)
        return (False, False)
    
    # Usuario anónimo: verificar sesión temporal
    acceso_temporal = request.session.get('pedido_acceso_temporal')
    if not acceso_temporal:
        return (False, False)
    
    if (acceso_temporal.get('numero_pedido') == pedido.numero_pedido and 
        acceso_temporal.get('tracking_token') == str(pedido.tracking_token)):
        try:
            timestamp = timezone.datetime.fromisoformat(acceso_temporal['timestamp'])
            if timezone.now() - timestamp < timezone.timedelta(hours=1):
                return (True, True)
        except (KeyError, ValueError):
            pass
    
    return (False, False)


def pedido_modificar(request, numero_pedido):
    pedido = get_object_or_404(Pedido.objects.prefetch_related('items__producto'), numero_pedido=numero_pedido)
    
    # Verificar acceso
    tiene_acceso, es_propietario = _verificar_acceso_pedido(request, pedido)
    
    if not tiene_acceso:
        messages.error(request, 'No tienes acceso a este pedido.')
        if request.user.is_authenticated:
            return redirect('mis_pedidos')
        return redirect('pedido_seguimiento_ingresar')
    
    if not es_propietario and not request.user.is_staff:
        messages.error(request, 'No tienes permiso para modificar este pedido.')
        return redirect('pedido_seguimiento', numero_pedido=numero_pedido)
    
    # Verificar que se puede modificar
    if not pedido.puede_modificar():
        messages.warning(request, 'Este pedido ya no puede ser modificado.')
        return redirect('pedido_seguimiento', numero_pedido=numero_pedido)
    
    if request.method == 'POST':
        direccion_envio = request.POST.get('direccion_envio', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        
        if not direccion_envio:
            messages.error(request, 'La dirección de envío es obligatoria.')
        elif not telefono:
            messages.error(request, 'El teléfono es obligatorio.')
        else:
            pedido.direccion_envio = direccion_envio
            pedido.telefono = telefono
            try:
                pedido.save()
                messages.success(request, f'El pedido #{pedido.numero_pedido} ha sido actualizado correctamente.')
                return redirect('pedido_seguimiento', numero_pedido=numero_pedido)
            except ValidationError as e:
                messages.error(request, f'Error al actualizar: {e}')
    
    return render(request, 'core/pedido_modificar.html', {
        'pedido': pedido,
        'items': pedido.items.all()
    })


def pedido_cancelar(request, numero_pedido):
    if request.method != 'POST':
        return redirect('pedido_seguimiento', numero_pedido=numero_pedido)
    
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido)
    
    # Verificar acceso
    tiene_acceso, es_propietario = _verificar_acceso_pedido(request, pedido)
    
    if not tiene_acceso:
        messages.error(request, 'No tienes acceso a este pedido.')
        if request.user.is_authenticated:
            return redirect('mis_pedidos')
        return redirect('pedido_seguimiento_ingresar')
    
    if not es_propietario and not request.user.is_staff:
        messages.error(request, 'No tienes permiso para cancelar este pedido.')
        return redirect('pedido_seguimiento', numero_pedido=numero_pedido)
    
    # Verificar que se puede cancelar
    if not pedido.puede_cancelar():
        messages.warning(request, 'Este pedido ya no puede ser cancelado.')
        return redirect('pedido_seguimiento', numero_pedido=numero_pedido)
    
    pedido.estado = 'cancelado'
    pedido.save()
    messages.success(request, f'El pedido #{pedido.numero_pedido} ha sido cancelado correctamente.')
    
    return redirect('pedido_seguimiento', numero_pedido=numero_pedido)
