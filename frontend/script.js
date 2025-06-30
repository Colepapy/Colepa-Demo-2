/**
 * COLEPA - JavaScript Minimalista
 * Sistema Legal de Paraguay - Versión ChatGPT
 */

// === CONFIGURACIÓN ===
const CONFIG = {
    API_BASE_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000' 
        : 'https://colepa-demo-2-production.up.railway.app',
    MAX_MESSAGE_LENGTH: 2000,
    TYPING_SPEED: 30
};

// === ESTADO GLOBAL ===
let app = {
    conversaciones: [],
    conversacionActual: [],
    sesionId: null,
    isLoading: false
};

// === ELEMENTOS DOM ===
let elementos = {};

// === INICIALIZACIÓN ===
document.addEventListener('DOMContentLoaded', function() {
    inicializar();
});

function inicializar() {
    // Obtener elementos
    elementos = {
        messagesContainer: document.getElementById('messagesContainer'),
        welcomeMessage: document.getElementById('welcomeMessage'),
        chatHistory: document.getElementById('chatHistory'),
        messageForm: document.getElementById('messageForm'),
        messageInput: document.getElementById('messageInput'),
        sendBtn: document.getElementById('sendBtn'),
        loadingOverlay: document.getElementById('loadingOverlay')
    };

    // Cargar historial
    cargarHistorial();
    renderizarHistorial();
    
    // Configurar eventos
    configurarEventos();
    
    // Focus en input
    if (elementos.messageInput) {
        elementos.messageInput.focus();
    }
}

function configurarEventos() {
    // Auto-resize del textarea
    if (elementos.messageInput) {
        elementos.messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
            actualizarBotonEnvio();
        });
    }
}

// === FUNCIONES DE MENSAJES ===
function enviarMensaje(event) {
    event.preventDefault();
    
    if (app.isLoading) return;
    
    const mensaje = elementos.messageInput.value.trim();
    if (!mensaje) return;
    
    // Crear nueva sesión si no existe
    if (!app.sesionId) {
        nuevaConsulta();
    }
    
    // Agregar mensaje del usuario
    agregarMensaje('user', mensaje);
    
    // Limpiar input
    elementos.messageInput.value = '';
    elementos.messageInput.style.height = 'auto';
    actualizarBotonEnvio();
    
    // Procesar respuesta
    procesarRespuesta(mensaje);
}

function agregarMensaje(role, content, metadata = null) {
    const mensaje = {
        id: Date.now(),
        role,
        content,
        timestamp: new Date().toISOString(),
        metadata
    };
    
    app.conversacionActual.push(mensaje);
    actualizarSesionActual();
    renderizarMensajes();
    scrollToBottom();
    
    return mensaje;
}

async function procesarRespuesta(mensajeUsuario) {
    app.isLoading = true;
    actualizarBotonEnvio();
    
    // Mostrar indicador de escritura
    mostrarIndicadorEscritura();
    
    try {
        const response = await fetch(CONFIG.API_BASE_URL + '/api/consulta', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                historial: app.conversacionActual.map(msg => ({
                    role: msg.role === 'user' ? 'user' : 'assistant',
                    content: msg.content,
                    timestamp: msg.timestamp
                }))
            })
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Ocultar indicador de escritura
        ocultarIndicadorEscritura();
        
        // Agregar respuesta con efecto de escritura
        await mostrarRespuestaConEscritura(data);
        
    } catch (error) {
        console.error('Error:', error);
        ocultarIndicadorEscritura();
        
        const mensajeError = `Lo siento, ha ocurrido un error: ${error.message}

Por favor, intenta nuevamente o reformula tu pregunta.`;
        
        agregarMensaje('assistant', mensajeError);
        
    } finally {
        app.isLoading = false;
        actualizarBotonEnvio();
    }
}

async function mostrarRespuestaConEscritura(data) {
    const contenido = data.respuesta || 'Lo siento, no pude generar una respuesta.';
    const metadata = {
        fuente: data.fuente,
        recomendaciones: data.recomendaciones
    };
    
    // Agregar mensaje vacío
    const mensaje = agregarMensaje('assistant', '', metadata);
    const indexMensaje = app.conversacionActual.length - 1;
    
    // Efecto de escritura palabra por palabra
    const palabras = contenido.split(' ');
    let contenidoActual = '';
    
    for (let i = 0; i < palabras.length; i++) {
        if (i > 0) contenidoActual += ' ';
        contenidoActual += palabras[i];
        
        // Actualizar mensaje
        app.conversacionActual[indexMensaje].content = contenidoActual;
        renderizarMensajes();
        scrollToBottom();
        
        // Pausa para efecto de escritura
        await sleep(CONFIG.TYPING_SPEED + Math.random() * 20);
    }
    
    // Contenido final
    app.conversacionActual[indexMensaje].content = contenido;
    actualizarSesionActual();
    renderizarHistorial();
}

// === FUNCIONES DE RENDERIZADO ===
function renderizarMensajes() {
    if (!elementos.messagesContainer) return;
    
    // Mostrar/ocultar mensaje de bienvenida
    if (app.conversacionActual.length === 0) {
        elementos.welcomeMessage.style.display = 'flex';
        return;
    } else {
        elementos.welcomeMessage.style.display = 'none';
    }
    
    // Limpiar mensajes anteriores (excepto bienvenida)
    const mensajesExistentes = elementos.messagesContainer.querySelectorAll('.message, .typing-indicator');
    mensajesExistentes.forEach(el => el.remove());
    
    // Renderizar mensajes
    app.conversacionActual.forEach(mensaje => {
        const elementoMensaje = crearElementoMensaje(mensaje);
        elementos.messagesContainer.appendChild(elementoMensaje);
    });
}

function crearElementoMensaje(mensaje) {
    const div = document.createElement('div');
    div.className = `message ${mensaje.role}`;
    
    let contenidoHTML = formatearContenido(mensaje.content);
    
    // Agregar fuente legal si existe
    if (mensaje.metadata && mensaje.metadata.fuente) {
        contenidoHTML += crearFuenteLegal(mensaje.metadata.fuente);
    }
    
    if (mensaje.role === 'user') {
        div.innerHTML = `
            <div class="message-content">${contenidoHTML}</div>
            <div class="message-avatar">
                <i class="fas fa-user"></i>
            </div>
        `;
    } else {
        div.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-balance-scale"></i>
            </div>
            <div class="message-content">${contenidoHTML}</div>
        `;
    }
    
    return div;
}

function formatearContenido(contenido) {
    return contenido
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

function crearFuenteLegal(fuente) {
    if (!fuente || !fuente.ley) return '';
    
    return `
        <div class="legal-source">
            <div class="source-header">
                <i class="fas fa-book-open"></i>
                <span>Fuente Legal</span>
            </div>
            <div class="source-details">
                <strong>${fuente.ley}</strong>
                ${fuente.articulo_numero ? `, Artículo ${fuente.articulo_numero}` : ''}
            </div>
        </div>
    `;
}

// === GESTIÓN DE HISTORIAL ===
function cargarHistorial() {
    try {
        const historialGuardado = localStorage.getItem('colepa_conversaciones');
        if (historialGuardado) {
            app.conversaciones = JSON.parse(historialGuardado);
        }
    } catch (error) {
        console.error('Error cargando historial:', error);
        app.conversaciones = [];
    }
}

function guardarHistorial() {
    try {
        localStorage.setItem('colepa_conversaciones', JSON.stringify(app.conversaciones));
    } catch (error) {
        console.error('Error guardando historial:', error);
    }
}

function renderizarHistorial() {
    if (!elementos.chatHistory) return;
    
    elementos.chatHistory.innerHTML = '';
    
    if (app.conversaciones.length === 0) {
        elementos.chatHistory.innerHTML = '<div style="padding: 1rem; text-align: center; color: var(--text-secondary); font-size: 0.875rem;">No hay conversaciones</div>';
        return;
    }
    
    app.conversaciones.forEach(conversacion => {
        const div = document.createElement('div');
        div.className = 'chat-item';
        if (conversacion.id === app.sesionId) {
            div.classList.add('active');
        }
        
        div.innerHTML = `
            <div class="chat-title" onclick="cargarConversacion('${conversacion.id}')">${conversacion.titulo}</div>
            <button class="chat-delete" onclick="eliminarConversacion('${conversacion.id}')" title="Eliminar">
                <i class="fas fa-trash"></i>
            </button>
        `;
        
        elementos.chatHistory.appendChild(div);
    });
}

function actualizarSesionActual() {
    if (!app.sesionId || app.conversacionActual.length === 0) return;
    
    let conversacion = app.conversaciones.find(c => c.id === app.sesionId);
    
    if (!conversacion) {
        conversacion = {
            id: app.sesionId,
            titulo: 'Nueva consulta',
            mensajes: [],
            fechaCreacion: new Date().toISOString()
        };
        app.conversaciones.unshift(conversacion);
    }
    
    // Actualizar título basado en primer mensaje
    if (conversacion.titulo === 'Nueva consulta') {
        const primerMensaje = app.conversacionActual.find(m => m.role === 'user');
        if (primerMensaje) {
            conversacion.titulo = primerMensaje.content.substring(0, 50) + 
                                 (primerMensaje.content.length > 50 ? '...' : '');
        }
    }
    
    conversacion.mensajes = [...app.conversacionActual];
    conversacion.ultimaActividad = new Date().toISOString();
    
    guardarHistorial();
}

// === FUNCIONES PÚBLICAS ===
window.nuevaConsulta = function() {
    app.sesionId = 'chat_' + Date.now();
    app.conversacionActual = [];
    renderizarMensajes();
    renderizarHistorial();
    
    if (elementos.messageInput) {
        elementos.messageInput.focus();
    }
};

window.cargarConversacion = function(id) {
    const conversacion = app.conversaciones.find(c => c.id === id);
    if (!conversacion) return;
    
    app.sesionId = id;
    app.conversacionActual = [...conversacion.mensajes];
    renderizarMensajes();
    renderizarHistorial();
    scrollToBottom();
};

window.eliminarConversacion = function(id) {
    if (confirm('¿Eliminar esta conversación?')) {
        app.conversaciones = app.conversaciones.filter(c => c.id !== id);
        
        if (app.sesionId === id) {
            nuevaConsulta();
        }
        
        guardarHistorial();
        renderizarHistorial();
    }
};

// === FUNCIONES DE EVENTOS ===
function manejarTeclas(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (elementos.messageForm) {
            elementos.messageForm.dispatchEvent(new Event('submit'));
        }
    }
}

function manejarInput() {
    actualizarBotonEnvio();
}

function actualizarBotonEnvio() {
    if (!elementos.sendBtn || !elementos.messageInput) return;
    
    const tieneTexto = elementos.messageInput.value.trim().length > 0;
    const puedeEnviar = tieneTexto && !app.isLoading;
    
    elementos.sendBtn.disabled = !puedeEnviar;
}

// === INDICADORES VISUALES ===
function mostrarIndicadorEscritura() {
    if (!elementos.messagesContainer) return;
    
    const indicador = document.createElement('div');
    indicador.className = 'typing-indicator';
    indicador.id = 'typingIndicator';
    indicador.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-balance-scale"></i>
        </div>
        <div class="typing-content">
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    
    elementos.messagesContainer.appendChild(indicador);
    scrollToBottom();
}

function ocultarIndicadorEscritura() {
    const indicador = document.getElementById('typingIndicator');
    if (indicador) {
        indicador.remove();
    }
}

function mostrarLoading() {
    if (elementos.loadingOverlay) {
        elementos.loadingOverlay.classList.add('active');
    }
}

function ocultarLoading() {
    if (elementos.loadingOverlay) {
        elementos.loadingOverlay.classList.remove('active');
    }
}

// === UTILIDADES ===
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function scrollToBottom() {
    if (elementos.messagesContainer) {
        setTimeout(() => {
            elementos.messagesContainer.scrollTop = elementos.messagesContainer.scrollHeight;
        }, 10);
    }
}

// Inicializar nueva consulta al cargar
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        if (app.conversaciones.length === 0) {
            nuevaConsulta();
        }
    }, 100);
});
