# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProductosListView.as_view(), name='home'),
    path('catalogo/', views.ProductosListView.as_view(), name='catalogo'),
    # Endpoints JSON:
    path('api/categorias/', views.api_categorias, name='api_categorias'),
    path('api/productos/', views.api_productos, name='api_productos'),

    path('api/carrito/procesar-pago/', views.ProcesarPagoView.as_view(), name='carrito_procesar_pago'),

]
