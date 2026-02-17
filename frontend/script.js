/**
 * COLEPA NASDAQ Edition - Frontend v4.0.0
 * Typewriter optimizado + Fix error 422
 */

// === CONFIGURACIÓN ===
const CONFIG = {
    API_BASE_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000' 
        : 'https://colepa-demo-2-production.up.railway.app',
    ENDPOINT_CONSULTA: '/api/consulta',
    ENDPOINT_HEALTH: '/api/health',
    MAX_MESSAGE_LENGTH: 2000,
    TYPING_SPEED_MIN: 50,
    TYPING_SPEED_MAX: 100
};

// === ESTADO GLOBAL ===
let app = {
    conversaciones: [],
    conversacionActual: [],
    sesionId: null,
    isLoading: false,
    sidebarCollapsed: false
};

// === INICIALIZACIÓN ===
document.addEventListener('DOMContentLoaded', function() {
    inicializar();
});

function inicializar() {
    cargarHistorial();
    renderizarHistorial();
    actualizarBotonEnvio();
    
    const input = document.getElementById('messageInput');
    if (input) input.focus();

    verificarConexionAPI();
    
    const savedCollapsed = localStorage.getItem('colepa_sidebar_collapsed');
    if (savedCollapsed === 'true') {
        toggleSidebarCollapse();
    }

    console.log('🚀 COLEPA NASDAQ v4.0.0 Inicializado');
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
            console.log('✅ API Online:', data);
        } else {
            throw new Error('API no responde');
        }
    } catch (error) {
        console.error('❌ Error de conexión:', error);
        mostrarNotificacion('Sin conexión al servidor legal', 'error');
    }
}

// === SIDEBAR CLAUDE-STYLE ===
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('active');
}

function toggleSidebarCollapse() {
    const sidebar = document.getElementById('sidebar');
    const mainArea = document.getElementById('mainArea');
    const btn = document.querySelector('.collapse-sidebar-btn i');
    
    app.sidebarCollapsed = !app.sidebarCollapsed;
    
    if (app.sidebarCollapsed) {
        sidebar.classList.add('collapsed');
        mainArea.classList.add('sidebar-collapsed');
        if (btn) {
            btn.classList.remove('fa-chevron-left');
            btn.classList.add('fa-chevron-right');
        }
    } else {
        sidebar.classList.remove('collapsed');
        mainArea.classList.remove('sidebar-collapsed');
        if (btn) {
            btn.classList.remove('fa-chevron-right');
            btn.classList.add('fa-chevron-left');
        }
    }
    
    localStorage.setItem('colepa_sidebar_collapsed', app.sidebarCollapsed);
}

// === INPUT HANDLING ===
function manejarTeclas(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        enviarMensaje(event);
    }
}

function manejarInput() {
    const input = document.getElementById('messageInput');
    if (input) {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 200) + 'px';
    }
    actualizarBotonEnvio();
}

function actualizarBotonEnvio() {
    const input = document.getElementById('messageInput');
    const btn = document.getElementById('sendBtn');
    
    if (!input || !btn) return;

    const tieneTexto = input.value.trim().length > 0;
    
    if (tieneTexto && !app.isLoading) {
        btn.disabled = false;
        btn.style.opacity = "1";
        btn.style.cursor = "pointer";
    } else {
        btn.disabled = true;
        btn.style.opacity = "0.5";
        btn.style.cursor = "not-allowed";
    }
}

// === ENVÍO DE MENSAJES ===
function enviarMensaje(event) {
    if (event) event.preventDefault();
    
    if (app.isLoading) {
        console.log('⏳ Ya hay una consulta en proceso');
        return;
    }
    
    const input = document.getElementById('messageInput');
    if (!input) {
        console.error('❌ Input no encontrado');
        return;
    }
    
    const mensaje = input.value.trim();
    if (!mensaje) {
        console.log('⚠️ Mensaje vacío');
        return;
    }
    
    if (mensaje.length > CONFIG.MAX_MESSAGE_LENGTH) {
        mostrarNotificacion(`Máximo ${CONFIG.MAX_MESSAGE_LENGTH} caracteres`, 'warning');
        return;
    }

    console.log('📤 Enviando mensaje:', mensaje);

    if (!app.sesionId) {
        nuevaConsulta();
    }
    
    agregarMensaje('user', mensaje);
    
    input.value = '';
    input.style.height = 'auto';
    actualizarBotonEnvio();
    
    procesarRespuesta(mensaje);
}

function enviarConsultaSugerida(consulta) {
    const input = document.getElementById('messageInput');
    if (input) {
        input.value = consulta;
        actualizarBotonEnvio();
        enviarMensaje(null);
    }
}

// === PROCESAMIENTO CON API ===
async function procesarRespuesta(mensajeUsuario) {
    app.isLoading = true;
    actualizarBotonEnvio();
    mostrarIndicadorEscritura();
    
    const startTime = Date.now();
    
    try {
        const url = CONFIG.API_BASE_URL + CONFIG.ENDPOINT_CONSULTA;
        
        // ✅ CRÍTICO: Enviar SOLO mensajes con contenido (sin vacíos)
        const requestData = {
            historial: app.conversacionActual
                .filter(msg => msg.content && msg.content.trim() !== '')
                .map(msg => ({
                    role: msg.role === 'user' ? 'user' : 'assistant',
                    content: msg.content,
                    timestamp: msg.timestamp
                }))
        };

        console.log('📡 Enviando request a:', url);
        console.log('📦 Historial:', requestData.historial.length, 'mensajes');

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            let errorMessage = `Error ${response.status}`;
            try {
                const errorData = await response.json();
                console.error('❌ Error del backend:', errorData);
                if (errorData.detalle) errorMessage += `: ${errorData.detalle}`;
                if (errorData.detail) errorMessage += `: ${errorData.detail}`;
            } catch (e) {
                console.error('Error parseando error response');
            }
            throw new Error(errorMessage);
        }
        
        const data = await response.json();
        console.log('✅ Respuesta recibida:', data);
        
        ocultarIndicadorEscritura();
        
        const tiempoReal = ((Date.now() - startTime) / 1000).toFixed(2);
        data.tiempo_procesamiento_real = tiempoReal;
        
        await mostrarRespuestaConEscritura(data);
        
    } catch (error) {
        console.error('❌ Error completo:', error);
        ocultarIndicadorEscritura();
        
        let mensajeError = '🚨 **Error procesando consulta**\n\n';
        
        if (error.message.includes('Failed to fetch')) {
            mensajeError += 'No hay conexión con el servidor legal.';
        } else if (error.message.includes('404')) {
            mensajeError += 'Servicio no disponible (404).';
        } else if (error.message.includes('422')) {
            mensajeError += 'Error de validación. Intenta con un nuevo chat.';
        } else if (error.message.includes('500')) {
            mensajeError += 'Error interno del servidor.';
        } else {
            mensajeError += `Error: ${error.message}`;
        }
        
        agregarMensaje('assistant', mensajeError);
        
    } finally {
        app.isLoading = false;
        actualizarBotonEnvio();
        
        setTimeout(() => {
            const input = document.getElementById('messageInput');
            if(input) input.focus();
        }, 100);
    }
}

// === RENDERIZADO VISUAL ===
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

function renderizarMensajes() {
    const container = document.getElementById('messagesContainer');
    const welcome = document.getElementById('welcomeMessage');
    
    if (!container) return;
    
    // ⚡ OPTIMIZACIÓN: Si estamos escribiendo, NO re-renderizar
    if (app.isLoading) {
        if (app.conversacionActual.length > 0 && welcome) {
            welcome.style.display = 'none';
        }
        return;
    }
    
    if (app.conversacionActual.length === 0) {
        if(welcome) welcome.style.display = 'flex';
        Array.from(container.children).forEach(child => {
            if (child.id !== 'welcomeMessage') child.remove();
        });
        return;
    } else {
        if(welcome) welcome.style.display = 'none';
    }
    
    Array.from(container.children).forEach(child => {
        if (child.id !== 'welcomeMessage') child.remove();
    });
    
    app.conversacionActual.forEach(mensaje => {
        const el = crearElementoMensaje(mensaje);
        container.appendChild(el);
    });
}

function crearElementoMensaje(mensaje) {
    const div = document.createElement('div');
    div.className = `message ${mensaje.role}`;
    div.setAttribute('data-message-id', mensaje.id);
    
    let contenidoHTML = formatearContenido(mensaje.content);
    
    if (mensaje.role === 'assistant') {
        contenidoHTML = `
            <div class="message-actions">
                <button class="copy-btn" onclick="copiarMensaje(${mensaje.id})" title="Copiar respuesta">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
            ${contenidoHTML}
        `;
        
        if (mensaje.metadata && mensaje.metadata.fuente && mensaje.metadata.fuente.ley) {
            contenidoHTML += crearFuenteLegal(mensaje.metadata.fuente);
        }
        
        if (mensaje.metadata && mensaje.metadata.tiempo_procesamiento_real) {
            contenidoHTML += `<div class="processing-time"><i class="fas fa-clock"></i> ${mensaje.metadata.tiempo_procesamiento_real}s</div>`;
        }
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';
    
    const iconClass = mensaje.role === 'user' ? 'fa-user' : 'fa-scale-balanced';
    
    wrapper.innerHTML = `
        <div class="message-avatar">
            <i class="fas ${iconClass}"></i>
        </div>
        <div class="message-text">${contenidoHTML}</div>
    `;
    
    div.appendChild(wrapper);
    return div;
}

function formatearContenido(texto) {
    if (!texto) return '';
    return texto
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

function crearFuenteLegal(fuente) {
    if (!fuente || !fuente.ley) return '';
    return `
        <div class="legal-source">
            <div class="source-header">
                <i class="fas fa-book"></i>
                <span>Fuente Legal</span>
            </div>
            <div class="source-content">
                <strong>${fuente.ley}</strong>
                ${fuente.articulo_numero ? ` • Artículo ${fuente.articulo_numero}` : ''}
            </div>
        </div>
    `;
}

// === TYPEWRITER OPTIMIZADO (NO AGREGA AL ESTADO HASTA TERMINAR) ===
async function mostrarRespuestaConEscritura(data) {
    const contenido = data.respuesta || 'No pude generar respuesta.';
    const metadata = {
        fuente: data.fuente,
        recomendaciones: data.recomendaciones,
        tiempo_procesamiento: data.tiempo_procesamiento,
        tiempo_procesamiento_real: data.tiempo_procesamiento_real
    };
    
    // Obtener container y ocultar welcome
    const container = document.getElementById('messagesContainer');
    const welcome = document.getElementById('welcomeMessage');
    if (welcome) welcome.style.display = 'none';
    
    // Crear ID temporal
    const tempId = Date.now();
    
    // Crear elemento DOM manualmente (sin agregar al estado todavía)
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.setAttribute('data-message-id', tempId);
    
    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';
    
    wrapper.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-scale-balanced"></i>
        </div>
        <div class="message-text">
            <div class="message-actions">
                <button class="copy-btn" onclick="copiarMensaje(${tempId})" title="Copiar respuesta">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
        </div>
    `;
    
    div.appendChild(wrapper);
    container.appendChild(div);
    
    const messageTextDiv = div.querySelector('.message-text');
    
    // Botón copiar
    const copyBtn = `
        <div class="message-actions">
            <button class="copy-btn" onclick="copiarMensaje(${tempId})" title="Copiar respuesta">
                <i class="fas fa-copy"></i>
            </button>
        </div>
    `;
    
    // Split por palabras
    const palabras = contenido.split(' ');
    let textoAcumulado = '';
    
    // Typewriter palabra por palabra
    for (let i = 0; i < palabras.length; i++) {
        textoAcumulado += (i > 0 ? ' ' : '') + palabras[i];
        
        // Actualizar SOLO el DOM (no el estado)
        const contenidoHTML = formatearContenido(textoAcumulado);
        messageTextDiv.innerHTML = copyBtn + contenidoHTML;
        
        // Scroll suave cada 5 palabras
        if (i % 5 === 0 || i === palabras.length - 1) {
            container.scrollTop = container.scrollHeight;
        }
        
        // Delay aleatorio tipo Claude
        const delay = Math.random() * (CONFIG.TYPING_SPEED_MAX - CONFIG.TYPING_SPEED_MIN) + CONFIG.TYPING_SPEED_MIN;
        await sleep(delay);
    }
    
    // HTML final con metadata
    let finalHTML = copyBtn + formatearContenido(textoAcumulado);
    
    if (metadata.fuente && metadata.fuente.ley) {
        finalHTML += crearFuenteLegal(metadata.fuente);
    }
    
    if (metadata.tiempo_procesamiento_real) {
        finalHTML += `<div class="processing-time"><i class="fas fa-clock"></i> ${metadata.tiempo_procesamiento_real}s</div>`;
    }
    
    messageTextDiv.innerHTML = finalHTML;
    
    // ✅ AHORA SÍ agregamos al estado (con contenido completo)
    const mensaje = {
        id: tempId,
        role: 'assistant',
        content: textoAcumulado,
        timestamp: new Date().toISOString(),
        metadata
    };
    
    app.conversacionActual.push(mensaje);
    actualizarSesionActual();
}

function mostrarIndicadorEscritura() {
    const container = document.getElementById('messagesContainer');
    if (!container) return;

    ocultarIndicadorEscritura();

    const indicador = document.createElement('div');
    indicador.id = 'typingIndicator';
    indicador.className = 'message assistant';
    
    indicador.innerHTML = `
        <div class="message-content-wrapper">
            <div class="message-avatar loading-paraguay">
                <i class="fas fa-scale-balanced"></i>
            </div>
            <div class="message-text typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    container.appendChild(indicador);
    scrollToBottom();
}

function ocultarIndicadorEscritura() {
    const indicador = document.getElementById('typingIndicator');
    if (indicador) indicador.remove();
}

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    if (container) {
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 50);
    }
}

// === COPIAR MENSAJE ===
function copiarMensaje(messageId) {
    const mensaje = app.conversacionActual.find(m => m.id === messageId);
    if (!mensaje) {
        console.warn('Mensaje no encontrado en estado, intentando copiar del DOM');
        const element = document.querySelector(`[data-message-id="${messageId}"] .message-text`);
        if (element) {
            const texto = element.innerText.replace(/Copiar respuesta/g, '').trim();
            navigator.clipboard.writeText(texto).then(() => {
                mostrarNotificacion('Respuesta copiada', 'success');
            }).catch(err => {
                console.error('Error copiando:', err);
                mostrarNotificacion('Error al copiar', 'error');
            });
        }
        return;
    }
    
    const textoPlano = mensaje.content
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/\*(.*?)\*/g, '$1')
        .replace(/<br>/g, '\n');
    
    navigator.clipboard.writeText(textoPlano).then(() => {
        mostrarNotificacion('Respuesta copiada', 'success');
    }).catch(err => {
        console.error('Error copiando:', err);
        mostrarNotificacion('Error al copiar', 'error');
    });
}

// === NOTIFICACIONES ===
function mostrarNotificacion(mensaje, tipo = 'info') {
    const notif = document.createElement('div');
    notif.className = `notification notification-${tipo}`;
    
    const iconos = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    
    notif.innerHTML = `
        <i class="fas ${iconos[tipo]}"></i>
        <span>${mensaje}</span>
    `;
    
    document.body.appendChild(notif);
    
    setTimeout(() => notif.classList.add('show'), 10);
    setTimeout(() => {
        notif.classList.remove('show');
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

// === HISTORIAL (LOCAL STORAGE) ===
function cargarHistorial() {
    try {
        const saved = localStorage.getItem('colepa_conversaciones');
        if (saved) app.conversaciones = JSON.parse(saved);
    } catch (e) {
        console.error("Error cargando historial", e);
        app.conversaciones = [];
    }
}

function guardarHistorial() {
    try {
        localStorage.setItem('colepa_conversaciones', JSON.stringify(app.conversaciones));
    } catch (e) {
        console.error("Error guardando historial", e);
    }
}

function actualizarSesionActual() {
    if (!app.sesionId) return;
    
    const index = app.conversaciones.findIndex(c => c.id === app.sesionId);
    
    const primerMensaje = app.conversacionActual.find(m => m.role === 'user');
    let titulo = 'Nueva Consulta Legal';
    
    if (primerMensaje) {
        titulo = primerMensaje.content.substring(0, 50);
        if (primerMensaje.content.length > 50) titulo += '...';
    }

    const sesionData = {
        id: app.sesionId,
        titulo: titulo,
        mensajes: [...app.conversacionActual],
        fecha: new Date().toISOString()
    };

    if (index >= 0) {
        app.conversaciones[index] = sesionData;
    } else {
        app.conversaciones.unshift(sesionData);
    }
    
    guardarHistorial();
    renderizarHistorial();
}

// === ACCIONES UI ===
function nuevaConsulta() {
    app.sesionId = 'chat_' + Date.now();
    app.conversacionActual = [];
    renderizarMensajes();
    renderizarHistorial();
    
    const input = document.getElementById('messageInput');
    if (input) {
        input.value = '';
        input.focus();
    }
    actualizarBotonEnvio();
    
    const sidebar = document.getElementById('sidebar');
    if(sidebar) sidebar.classList.remove('active');
}

function cargarConversacion(id) {
    const chat = app.conversaciones.find(c => c.id === id);
    if (chat) {
        app.sesionId = chat.id;
        app.conversacionActual = [...chat.mensajes];
        renderizarMensajes();
        scrollToBottom();
        
        const sidebar = document.getElementById('sidebar');
        if(sidebar) sidebar.classList.remove('active');
        
        renderizarHistorial();
    }
}

function eliminarConversacion(e, id) {
    if (e) e.stopPropagation();
    
    if(confirm('¿Eliminar este chat permanentemente?')) {
        app.conversaciones = app.conversaciones.filter(c => c.id !== id);
        guardarHistorial();
        
        if(app.sesionId === id) {
            nuevaConsulta();
        } else {
            renderizarHistorial();
        }
    }
}

function renderizarHistorial() {
    const container = document.getElementById('chatHistory');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (app.conversaciones.length === 0) {
        container.innerHTML = `
            <div class="empty-history">
                <i class="fas fa-comments"></i>
                <p>No hay historial</p>
            </div>
        `;
        return;
    }
    
    app.conversaciones.forEach(chat => {
        const div = document.createElement('div');
        div.className = `chat-item ${chat.id === app.sesionId ? 'active' : ''}`;
        div.onclick = () => cargarConversacion(chat.id);
        
        div.innerHTML = `
            <div class="chat-item-content">
                <i class="far fa-comment-dots"></i>
                <span class="chat-title">${chat.titulo}</span>
            </div>
            <button class="chat-delete" onclick="eliminarConversacion(event, '${chat.id}')" title="Eliminar">
                <i class="fas fa-trash-alt"></i>
            </button>
        `;
        container.appendChild(div);
    });
}

// === UTILIDADES ===
function sleep(ms) { 
    return new Promise(r => setTimeout(r, ms)); 
}
