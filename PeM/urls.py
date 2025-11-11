"""
URL configuration for PeM project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

# Personalización del admin para branding
admin.site.site_header = "PeM - Administración"
admin.site.site_title = "PeM Admin"
admin.site.index_title = "Panel de Administración - Juguetes para Mascotas"

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Página principal
    path('', views.home, name='home'),

    # API REST - Carrito
    path('api/carrito/', views.ObtenerCarritoView.as_view(), name='api_carrito_obtener'),
    path('api/carrito/agregar/', views.AgregarProductoView.as_view(), name='api_carrito_agregar'),
    path('api/carrito/modificar/', views.ModificarCantidadView.as_view(), name='api_carrito_modificar'),
    path('api/carrito/eliminar/<int:producto_id>/', views.EliminarProductoView.as_view(), name='api_carrito_eliminar'),
    path('api/carrito/vaciar/', views.VaciarCarritoView.as_view(), name='api_carrito_vaciar'),

    # API REST - Pedidos ADMIN
    path('api/admin/pedidos/', views.admin_pedidos_lista, name='admin_pedidos_lista'),
    path('api/admin/pedidos/<int:pedido_id>/', views.admin_pedido_detalle, name='admin_pedido_detalle'),
    path('api/admin/pedidos/<int:pedido_id>/cambiar-estado/', views.admin_pedido_cambiar_estado, name='admin_pedido_cambiar_estado'),
    path('api/admin/pedidos/<int:pedido_id>/cancelar/', views.admin_pedido_cancelar, name='admin_pedido_cancelar'),
    path('api/admin/pedidos/estadisticas/', views.admin_pedidos_estadisticas, name='admin_pedidos_estadisticas'),
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
