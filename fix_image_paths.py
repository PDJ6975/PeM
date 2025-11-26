"""
Script para corregir las rutas de imágenes en la base de datos.
Ejecutar en producción: python fix_image_paths.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PeM.settings')
django.setup()

from core.models import Producto

productos = Producto.objects.all()
actualizados = 0

for producto in productos:
    if producto.imagen and producto.imagen.name:
        ruta_original = producto.imagen.name
        
        # Si la ruta tiene ../media/productos/, quitarlo
        if '../media/productos/' in ruta_original:
            nueva_ruta = ruta_original.replace('../media/productos/', 'productos/')
            producto.imagen.name = nueva_ruta
            producto.save()
            print(f"✅ {producto.nombre}: {ruta_original} -> {nueva_ruta}")
            actualizados += 1
        
        # Si la ruta tiene ../media/, quitarlo
        elif '../media/' in ruta_original:
            nueva_ruta = ruta_original.replace('../media/', '')
            producto.imagen.name = nueva_ruta
            producto.save()
            print(f"✅ {producto.nombre}: {ruta_original} -> {nueva_ruta}")
            actualizados += 1
        
        else:
            print(f"⏭️  {producto.nombre}: {ruta_original} (ya correcto)")

print(f"\n✨ Actualizados: {actualizados} productos")
