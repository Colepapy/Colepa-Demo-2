/**
 * COLEPA - JavaScript Sincronizado con Backend Mejorado
 * Sistema Legal de Paraguay con respuestas estructuradas
 */

// === CONFIGURACIÓN ===
const CONFIG = {
    API_BASE_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000' 
        : 'https://colepa-demo-2-production.up.railway.app',
    ENDPOINT_CONSULTA: '/api/consulta',
    ENDPOINT_HEALTH: '/api/health',
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
    elementos = {
        messagesContainer: document.getElementById('messagesContainer'),
        welcomeMessage: document.getElementById('welcomeMessage'),
        chatHistory: document.getElementById('chatHistory'),
        messageForm: document.getElementById('messageForm'),
        messageInput: document.getElementById('messageInput'),
        sendBtn: document.getElementById('sendBtn'),
        loadingOverlay: document.getElementById('loadingOverlay')
    };

    cargarHistorial();
    renderizarHistorial();
    configurarEventos();
    
    if (elementos.messageInput) {
        elementos.messageInput.focus();
    }

    verificarConexionAPI();
    console.log('🚀 COLEPA inicializado correctamente');
}

function configurarEventos() {
    if (elementos.messageInput) {
        elementos.messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
            actualizarBotonEnvio();
        });
    }
}

// === VERIFICACIÓN DE CONEXIÓN ===
async function verificarConexionAPI() {
    try {
        const response = await fetch(CONFIG.API_BASE_URL + CONFIG.ENDPOINT_HEALTH, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Conexión con API exitosa:', data);
        }
    } catch (error) {
        console.error('❌ Error conectando con API:', error);
        mostrarMensajeConexion(false);
    }
}

function mostrarMensajeConexion(exito) {
    if (!exito) {
        const mensajeConexion = document.createElement('div');
        mensajeConexion.className = 'connection-warning';
        mensajeConexion.style.cssText = `
            position: fixed; top: 20px; right: 20px; background: var(--primary-red);
            color: white; padding: 12px 16px; border-radius: 8px; display: flex;
            align-items: center; gap: 8px; font-size: 14px; box-shadow: var(--shadow-md);
            z-index: 1000; animation: slideIn 0.3s ease;
        `;
        mensajeConexion.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <span>Problema de conexión con el servidor. Intentando reconectar...</span>
        `;
        document.body.appendChild(mensajeConexion);
        setTimeout(() => mensajeConexion.remove(), 5000);
    }
}

// === FUNCIONES DE MENSAJES ===
function enviarMensaje(event) {
    event.preventDefault();
    
    if (app.isLoading) return;
    
    const mensaje = elementos.messageInput.value.trim();
    if (!mensaje) return;
    
    if (mensaje.length > CONFIG.MAX_MESSAGE_LENGTH) {
        alert(`El mensaje es demasiado largo. Máximo ${CONFIG.MAX_MESSAGE_LENGTH} caracteres.`);
        return;
    }
    
    if (!app.sesionId) {
        nuevaConsulta();
    }
    
    agregarMensaje('user', mensaje);
    
    elementos.messageInput.value = '';
    elementos.messageInput.style.height = 'auto';
    actualizarBotonEnvio();
    
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
    
    mostrarIndicadorEscritura();
    
    try {
        const url = CONFIG.API_BASE_URL + CONFIG.ENDPOINT_CONSULTA;
        
        const requestData = {
            historial: app.conversacionActual.map(msg => ({
                role: msg.role === 'user' ? 'user' : 'assistant',
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
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            let errorMessage = `Error ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                if (errorData.detalle) {
                    errorMessage += `\nDetalle: ${errorData.detalle}`;
                }
            } catch (e) {
                console.error('❌ No se pudo parsear error JSON');
            }
            throw new Error(errorMessage);
        }
        
        const data = await response.json();
        console.log('✅ Datos recibidos:', data);
        
        ocultarIndicadorEscritura();
        
        // NUEVA LÓGICA: Efecto de escritura híbrido
        await mostrarRespuestaConEscritura(data);
        
    } catch (error) {
        console.error('❌ Error completo:', error);
        ocultarIndicadorEscritura();
        
        let mensajeError = '🚨 **Error al procesar consulta**\n\n';
        
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            mensajeError += 'No se pudo conectar con el servidor COLEPA. Verifica tu conexión a internet.';
        } else if (error.message.includes('404')) {
            mensajeError += 'El servicio de consultas no está disponible en este momento.';
        } else if (error.message.includes('500')) {
            mensajeError += 'Error interno del servidor. El sistema está procesando tu consulta o experimentando dificultades técnicas.';
        } else {
            mensajeError += `Error: ${error.message}`;
        }
        
        mensajeError += '\n\n💡 **Sugerencias:**\n- Intenta reformular tu pregunta\n- Verifica tu conexión a internet\n- Contacta con soporte si el problema persiste';
        
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
        recomendaciones: data.recomendaciones,
        clasificacion: data.clasificacion,
        tiempo_procesamiento: data.tiempo_procesamiento
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

// === NUEVA FUNCIÓN: DETECCIÓN DE EMERGENCIAS ===
function detectarEmergencia(contenido) {
    const palabrasEmergencia = [
        'línea 137', '137', 'violencia', 'maltrato', 'agresión', 
        'golpes', 'pega', 'abuso', 'emergencia', 'inmediatamente',
        'urgente', 'peligro', 'amenaza'
    ];
    
    const contenidoLower = contenido.toLowerCase();
    return palabrasEmergencia.some(palabra => contenidoLower.includes(palabra));
}

// === FUNCIONES DE RENDERIZADO MEJORADAS ===
function renderizarMensajes() {
    if (!elementos.messagesContainer) return;
    
    if (app.conversacionActual.length === 0) {
        elementos.welcomeMessage.style.display = 'flex';
        return;
    } else {
        elementos.welcomeMessage.style.display = 'none';
    }
    
    const mensajesExistentes = elementos.messagesContainer.querySelectorAll('.message, .typing-indicator');
    mensajesExistentes.forEach(el => el.remove());
    
    app.conversacionActual.forEach(mensaje => {
        const elementoMensaje = crearElementoMensaje(mensaje);
        elementos.messagesContainer.appendChild(elementoMensaje);
    });
}

// === FUNCIÓN MEJORADA: CREAR ELEMENTO MENSAJE ===
function crearElementoMensaje(mensaje) {
    const div = document.createElement('div');
    div.className = `message ${mensaje.role}`;
    
    // NUEVA LÓGICA: Formateo estructurado
    let contenidoHTML = formatearContenido(mensaje.content);
    
    if (mensaje.metadata && mensaje.metadata.fuente) {
        contenidoHTML += crearFuenteLegal(mensaje.metadata.fuente);
    }
    
    if (mensaje.metadata && mensaje.metadata.recomendaciones) {
        contenidoHTML += crearRecomendaciones(mensaje.metadata.recomendaciones);
    }
    
    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';
    
    if (mensaje.role === 'user') {
        wrapper.innerHTML = `
            <div class="message-text">${contenidoHTML}</div>
            <div class="message-avatar">
                <i class="fas fa-user"></i>
            </div>
        `;
    } else {
        wrapper.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-balance-scale"></i>
            </div>
            <div class="message-text">${contenidoHTML}</div>
        `;
    }
    
    div.appendChild(wrapper);
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
                ${fuente.titulo ? `<br><em>${fuente.titulo}</em>` : ''}
            </div>
        </div>
    `;
}

function crearRecomendaciones(recomendaciones) {
    if (!recomendaciones || !Array.isArray(recomendaciones)) return '';
    
    const items = recomendaciones.map(rec => `<li>${rec}</li>`).join('');
    
    return `
        <div class="classification-info">
            <div class="classification-header">
                <i class="fas fa-lightbulb"></i>
                <span>Recomendaciones</span>
            </div>
            <ul style="margin-top: 8px; padding-left: 20px;">
                ${items}
            </ul>
        </div>
    `;
}

// === GESTIÓN DE HISTORIAL (SIN CAMBIOS) ===
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
        elementos.chatHistory.innerHTML = '<div class="empty-history">No hay conversaciones</div>';
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
    event.stopPropagation();
    
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
    
    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';
    wrapper.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-balance-scale"></i>
        </div>
        <div class="typing-dots">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    
    indicador.appendChild(wrapper);
    elementos.messagesContainer.appendChild(indicador);
    scrollToBottom();
}

function ocultarIndicadorEscritura() {
    const indicador = document.getElementById('typingIndicator');
    if (indicador) {
        indicador.remove();
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

// === INICIALIZACIÓN AUTOMÁTICA ===
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        if (app.conversaciones.length === 0) {
            nuevaConsulta();
        }
    }, 100);
});
