from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('login/', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # API REST - Carrito
    path('api/carrito/', views.ObtenerCarritoView.as_view(), name='api_carrito_obtener'),
    path('api/carrito/agregar/', views.AgregarProductoView.as_view(), name='api_carrito_agregar'),
    path('api/carrito/modificar/', views.ModificarCantidadView.as_view(), name='api_carrito_modificar'),
    path('api/carrito/eliminar/<int:producto_id>/', views.EliminarProductoView.as_view(), name='api_carrito_eliminar'),
    path('api/carrito/vaciar/', views.VaciarCarritoView.as_view(), name='api_carrito_vaciar'),

    # API REST - Usuarios y Autenticación
    path('api/auth/register/', views.RegisterView.as_view(), name='api_auth_register'),
    path('api/auth/login/', views.LoginView.as_view(), name='api_auth_login'),

    # API REST - Consulta de Pedido sin Cuenta
    path("seguimiento/<uuid:tracking_token>/", views.SeguimientoPorTokenView.as_view(), name="seguimiento_por_token"),
    path("api/carrito/procesar-pago/", views.create_checkout_session, name="create_checkout_session"),
        # NUEVAS rutas de post-pago
    path("checkout/success", views.checkout_success, name="checkout_success"),
    path("checkout/cancelled", views.checkout_cancelled, name="checkout_cancelled"),
    path("checkout/cod/", views.checkout_cod, name="checkout_cod"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
