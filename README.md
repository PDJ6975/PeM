\# PeM - Plataforma eCommerce de Juguetes para Mascotas



Proyecto desarrollado dentro de la asignatura \*\*Proceso Software y Gestión II\*\* (Universidad de Sevilla).  

El objetivo es diseñar, planificar y desarrollar una \*\*plataforma eCommerce B2C\*\* utilizando un \*\*ciclo de vida híbrido\*\*.



\## Descripción



PeM es una aplicación web que permite comprar juguetes para mascotas de forma rápida y sencilla.  

Incluye gestión de productos, pedidos y clientes, así como funciones básicas de administración.



\## Tecnologías



\- Python 3.12  

\- Django  

\- HTML, CSS, Bootstrap y JavaScript  

\- SQLite (desarrollo) / PostgreSQL (producción)  

\- Visual Studio Code  

\- Git y GitHub



\## Funcionalidades principales



\- Catálogo de productos con categorías.  

\- Cesta de compra siempre visible y editable.  

\- Compra en un máximo de tres pasos sin registro obligatorio.  

\- Registro e inicio de sesión mediante correo y contraseña.  

\- Seguimiento de pedidos.  

\- Notificación por correo al finalizar una compra.  

\- Panel de administración con control de stock y pedidos.  

\- Interfaz completamente en español.



\## Instalación local



```bash

git clone https://github.com/<usuario>/pem-ecommerce.git

cd pem-ecommerce

python -m venv .venv

source .venv/bin/activate  # En Windows: .venv\\Scripts\\activate

pip install -r requirements.txt

python manage.py migrate

python manage.py runserver



