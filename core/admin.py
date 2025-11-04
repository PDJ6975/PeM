from django.contrib import admin
from .models import Cliente, Producto, Marca, Categoria
from django.contrib.auth.admin import UserAdmin

@admin.register(Cliente)
class ClienteAdmin(UserAdmin):
    model = Cliente
    list_display = ('email', 'nombre', 'apellidos', 'telefono', 'is_staff')
    list_filter = ('is_staff', 'is_superuser')
    ordering = ('email',)
    search_fields = ('email', 'nombre', 'apellidos')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información personal', {'fields': ('nombre', 'apellidos', 'telefono', 'direccion', 'ciudad', 'codigo_postal', 'fecha_creacion')}),
        ('Permisos', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'apellidos', 'telefono', 'direccion', 'ciudad', 'codigo_postal', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'imagen')
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'imagen')
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'marca', 'categoria', 'precio', 'precio_oferta', 'stock', 'esta_disponible', 'es_destacado')
    list_filter = ('marca', 'categoria', 'esta_disponible', 'es_destacado', 'genero')
    search_fields = ('nombre', 'descripcion', 'marca__nombre', 'categoria__nombre')
    ordering = ('nombre',)
    list_editable = ('esta_disponible', 'es_destacado')

    fieldsets = (
        ('Información básica', {
            'fields': ('nombre', 'descripcion', 'imagen')
        }),
        ('Clasificación', {
            'fields': ('marca', 'categoria', 'genero')
        }),
        ('Precios', {
            'fields': ('precio', 'precio_oferta')
        }),
        ('Características', {
            'fields': ('color', 'material')
        }),
        ('Inventario', {
            'fields': ('stock', 'esta_disponible', 'es_destacado')
        }),
    )