# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProductosListView.as_view(), name='home'),
    path('catalogo/', views.ProductosListView.as_view(), name='catalogo'),
    path('sobre-nosotros/', views.sobre_nosotros, name='sobre_nosotros'),
    path('contacto/', views.contacto, name='contacto'),
    path('api/categorias/', views.api_categorias, name='api_categorias'),
    path('api/productos/', views.api_productos, name='api_productos'),

    path('mis-pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('pedidos/seguimiento/', views.pedido_seguimiento_ingresar, name='pedido_seguimiento_ingresar'),
    path('pedidos/seguimiento/<str:numero_pedido>/', views.pedido_seguimiento, name='pedido_seguimiento'),
    path('pedidos/modificar/<str:numero_pedido>/', views.pedido_modificar, name='pedido_modificar'),
    path('pedidos/cancelar/<str:numero_pedido>/', views.pedido_cancelar, name='pedido_cancelar'),
]
