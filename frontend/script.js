/**
 * COLEPA - Sistema Legal Oficial de Paraguay
 * Frontend JavaScript - Versión Compacta
 */

// === CONFIGURACIÓN GLOBAL ===
const CONFIG = {
    // URL de la API (tu Railway)
    API_BASE_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000' 
        : 'https://colepa-demo-2-production.up.railway.app',
    
    // Límites
    MAX_MESSAGE_LENGTH: 2000,
    MAX_HISTORY_ITEMS: 20,
    
    // Endpoints
    ENDPOINTS: {
        CONSULTA: '/api/consulta',
        HEALTH: '/api/health'
    }
};

// === ESTADO DE LA APLICACIÓN ===
class AppState {
    constructor() {
        this.conversacionActual = [];
        this.historialSesiones = this.cargarHistorial();
        this.sesionActualId = null;
        this.estaCargando = false;
        this.sistemaOnline = true;
    }

    cargarHistorial() {
        try {
            const historial = localStorage.getItem('colepa_historial');
            return historial ? JSON.parse(historial) : [];
        } catch (error) {
            console.error('Error cargando historial:', error);
            return [];
        }
    }

    guardarHistorial() {
        try {
            localStorage.setItem('colepa_historial', JSON.stringify(this.historialSesiones));
        } catch (error) {
            console.error('Error guardando historial:', error);
        }
    }

    crearNuevaSesion() {
        this.sesionActualId = 'sesion_' + Date.now();
        this.conversacionActual = [];
        
        const nuevaSesion = {
            id: this.sesionActualId,
            titulo: 'Nueva Consulta',
            mensajes: [],
            fechaCreacion: new Date().toISOString()
        };
        
        this.historialSesiones.unshift(nuevaSesion);
        this.guardarHistorial();
        return this.sesionActualId;
    }

    agregarMensaje(role, content) {
        const mensaje = {
            role,
            content,
            timestamp: new Date().toISOString()
        };
        
        this.conversacionActual.push(mensaje);
        this.actualizarSesionActual();
        return mensaje;
    }

    actualizarSesionActual() {
        if (!this.sesionActualId) return;
        
        const sesion = this.historialSesiones.find(s => s.id === this.sesionActualId);
        if (sesion) {
            sesion.mensajes = [...this.conversacionActual];
            
            // Actualizar título
            const primerMensaje = this.conversacionActual.find(m => m.role === 'user');
            if (primerMensaje && sesion.titulo === 'Nueva Consulta') {
                sesion.titulo = primerMensaje.content.substring(0, 50) + '...';
            }
            
            this.guardarHistorial();
        }
    }
}

// === INSTANCIA GLOBAL ===
const app = new AppState();

// === ELEMENTOS DEL DOM ===
let elementos = {};

// === INICIALIZACIÓN ===
document.addEventListener('DOMContentLoaded', function() {
    inicializarElementos();
    inicializarEventListeners();
    iniciarNuevaConsulta();
    verificarEstadoSistema();
});

function inicializarElementos() {
    elementos = {
        chatMessages: document.getElementById('chatMessages'),
        chatHistory: document.getElementById('chatHistory'),
        chatForm: document.getElementById('chatForm'),
        chatInput: document.getElementById('chatInput'),
        sendButton: document.getElementById('sendButton'),
        charCounter: document.getElementById('charCounter'),
        newChatBtn: document.getElementById('newChatBtn'),
        sidebar: document.getElementById('sidebar'),
        sidebarToggle: document.getElementById('sidebarToggle'),
        loadingOverlay: document.getElementById('loadingOverlay'),
        toastContainer: document.getElementById('toastContainer'),
        modalOverlay: document.getElementById('modalOverlay'),
        systemStatus: document.getElementById('systemStatus'),
        currentChatTitle: document.getElementById('currentChatTitle')
    };
}

function inicializarEventListeners() {
    elementos.chatForm.addEventListener('submit', manejarEnvioMensaje);
    elementos.chatInput.addEventListener('input', manejarInputChange);
    elementos.chatInput.addEventListener('keydown', manejarTeclasInput);
    elementos.newChatBtn.addEventListener('click', iniciarNuevaConsulta);
    
    if (elementos.sidebarToggle) {
        elementos.sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    // Auto-redimensionar textarea
    elementos.chatInput.addEventListener('input', autoRedimensionarTextarea);
}

// === GESTIÓN DE MENSAJES ===
async function manejarEnvioMensaje(event) {
    event.preventDefault();
    
    if (app.estaCargando) return;
    
    const mensaje = elementos.chatInput.value.trim();
    if (!mensaje) return;
    
    if (mensaje.length > CONFIG.MAX_MESSAGE_LENGTH) {
        mostrarToast('El mensaje es demasiado largo', 'error');
        return;
    }
    
    // Si no hay sesión, crear una nueva
    if (!app.sesionActualId) {
        app.crearNuevaSesion();
    }
    
    // Agregar mensaje del usuario
    app.agregarMensaje('user', mensaje);
    renderizarMensajes();
    
    // Limpiar input
    elementos.chatInput.value = '';
    actualizarContadorCaracteres();
    autoRedimensionarTextarea();
    actualizarEstadoBotonEnvio();
    
    // Procesar consulta
    await procesarConsulta();
}

async function procesarConsulta() {
    app.estaCargando = true;
    actualizarEstadoBotonEnvio();
    mostrarIndicadorCarga();
    
    try {
        const response = await enviarConsultaAPI();
        
        if (response && response.respuesta) {
            // Agregar respuesta del bot
            app.agregarMensaje('assistant', response.respuesta);
            renderizarMensajes();
            renderizarHistorial();
        } else {
            throw new Error('Respuesta vacía del servidor');
        }
        
    } catch (error) {
        console.error('Error procesando consulta:', error);
        
        let mensajeError = 'Lo siento, ha ocurrido un error procesando su consulta.';
        if (!navigator.onLine) {
            mensajeError = 'Sin conexión a internet. Verifique su conexión.';
        }
        
        app.agregarMensaje('assistant', mensajeError);
        renderizarMensajes();
        mostrarToast('Error procesando consulta', 'error');
        
    } finally {
        ocultarIndicadorCarga();
        app.estaCargando = false;
        actualizarEstadoBotonEnvio();
        elementos.chatInput.focus();
    }
}

async function enviarConsultaAPI() {
    const url = CONFIG.API_BASE_URL + CONFIG.ENDPOINTS.CONSULTA;
    
    const payload = {
        historial: app.conversacionActual.map(msg => ({
            role: msg.role === 'assistant' ? 'assistant' : msg.role,
            content: msg.content,
            timestamp: msg.timestamp
        }))
    };
    
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
        throw new Error(`Error del servidor: ${response.status}`);
    }
    
    return await response.json();
}

// === RENDERIZADO ===
function renderizarMensajes() {
    if (app.conversacionActual.length === 0) {
        mostrarMensajeBienvenida();
        return;
    }
    
    elementos.chatMessages.innerHTML = '';
    
    app.conversacionActual.forEach((mensaje, index) => {
        const elementoMensaje = crearElementoMensaje(mensaje);
        elementos.chatMessages.appendChild(elementoMensaje);
    });
    
    scrollToBottom();
}

function crearElementoMensaje(mensaje) {
    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${mensaje.role}`;
    
    const esUsuario = mensaje.role === 'user';
    const nombreSender = esUsuario ? 'Usted' : 'COLEPA';
    const iconoAvatar = esUsuario ? 'fa-user' : 'fa-balance-scale';
    const claseAvatar = esUsuario ? 'user-avatar' : 'bot-avatar';
    
    const contenidoHTML = formatearContenido(mensaje.content);
    const badgeOficial = !esUsuario ? '<span class="message-badge official">OFICIAL</span>' : '';
    
    wrapper.innerHTML = `
        <div class="message ${mensaje.role}">
            <div class="message-avatar">
                <div class="avatar ${claseAvatar}">
                    <i class="fas ${iconoAvatar}"></i>
                </div>
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="sender-name">${nombreSender}</span>
                    ${badgeOficial}
                    <span class="message-time">${formatearTiempo(mensaje.timestamp)}</span>
                </div>
                <div class="message-text">
                    ${contenidoHTML}
                </div>
            </div>
        </div>
    `;
    
    return wrapper;
}

function formatearContenido(contenido) {
    return contenido
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

function mostrarMensajeBienvenida() {
    elementos.chatMessages.innerHTML = `
        <div class="message-wrapper welcome-message">
            <div class="message system">
                <div class="message-avatar">
                    <div class="avatar bot-avatar">
                        <i class="fas fa-balance-scale"></i>
                    </div>
                </div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="sender-name">COLEPA</span>
                        <span class="message-badge official">OFICIAL</span>
                    </div>
                    <div class="message-text">
                        <h3>¡Bienvenido al Sistema COLEPA!</h3>
                        <p>Soy su asistente legal oficial especializado en la legislación paraguaya. Estoy aquí para ayudarle con consultas sobre:</p>
                        
                        <div class="legal-codes-grid">
                            <div class="code-item">
                                <i class="fas fa-gavel"></i>
                                <span>Código Civil</span>
                            </div>
                            <div class="code-item">
                                <i class="fas fa-handcuffs"></i>
                                <span>Código Penal</span>
                            </div>
                            <div class="code-item">
                                <i class="fas fa-briefcase"></i>
                                <span>Código Laboral</span>
                            </div>
                            <div class="code-item">
                                <i class="fas fa-child"></i>
                                <span>Código de la Niñez</span>
                            </div>
                            <div class="code-item">
                                <i class="fas fa-vote-yea"></i>
                                <span>Código Electoral</span>
                            </div>
                            <div class="code-item">
                                <i class="fas fa-truck"></i>
                                <span>Código Aduanero</span>
                            </div>
                        </div>

                        <div class="welcome-examples">
                            <h4>Ejemplos de consultas:</h4>
                            <div class="example-queries">
                                <button class="example-btn" onclick="enviarEjemplo('¿Qué dice el artículo 22 del Código Civil?')">
                                    "¿Qué dice el artículo 22 del Código Civil?"
                                </button>
                                <button class="example-btn" onclick="enviarEjemplo('Mi empleador no me paga las horas extras, ¿qué puedo hacer?')">
                                    "Mi empleador no me paga las horas extras, ¿qué puedo hacer?"
                                </button>
                                <button class="example-btn" onclick="enviarEjemplo('¿Cuáles son las consecuencias legales del robo en Paraguay?')">
                                    "¿Cuáles son las consecuencias legales del robo en Paraguay?"
                                </button>
                            </div>
                        </div>

                        <p class="help-text">
                            <i class="fas fa-lightbulb"></i>
                            <strong>Tip:</strong> Sea específico en su consulta para obtener información más precisa.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderizarHistorial() {
    if (!elementos.chatHistory) return;
    
    elementos.chatHistory.innerHTML = '';
    
    if (app.historialSesiones.length === 0) {
        elementos.chatHistory.innerHTML = '<div style="padding: 1rem; text-align: center; opacity: 0.7;">No hay consultas anteriores</div>';
        return;
    }
    
    app.historialSesiones.slice(0, 10).forEach(sesion => {
        const item = document.createElement('div');
        item.className = 'history-item';
        if (sesion.id === app.sesionActualId) {
            item.classList.add('active');
        }
        
        item.innerHTML = `
            <div onclick="cargarSesion('${sesion.id}')">${sesion.titulo}</div>
        `;
        
        elementos.chatHistory.appendChild(item);
    });
}

// === GESTIÓN DE EVENTOS ===
function manejarInputChange() {
    actualizarContadorCaracteres();
    actualizarEstadoBotonEnvio();
}

function actualizarContadorCaracteres() {
    const longitud = elementos.chatInput.value.length;
    elementos.charCounter.textContent = `${longitud}/${CONFIG.MAX_MESSAGE_LENGTH}`;
    
    elementos.charCounter.className = 'char-counter';
    if (longitud > CONFIG.MAX_MESSAGE_LENGTH * 0.9) {
        elementos.charCounter.classList.add('warning');
    }
}

function actualizarEstadoBotonEnvio() {
    const tieneContenido = elementos.chatInput.value.trim().length > 0;
    const noExcedeLimite = elementos.chatInput.value.length <= CONFIG.MAX_MESSAGE_LENGTH;
    const puedeEnviar = tieneContenido && noExcedeLimite && !app.estaCargando;
    
    elementos.sendButton.disabled = !puedeEnviar;
}

function manejarTeclasInput(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        elementos.chatForm.dispatchEvent(new Event('submit'));
    }
}

function autoRedimensionarTextarea() {
    elementos.chatInput.style.height = 'auto';
    const nuevaAltura = Math.min(elementos.chatInput.scrollHeight, 120);
    elementos.chatInput.style.height = nuevaAltura + 'px';
}

// === FUNCIONES DE UTILIDAD ===
function scrollToBottom() {
    requestAnimationFrame(() => {
        elementos.chatMessages.scrollTop = elementos.chatMessages.scrollHeight;
    });
}

function formatearTiempo(timestamp) {
    const fecha = new Date(timestamp);
    const ahora = new Date();
    const diff = ahora - fecha;
    
    const minutos = Math.floor(diff / (1000 * 60));
    const horas = Math.floor(diff / (1000 * 60 * 60));
    
    if (minutos < 1) return 'Ahora';
    if (minutos < 60) return `${minutos}m`;
    if (horas < 24) return `${horas}h`;
    
    return fecha.toLocaleDateString('es-PY', { 
        day: 'numeric', 
        month: 'short' 
    });
}

// === INDICADORES VISUALES ===
function mostrarIndicadorCarga() {
    if (elementos.loadingOverlay) {
        elementos.loadingOverlay.classList.add('active');
    }
}

function ocultarIndicadorCarga() {
    if (elementos.loadingOverlay) {
        elementos.loadingOverlay.classList.remove('active');
    }
}

// === ESTADO DEL SISTEMA ===
async function verificarEstadoSistema() {
    try {
        const response = await fetch(CONFIG.API_BASE_URL + CONFIG.ENDPOINTS.HEALTH);
        app.sistemaOnline = response.ok;
    } catch (error) {
        app.sistemaOnline = false;
    }
    
    actualizarEstadoSistema();
}

function actualizarEstadoSistema() {
    if (!elementos.systemStatus) return;
    
    const indicador = elementos.systemStatus.querySelector('.status-indicator');
    const texto = elementos.systemStatus.querySelector('.status-text');
    
    if (app.sistemaOnline) {
        indicador.style.color = '#10b981';
        texto.textContent = 'Sistema Operativo';
    } else {
        indicador.style.color = '#ef4444';
        texto.textContent = 'Sistema Fuera de Línea';
    }
}

// === NOTIFICACIONES ===
function mostrarToast(mensaje, tipo = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;
    
    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <i class="fas fa-info-circle"></i>
            <span>${mensaje}</span>
        </div>
    `;
    
    elementos.toastContainer.appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 5000);
}

// === FUNCIONES PÚBLICAS ===
window.iniciarNuevaConsulta = function() {
    app.crearNuevaSesion();
    renderizarMensajes();
    renderizarHistorial();
    elementos.chatInput.focus();
    
    if (elementos.currentChatTitle) {
        elementos.currentChatTitle.textContent = 'Nueva Consulta Legal';
    }
};

window.cargarSesion = function(sesionId) {
    const sesion = app.historialSesiones.find(s => s.id === sesionId);
    if (sesion) {
        app.sesionActualId = sesionId;
        app.conversacionActual = [...sesion.mensajes];
        renderizarMensajes();
        renderizarHistorial();
        
        if (elementos.currentChatTitle) {
            elementos.currentChatTitle.textContent = sesion.titulo;
        }
    }
};

window.enviarEjemplo = function(texto) {
    elementos.chatInput.value = texto;
    manejarInputChange();
    autoRedimensionarTextarea();
    elementos.chatInput.focus();
};

window.toggleSidebar = function() {
    if (elementos.sidebar) {
        elementos.sidebar.classList.toggle('open');
    }
};

window.limpiarChat = function() {
    if (confirm('¿Está seguro de que desea limpiar la conversación actual?')) {
        iniciarNuevaConsulta();
        mostrarToast('Conversación limpiada', 'success');
    }
};

window.exportarConsulta = function() {
    if (app.conversacionActual.length === 0) {
        mostrarToast('No hay conversación para exportar', 'warning');
        return;
    }
    
    elementos.modalOverlay.classList.add('active');
};

window.cerrarModal = function() {
    elementos.modalOverlay.classList.remove('active');
};

window.exportar = function(formato) {
    if (app.conversacionActual.length === 0) return;
    
    const sesion = app.historialSesiones.find(s => s.id === app.sesionActualId);
    const titulo = sesion ? sesion.titulo : 'Consulta Legal';
    const fecha = new Date().toLocaleDateString('es-PY');
    
    let contenido = `COLEPA - Consulta Legal\n`;
    contenido += `Título: ${titulo}\n`;
    contenido += `Fecha: ${fecha}\n`;
    contenido += `${'='.repeat(50)}\n\n`;
    
    app.conversacionActual.forEach((mensaje) => {
        const rol = mensaje.role === 'user' ? 'USUARIO' : 'COLEPA';
        contenido += `[${rol}]\n${mensaje.content}\n\n`;
    });
    
    const blob = new Blob([contenido], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `colepa_${titulo.replace(/[^a-zA-Z0-9]/g, '_')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    cerrarModal();
    mostrarToast('Consulta exportada exitosamente', 'success');
};

// Inicializar cuando se carga la página
iniciarNuevaConsulta();
