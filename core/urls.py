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


]
