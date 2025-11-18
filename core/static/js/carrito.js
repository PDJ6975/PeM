/**
 * Módulo de gestión del carrito de compras
 * Conecta el frontend con la API REST del carrito
 */

// ============================================
// Configuración y constantes
// ============================================

const API_BASE_URL = '/api/carrito';

const ENDPOINTS = {
    obtener: `${API_BASE_URL}/`,
    agregar: `${API_BASE_URL}/agregar/`,
    modificar: `${API_BASE_URL}/modificar/`,
    eliminar: (producto_id) => `${API_BASE_URL}/eliminar/${producto_id}/`,
    vaciar: `${API_BASE_URL}/vaciar/`,
};


// ============================================
// Utilidades HTTP
// ============================================

/**
 * Realiza una petición HTTP a la API
 */
async function fetchAPI(url, options = {}) {
  try {
    const { headers, ...rest } = options;
    const response = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(headers || {}) },
      ...rest,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.mensaje || 'Error en la petición');
    return data;
  } catch (error) {
    console.error('Error en fetchAPI:', error);
    throw error;
  }
}



// ============================================
// Funciones de la API del Carrito
// ============================================

/**
 * Obtiene el estado actual del carrito
 */
async function obtenerCarrito() {
    return await fetchAPI(ENDPOINTS.obtener);
}

/**
 * Agrega un producto al carrito
 * @param {number} productoId - ID del producto
 * @param {number} cantidad - Cantidad a agregar (default: 1)
 */
async function agregarProducto(productoId, cantidad = 1) {
    return await fetchAPI(ENDPOINTS.agregar, {
        method: 'POST',
        body: JSON.stringify({
            producto_id: productoId,
            cantidad: cantidad,
        }),
    });
}

/**
 * Modifica la cantidad de un producto en el carrito
 * @param {number} productoId - ID del producto
 * @param {number} nuevaCantidad - Nueva cantidad
 */
async function modificarCantidad(productoId, nuevaCantidad) {
    return await fetchAPI(ENDPOINTS.modificar, {
        method: 'PUT',
        body: JSON.stringify({
            producto_id: productoId,
            cantidad: nuevaCantidad,
        }),
    });
}

/**
 * Elimina un producto del carrito
 * @param {number} productoId - ID del producto
 */
async function eliminarProducto(productoId) {
    return await fetchAPI(ENDPOINTS.eliminar(productoId), {
        method: 'DELETE',
    });
}

/**
 * Vacía el carrito completamente
 */
async function vaciarCarrito() {
    return await fetchAPI(ENDPOINTS.vaciar, {
        method: 'DELETE',
    });
}


// ============================================
// Renderizado del Carrito
// ============================================

/**
 * Actualiza la interfaz del carrito con los datos recibidos
 * @param {Object} carritoData - Datos del carrito
 */
function renderizarCarrito(carritoData) {
    const { carrito } = carritoData;

    // Actualizar badge
    actualizarBadge(carrito.total_items);

    // Actualizar total
    actualizarTotal(carrito.subtotal);

    // Actualizar contenido
    actualizarContenido(carrito);
}

/**
 * Actualiza el badge con el número de productos
 */
function actualizarBadge(totalItems) {
    const badge = document.getElementById('carritoBadge');
    if (badge) {
        badge.textContent = totalItems;
        badge.style.display = totalItems > 0 ? 'inline-block' : 'none';
    }
}

/**
 * Actualiza el total del carrito
 */
function actualizarTotal(subtotal) {
    const totalElement = document.getElementById('carritoTotal');
    if (totalElement) {
        totalElement.textContent = formatearPrecio(subtotal);
    }

    // Actualizar también el total en el widget superior
    const totalWidgetElement = document.getElementById('carritoTotalWidget');
    if (totalWidgetElement) {
        totalWidgetElement.textContent = formatearPrecio(subtotal);
    }
}

/**
 * Actualiza el contenido del offcanvas del carrito
 */
function actualizarContenido(carrito) {
    const contenedor = document.getElementById('carritoContenido');

    if (!contenedor) return;

    if (carrito.esta_vacio) {
        contenedor.innerHTML = `
            <div class="text-center py-5 text-muted">
                <i class="bi bi-cart-x display-1"></i>
                <p class="mt-3">Tu carrito está vacío</p>
            </div>
        `;
        return;
    }

    // Renderizar items
    let html = '<div class="list-group list-group-flush">';

    carrito.items.forEach(item => {
        html += crearItemHTML(item);
    });

    html += '</div>';
    contenedor.innerHTML = html;

    // Agregar event listeners a los botones
    agregarEventListeners();
}

/**
 * Genera el HTML para un item del carrito
 */
function crearItemHTML(item) {
    const imagenUrl = item.producto.imagen || '/static/images/placeholder.png';

    return `
        <div class="list-group-item py-3" data-producto-id="${item.producto.id}">
            <div class="row align-items-center">
                <div class="col-3">
                    <img src="${imagenUrl}" alt="${item.producto.nombre}"
                         class="img-fluid rounded" style="max-height: 60px; object-fit: cover;">
                </div>
                <div class="col-6">
                    <h6 class="mb-1">${item.producto.nombre}</h6>
                    <small class="text-muted">${item.producto.marca}</small>
                    <div class="mt-1">
                        <strong>${formatearPrecio(item.producto.precio_unitario)}</strong>
                        ${item.producto.tiene_oferta ? '<span class="badge bg-success ms-1">Oferta</span>' : ''}
                    </div>
                </div>
                <div class="col-3 text-end">
                    <div class="input-group input-group-sm mb-2">
                        <button class="btn btn-outline-secondary btn-cantidad-menos"
                                data-producto-id="${item.producto.id}"
                                data-cantidad="${item.cantidad}">
                            <i class="bi bi-dash"></i>
                        </button>
                        <input type="number"
                               class="form-control text-center input-cantidad"
                               value="${item.cantidad}"
                               min="1"
                               data-producto-id="${item.producto.id}"
                               style="max-width: 50px;">
                        <button class="btn btn-outline-secondary btn-cantidad-mas"
                                data-producto-id="${item.producto.id}"
                                data-cantidad="${item.cantidad}">
                            <i class="bi bi-plus"></i>
                        </button>
                    </div>
                    <small class="d-block text-muted mb-2">
                        Subtotal: ${formatearPrecio(item.subtotal)}
                    </small>
                    <button class="btn btn-sm btn-outline-danger btn-eliminar"
                            data-producto-id="${item.producto.id}">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

/**
 * Formatea un número como precio en euros
 */
function formatearPrecio(precio) {
    return new Intl.NumberFormat('es-ES', {
        style: 'currency',
        currency: 'EUR'
    }).format(precio);
}


// ============================================
// Event Listeners
// ============================================

/**
 * Agrega event listeners a los botones del carrito
 */
function agregarEventListeners() {
    // Botones de incrementar cantidad
    document.querySelectorAll('.btn-cantidad-mas').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const productoId = parseInt(e.currentTarget.dataset.productoId);
            const cantidadActual = parseInt(e.currentTarget.dataset.cantidad);
            await manejarCambioCantidad(productoId, cantidadActual + 1);
        });
    });

    // Botones de decrementar cantidad
    document.querySelectorAll('.btn-cantidad-menos').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const productoId = parseInt(e.currentTarget.dataset.productoId);
            const cantidadActual = parseInt(e.currentTarget.dataset.cantidad);
            if (cantidadActual > 1) {
                await manejarCambioCantidad(productoId, cantidadActual - 1);
            }
        });
    });

    // Inputs de cantidad (cambio manual)
    document.querySelectorAll('.input-cantidad').forEach(input => {
        input.addEventListener('change', async (e) => {
            const productoId = parseInt(e.target.dataset.productoId);
            const nuevaCantidad = parseInt(e.target.value);
            if (nuevaCantidad >= 1) {
                await manejarCambioCantidad(productoId, nuevaCantidad);
            } else {
                e.target.value = 1;
            }
        });
    });

    // Botones de eliminar
    document.querySelectorAll('.btn-eliminar').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const productoId = parseInt(e.currentTarget.dataset.productoId);
            await manejarEliminarProducto(productoId);
        });
    });
}


// ============================================
// Manejadores de eventos
// ============================================

/**
 * Maneja el cambio de cantidad de un producto
 */
async function manejarCambioCantidad(productoId, nuevaCantidad) {
    try {
        mostrarCargando(true);
        const resultado = await modificarCantidad(productoId, nuevaCantidad);
        renderizarCarrito(resultado);
        mostrarMensaje(resultado.mensaje, 'success');
    } catch (error) {
        mostrarMensaje(error.message, 'error');
    } finally {
        mostrarCargando(false);
    }
}

/**
 * Maneja la eliminación de un producto
 */
async function manejarEliminarProducto(productoId) {
    if (!confirm('¿Estás seguro de eliminar este producto del carrito?')) {
        return;
    }

    try {
        mostrarCargando(true);
        const resultado = await eliminarProducto(productoId);
        renderizarCarrito(resultado);
        mostrarMensaje(resultado.mensaje, 'success');
    } catch (error) {
        mostrarMensaje(error.message, 'error');
    } finally {
        mostrarCargando(false);
    }
}

/**
 * Maneja agregar un producto (para usar desde páginas de productos)
 */
async function manejarAgregarProducto(productoId, cantidad = 1) {
    try {
        mostrarCargando(true);
        const resultado = await agregarProducto(productoId, cantidad);
        renderizarCarrito(resultado);
        mostrarMensaje(resultado.mensaje, 'success');

        // Abrir el offcanvas del carrito
        const offcanvas = new bootstrap.Offcanvas(document.getElementById('carritoOffcanvas'));
        offcanvas.show();
    } catch (error) {
        mostrarMensaje(error.message, 'error');
    } finally {
        mostrarCargando(false);
    }
}


// ============================================
// Utilidades UI
// ============================================

/**
 * Muestra/oculta indicador de carga
 */
function mostrarCargando(mostrar) {
    // TODO: Implementar spinner de carga
    console.log('Cargando:', mostrar);
}

/**
 * Muestra un mensaje al usuario
 */
function mostrarMensaje(mensaje, tipo = 'info') {
    // TODO: Implementar sistema de notificaciones
    console.log(`[${tipo.toUpperCase()}] ${mensaje}`);

    // Alternativa simple con alert (temporal)
    if (tipo === 'error') {
        alert(`Error: ${mensaje}`);
    }
}


// ============================================
// Inicialización
// ============================================

/**
 * Inicializa el módulo del carrito
 */
async function inicializarCarrito() {
    try {
        // Cargar estado inicial del carrito
        const resultado = await obtenerCarrito();
        renderizarCarrito(resultado);

        // Configurar eventos del offcanvas
        configurarEventosOffcanvas();

        console.log('Carrito inicializado correctamente');
    } catch (error) {
        console.error('Error al inicializar carrito:', error);
    }
}

/**
 * Configura los eventos del offcanvas para ocultar/mostrar el widget
 */
function configurarEventosOffcanvas() {
    const offcanvasElement = document.getElementById('carritoOffcanvas');
    const widgetElement = document.querySelector('.carrito-widget-top');

    if (offcanvasElement && widgetElement) {
        // Cuando empieza a abrirse el offcanvas, ocultar el widget inmediatamente
        offcanvasElement.addEventListener('show.bs.offcanvas', () => {
            widgetElement.classList.add('hidden');
        });

        // Cuando se cierra el offcanvas, mostrar el widget
        offcanvasElement.addEventListener('hidden.bs.offcanvas', () => {
            widgetElement.classList.remove('hidden');
        });
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', inicializarCarrito);


// ============================================
// API Pública (para usar desde otras páginas)
// ============================================

window.CarritoAPI = {
    agregar: manejarAgregarProducto,
    obtener: obtenerCarrito,
    modificar: manejarCambioCantidad,
    eliminar: manejarEliminarProducto,
    vaciar: vaciarCarrito,
    renderizar: renderizarCarrito,
};
