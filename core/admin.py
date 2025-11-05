from django.contrib import admin
from .models import Cliente, Producto, Marca, Categoria, Pedido, ItemPedido
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


# Inline para mostrar items dentro del pedido
class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    fields = ('producto', 'cantidad', 'precio_unitario', 'total')
    readonly_fields = ('total',)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('numero_pedido', 'cliente', 'estado', 'total', 'fecha_creacion', 'puede_cancelar_display')
    list_filter = ('estado', 'fecha_creacion')
    search_fields = ('numero_pedido', 'cliente__email', 'cliente__nombre', 'cliente__apellidos')
    ordering = ('-fecha_creacion',)
    readonly_fields = ('numero_pedido', 'fecha_creacion', 'fecha_actualizacion', 'total', 'stripe_payment_intent_id', 'stripe_session_id')
    list_editable = ('estado',)
    inlines = [ItemPedidoInline]
    actions = ['confirmar_pedidos', 'marcar_como_enviado', 'marcar_como_entregado', 'cancelar_pedidos']

    fieldsets = (
        ('Información del Pedido', {
            'fields': ('numero_pedido', 'cliente', 'estado', 'fecha_creacion', 'fecha_actualizacion')
        }),
        ('Información de Pago (Stripe)', {
            'fields': ('stripe_payment_intent_id', 'stripe_session_id')
        }),
        ('Montos', {
            'fields': ('subtotal', 'impuestos', 'coste_entrega', 'descuento', 'total')
        }),
        ('Información de Envío', {
            'fields': ('direccion_envio', 'telefono')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Hace que ciertos campos sean de solo lectura después de la creación.
        """
        if obj:  # Si el objeto ya existe (editando)
            return self.readonly_fields + ('cliente', 'subtotal')
        return self.readonly_fields

    def puede_cancelar_display(self, obj):
        """Muestra si el pedido puede ser cancelado"""
        return obj.puede_cancelar()
    
    puede_cancelar_display.short_description = "¿Cancelable?"
    puede_cancelar_display.boolean = True 

    def confirmar_pedidos(self, request, queryset):
        """Confirma los pedidos seleccionados que estén pendientes"""
        actualizados = 0
        for pedido in queryset:
            if pedido.confirmar_pedido():
                actualizados += 1
        
        if actualizados == 1:
            message = "1 pedido fue confirmado."
        else:
            message = f"{actualizados} pedidos fueron confirmados."
        self.message_user(request, message)
    confirmar_pedidos.short_description = "Confirmar pedidos seleccionados"

    def marcar_como_enviado(self, request, queryset):
        """Marca como enviados los pedidos seleccionados"""
        actualizados = 0
        for pedido in queryset:
            if pedido.marcar_como_enviado():
                actualizados += 1
        
        if actualizados == 1:
            message = "1 pedido fue marcado como enviado."
        else:
            message = f"{actualizados} pedidos fueron marcados como enviados."
        self.message_user(request, message)
    marcar_como_enviado.short_description = "Marcar como enviado"

    def marcar_como_entregado(self, request, queryset):
        """Marca como entregados los pedidos seleccionados"""
        actualizados = 0
        for pedido in queryset:
            if pedido.marcar_como_entregado():
                actualizados += 1
        
        if actualizados == 1:
            message = "1 pedido fue marcado como entregado."
        else:
            message = f"{actualizados} pedidos fueron marcados como entregados."
        self.message_user(request, message)
    marcar_como_entregado.short_description = "Marcar como entregado"

    def cancelar_pedidos(self, request, queryset):
        """Cancela los pedidos seleccionados que puedan cancelarse"""
        actualizados = 0
        for pedido in queryset:
            if pedido.cancelar_pedido():
                actualizados += 1
        
        if actualizados == 1:
            message = "1 pedido fue cancelado."
        else:
            message = f"{actualizados} pedidos fueron cancelados."
        self.message_user(request, message)
    cancelar_pedidos.short_description = "Cancelar pedidos seleccionados"


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'producto', 'cantidad', 'precio_unitario', 'total')
    list_filter = ('pedido__estado', 'producto__categoria', 'producto__marca')
    search_fields = ('pedido__numero_pedido', 'producto__nombre')
    ordering = ('-pedido__fecha_creacion',)
    readonly_fields = ('total',)

    fieldsets = (
        ('Información del Item', {
            'fields': ('pedido', 'producto')
        }),
        ('Detalles', {
            'fields': ('cantidad', 'precio_unitario', 'total')
        }),
    )