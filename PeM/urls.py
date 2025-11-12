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

    # API REST - Pedidos ADMIN --> COMENTADO POR AHORA HASTA QUE 
    # SEPAMOS QUE PANEL DE ADMINISTRACIÓN QUIERE EL CLIENTE
    
    # path('api/admin/pedidos/', views.admin_pedidos_lista, name='admin_pedidos_lista'),
    # path('api/admin/pedidos/<int:pedido_id>/', views.admin_pedido_detalle, name='admin_pedido_detalle'),
    # path('api/admin/pedidos/<int:pedido_id>/cambiar-estado/', views.admin_pedido_cambiar_estado, name='admin_pedido_cambiar_estado'),
    # path('api/admin/pedidos/<int:pedido_id>/cancelar/', views.admin_pedido_cancelar, name='admin_pedido_cancelar'),
    # path('api/admin/pedidos/estadisticas/', views.admin_pedidos_estadisticas, name='admin_pedidos_estadisticas'),

    # API REST - Usuarios y Autenticación
    path('api/auth/register/', views.RegisterView.as_view(), name='api_auth_register'),
    path('api/auth/login/', views.LoginView.as_view(), name='api_auth_login'),

    # API REST - Consulta de Pedido sin Cuenta
    path('seguimiento/<uuid:tracking_token>/', views.SeguimientoPedidoView.as_view(), name='seguimiento_pedido'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
