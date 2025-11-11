from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
import json

from core.services import carrito as carrito_service


def home(request):
    """Vista de la página de inicio"""
    return render(request, 'core/index.html')


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
