from django.db import migrations

def crear_datos_iniciales(apps, schema_editor):
    Marca = apps.get_model('core', 'Marca')
    Categoria = apps.get_model('core', 'Categoria')
    Producto = apps.get_model('core', 'Producto')

    # Crear marcas
    marca_kong, _ = Marca.objects.get_or_create(nombre='Kong')
    marca_pedigree, _ = Marca.objects.get_or_create(nombre='Pedigree')
    marca_royal, _ = Marca.objects.get_or_create(nombre='Royal Canin')
    marca_trixie, _ = Marca.objects.get_or_create(nombre='Trixie')
    marca_natura, _ = Marca.objects.get_or_create(nombre='NaturaPet')

    # Crear categorías
    cat_juguetes, _ = Categoria.objects.get_or_create(nombre='Juguetes')
    cat_comida, _ = Categoria.objects.get_or_create(nombre='Comida')
    cat_accesorios, _ = Categoria.objects.get_or_create(nombre='Accesorios')
    cat_higiene, _ = Categoria.objects.get_or_create(nombre='Higiene')
    cat_descanso, _ = Categoria.objects.get_or_create(nombre='Descanso')

    # Lista de productos iniciales
    productos = [
        # --- Juguetes ---
        dict(nombre='Pelota Kong Classic', descripcion='Pelota resistente para perro', marca=marca_kong, categoria=cat_juguetes, precio=9.99, precio_oferta=7.99, stock=25, es_destacado=True),
        dict(nombre='Hueso Mordedor', descripcion='Hueso de goma duradera', marca=marca_kong, categoria=cat_juguetes, precio=5.50, stock=10),
        dict(nombre='Cuerda de algodón', descripcion='Juguete de cuerda para limpiar dientes', marca=marca_trixie, categoria=cat_juguetes, precio=6.75, stock=30),
        dict(nombre='Pelota con sonido', descripcion='Pelota con sonido interior, ideal para cachorros', marca=marca_trixie, categoria=cat_juguetes, precio=4.99, stock=20),
        dict(nombre='Aro mordedor Kong Flyer', descripcion='Aro volador resistente', marca=marca_kong, categoria=cat_juguetes, precio=12.90, stock=15),

        # --- Comida ---
        dict(nombre='Pienso Pedigree Adulto', descripcion='Pienso completo para perros adultos', marca=marca_pedigree, categoria=cat_comida, precio=24.99, stock=40, es_destacado=True),
        dict(nombre='Pienso Pedigree Cachorro', descripcion='Pienso nutritivo para cachorros', marca=marca_pedigree, categoria=cat_comida, precio=22.99, stock=35),
        dict(nombre='Comida húmeda Royal Canin', descripcion='Comida húmeda para perros pequeños', marca=marca_royal, categoria=cat_comida, precio=15.20, stock=25),
        dict(nombre='Snack de pollo deshidratado', descripcion='Snack natural de pollo para premios', marca=marca_natura, categoria=cat_comida, precio=6.80, stock=50),
        dict(nombre='Barritas dentales Pedigree Dentastix', descripcion='Barritas para la higiene bucal diaria', marca=marca_pedigree, categoria=cat_comida, precio=8.50, stock=60),

        # --- Accesorios ---
        dict(nombre='Correa extensible 5m', descripcion='Correa extensible de nailon resistente', marca=marca_trixie, categoria=cat_accesorios, precio=13.99, stock=18),
        dict(nombre='Arnés ajustable', descripcion='Arnés acolchado para mayor comodidad', marca=marca_trixie, categoria=cat_accesorios, precio=17.50, stock=22),
        dict(nombre='Collar luminoso LED', descripcion='Collar recargable ideal para paseos nocturnos', marca=marca_natura, categoria=cat_accesorios, precio=14.99, stock=15, es_destacado=True),
        dict(nombre='Comedero antideslizante', descripcion='Comedero de acero inoxidable con base antideslizante', marca=marca_trixie, categoria=cat_accesorios, precio=9.20, stock=25),
        dict(nombre='Botella portátil de agua', descripcion='Botella plegable para paseos y viajes', marca=marca_trixie, categoria=cat_accesorios, precio=8.99, stock=30),

        # --- Higiene ---
        dict(nombre='Champú natural para perro', descripcion='Champú con avena y aloe vera', marca=marca_natura, categoria=cat_higiene, precio=11.50, stock=20),
        dict(nombre='Toallitas húmedas Trixie', descripcion='Toallitas para limpieza diaria', marca=marca_trixie, categoria=cat_higiene, precio=5.99, stock=40),
        dict(nombre='Cepillo doble', descripcion='Cepillo para desenredar y dar brillo', marca=marca_trixie, categoria=cat_higiene, precio=7.49, stock=25),

        # --- Descanso ---
        dict(nombre='Cama ovalada acolchada', descripcion='Cama suave con forro extraíble', marca=marca_trixie, categoria=cat_descanso, precio=34.90, stock=10, es_destacado=True),
        dict(nombre='Manta polar', descripcion='Manta polar lavable para mascotas', marca=marca_trixie, categoria=cat_descanso, precio=12.99, stock=25),
    ]

    for datos in productos:
        Producto.objects.get_or_create(
            nombre=datos['nombre'],
            defaults=dict(
                descripcion=datos.get('descripcion', ''),
                marca=datos['marca'],
                categoria=datos['categoria'],
                precio=datos['precio'],
                precio_oferta=datos.get('precio_oferta'),
                stock=datos['stock'],
                esta_disponible=True,
                es_destacado=datos.get('es_destacado', False),
            )
        )

def borrar_datos_iniciales(apps, schema_editor):
    Producto = apps.get_model('core', 'Producto')
    Marca = apps.get_model('core', 'Marca')
    Categoria = apps.get_model('core', 'Categoria')
    Producto.objects.all().delete()
    Marca.objects.all().delete()
    Categoria.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0007_remove_pedido_metodo_pago_and_more'),
    ]

    operations = [
        migrations.RunPython(crear_datos_iniciales, borrar_datos_iniciales),
    ]
