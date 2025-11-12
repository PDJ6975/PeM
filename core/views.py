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

from core.services import carrito as carrito_service
from core.services.pedido import PedidoService


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