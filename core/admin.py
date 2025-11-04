from django.contrib import admin
from .models import Cliente
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