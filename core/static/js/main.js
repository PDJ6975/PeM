/**
 * Script principal de PeM
 * Funcionalidades generales y utilidades compartidas
 */

// ============================================
// Inicialización
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('PeM - Sistema inicializado correctamente');

    // Aquí se pueden agregar inicializaciones globales
    // Ejemplo: tooltips, popovers, etc.
    inicializarBootstrapComponents();
});


// ============================================
// Componentes de Bootstrap
// ============================================

/**
 * Inicializa componentes de Bootstrap que lo requieran
 */
function inicializarBootstrapComponents() {
    // Inicializar tooltips si existen
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Inicializar popovers si existen
    const popoverTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="popover"]')
    );
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}


// ============================================
// Utilidades Globales
// ============================================

/**
 * Formatea un precio como moneda EUR
 */
function formatearPrecio(precio) {
    return new Intl.NumberFormat('es-ES', {
        style: 'currency',
        currency: 'EUR'
    }).format(precio);
}

/**
 * Muestra un toast de Bootstrap
 */
function mostrarToast(mensaje, tipo = 'info') {
    // TODO: Implementar sistema de toasts
    console.log(`[${tipo}] ${mensaje}`);
}

/**
 * Obtiene el token CSRF de Django
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Obtiene el token CSRF para peticiones
 */
function getCSRFToken() {
    return getCookie('csrftoken');
}


// ============================================
// API Pública
// ============================================

window.PeM = {
    formatearPrecio,
    mostrarToast,
    getCSRFToken,
};
