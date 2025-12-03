/**
 * COLEPA - JavaScript Ultimate Version
 * Fusiona: Diseño Gemini + Funcionalidad Original Completa + Corrección de Bugs
 */

// === CONFIGURACIÓN ===
const CONFIG = {
    API_BASE_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000' 
        : 'https://colepa-demo-2-production.up.railway.app',
    ENDPOINT_CONSULTA: '/api/consulta',
    ENDPOINT_HEALTH: '/api/health',
    MAX_MESSAGE_LENGTH: 2000,
    TYPING_SPEED: 40 // Ajustado para que se sienta fluido
};

// === ESTADO GLOBAL ===
let app = {
    conversaciones: [],
    conversacionActual: [],
    sesionId: null,
    isLoading: false
};

// === INICIALIZACIÓN ===
document.addEventListener('DOMContentLoaded', function() {
    inicializar();
});

function inicializar() {
    // 1. Cargar datos previos
    cargarHistorial();
    renderizarHistorial();
    
    // 2. Verificar estado inicial de la UI
    actualizarBotonEnvio();
    
    // 3. Auto-focus al input
    const input = document.getElementById('messageInput');
    if (input) input.focus();

    // 4. Verificar conexión con el backend (Restaurado del original)
    verificarConexionAPI();

    console.log('🚀 COLEPA Sistema Legal Inicializado');
}

// === VERIFICACIÓN DE CONEXIÓN (RESTAURADO) ===
async function verificarConexionAPI() {
    try {
        const response = await fetch(CONFIG.API_BASE_URL + CONFIG.ENDPOINT_HEALTH, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Conexión con API exitosa:', data);
        } else {
            throw new Error('Estado de API no OK');
        }
    } catch (error) {
        console.error('❌ Error conectando con API:', error);
        mostrarAvisoConexion(false);
    }
}

function mostrarAvisoConexion(exito) {
    if (!exito) {
        // Creamos un aviso discreto pero visible
        const aviso = document.createElement('div');
        aviso.style.cssText = `
            position: fixed; top: 20px; right: 20px; 
            background: rgba(255, 75, 75, 0.9); color: white;
            padding: 12px 20px; border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            z-index: 9999; font-size: 14px; display: flex; align-items: center; gap: 10px;
            backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);
            animation: fadeIn 0.5s ease;
        `;
        aviso.innerHTML = `<i class="fas fa-wifi"></i> <span>Sin conexión al servidor legal</span>`;
        document.body.appendChild(aviso);
        
        // Se quita solo después de 5 segundos
        setTimeout(() => aviso.remove(), 8000);
    }
}

// === LÓGICA DE INPUT Y ENVÍO (CORREGIDA) ===

function manejarTeclas(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault(); // Evitar salto de línea
        enviarMensaje(event);
    }
}

function manejarInput() {
    const input = document.getElementById('messageInput');
    if (input) {
        // Ajuste automático de altura
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
    
    // El botón se habilita si hay texto Y no está cargando
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

// === FUNCIÓN PRINCIPAL DE ENVÍO ===
function enviarMensaje(event) {
    if (event) event.preventDefault();
    
    if (app.isLoading) return;
    
    const input = document.getElementById('messageInput');
    if (!input) return;
    
    const mensaje = input.value.trim();
    if (!mensaje) return;
    
    // Validación de longitud (Restaurado)
    if (mensaje.length > CONFIG.MAX_MESSAGE_LENGTH) {
        alert(`Mensaje demasiado largo. Máximo ${CONFIG.MAX_MESSAGE_LENGTH} caracteres.`);
        return;
    }

    // Iniciar nueva sesión si no existe
    if (!app.sesionId) nuevaConsulta();
    
    // 1. Agregar mensaje del usuario visualmente
    agregarMensaje('user', mensaje);
    
    // 2. Limpiar input y resetear botón
    input.value = '';
    input.style.height = 'auto';
    actualizarBotonEnvio();
    
    // 3. Procesar respuesta con la API
    procesarRespuesta(mensaje);
}

// === PROCESAMIENTO CON API Y MANEJO DE ERRORES (COMPLETO) ===
async function procesarRespuesta(mensajeUsuario) {
    app.isLoading = true;
    actualizarBotonEnvio(); 
    mostrarIndicadorEscritura(); 
    
    try {
        const url = CONFIG.API_BASE_URL + CONFIG.ENDPOINT_CONSULTA;
        
        // Verificar emergencia localmente antes de enviar (Restaurado)
        if (detectarEmergencia(mensajeUsuario)) {
            console.warn("⚠️ Posible emergencia detectada en el input");
            // Aquí podríamos mostrar un aviso inmediato si quisiéramos
        }

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
        
        // Manejo de errores detallado (Restaurado del original)
        if (!response.ok) {
            let errorMessage = `Error ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                if (errorData.detalle) errorMessage += `\nDetalle: ${errorData.detalle}`;
            } catch (e) { console.error('No se pudo parsear error JSON'); }
            throw new Error(errorMessage);
        }
        
        const data = await response.json();
        
        ocultarIndicadorEscritura();
        await mostrarRespuestaConEscritura(data);
        
    } catch (error) {
        console.error('❌ Error completo:', error);
        ocultarIndicadorEscritura();
        
        // Mensajes de error específicos (Restaurado del original)
        let mensajeError = '🚨 **No pude procesar tu consulta**\n\n';
        
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            mensajeError += 'Parece que no hay conexión con el servidor de COLEPA. Verifica tu internet.';
        } else if (error.message.includes('404')) {
            mensajeError += 'El servicio de consultas no está respondiendo (404).';
        } else if (error.message.includes('500')) {
            mensajeError += 'Error interno del sistema legal. Estamos trabajando en ello.';
        } else {
            mensajeError += `Ocurrió un error técnico: ${error.message}`;
        }
        
        agregarMensaje('assistant', mensajeError);
        
    } finally {
        app.isLoading = false;
        actualizarBotonEnvio(); 
        
        // Auto-focus para seguir escribiendo rápido
        setTimeout(() => {
            const input = document.getElementById('messageInput');
            if(input) input.focus();
        }, 100);
    }
}

// === DETECCIÓN DE EMERGENCIA (RESTAURADO) ===
function detectarEmergencia(contenido) {
    const palabrasEmergencia = [
        'línea 137', '137', 'violencia', 'maltrato', 'agresión', 
        'golpes', 'pega', 'abuso', 'emergencia', 'inmediatamente',
        'urgente', 'peligro', 'amenaza', 'matar', 'socorro'
    ];
    
    const contenidoLower = contenido.toLowerCase();
    return palabrasEmergencia.some(palabra => contenidoLower.includes(palabra));
}

// === RENDERIZADO VISUAL (DISEÑO GEMINI) ===

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
    
    // Mostrar/Ocultar bienvenida
    if (app.conversacionActual.length === 0) {
        if(welcome) {
            welcome.style.display = 'flex';
            welcome.style.opacity = '1';
        }
        // Limpiar todo excepto bienvenida
        Array.from(container.children).forEach(child => {
            if (child.id !== 'welcomeMessage') child.remove();
        });
        return;
    } else {
        if(welcome) {
            welcome.style.display = 'none';
            welcome.style.opacity = '0';
        }
    }
    
    // Re-renderizado seguro
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
    
    let contenidoHTML = formatearContenido(mensaje.content);
    
    // Si es asistente, agregar fuentes y recomendaciones
    if (mensaje.role === 'assistant') {
        if (mensaje.metadata && mensaje.metadata.fuente && mensaje.metadata.fuente.ley) {
            contenidoHTML += crearFuenteLegal(mensaje.metadata.fuente);
        }
        if (mensaje.metadata && mensaje.metadata.recomendaciones) {
            contenidoHTML += crearRecomendaciones(mensaje.metadata.recomendaciones);
        }
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';
    
    const iconClass = mensaje.role === 'user' ? 'fa-user' : 'fa-scale-balanced'; // Icono legal
    
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
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Negritas
        .replace(/\*(.*?)\*/g, '<em>$1</em>') // Cursivas
        .replace(/\n/g, '<br>'); // Saltos de línea
}

function crearFuenteLegal(fuente) {
    if (!fuente || !fuente.ley) return '';
    return `
        <div class="legal-source">
            <div class="source-header">
                <i class="fas fa-book"></i>
                <span>Fuente Legal</span>
            </div>
            <div style="color: var(--text-secondary);">
                <strong>${fuente.ley}</strong>
                ${fuente.articulo_numero ? ` • Art. ${fuente.articulo_numero}` : ''}
                ${fuente.titulo ? `<br><span style="font-size: 0.85em; opacity: 0.8;">${fuente.titulo}</span>` : ''}
            </div>
        </div>
    `;
}

function crearRecomendaciones(recs) {
    if (!recs || !Array.isArray(recs) || recs.length === 0) return '';
    const items = recs.map(r => `<li>${r}</li>`).join('');
    return `
        <div style="margin-top: 15px; padding: 10px; background: rgba(255,255,255,0.03); border-radius: 8px;">
            <div style="font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 5px;">Sugerencias</div>
            <ul style="padding-left:20px; color:var(--text-secondary); font-size: 0.9em; line-height: 1.6;">${items}</ul>
        </div>
    `;
}

// === EFECTOS VISUALES Y ESCRITURA ===

async function mostrarRespuestaConEscritura(data) {
    const contenido = data.respuesta || 'Lo siento, no pude generar una respuesta.';
    const metadata = {
        fuente: data.fuente,
        recomendaciones: data.recomendaciones,
        tiempo_procesamiento: data.tiempo_procesamiento
    };
    
    const mensajeIdx = app.conversacionActual.length;
    agregarMensaje('assistant', '', metadata); // Mensaje vacío inicial
    
    const palabras = contenido.split(' ');
    let textoAcumulado = '';
    
    // Efecto de escritura palabra por palabra
    for (let i = 0; i < palabras.length; i++) {
        textoAcumulado += (i > 0 ? ' ' : '') + palabras[i];
        app.conversacionActual[mensajeIdx].content = textoAcumulado;
        
        // Renderizado optimizado: solo actualizar si es necesario o cada X palabras
        if (i % 2 === 0 || i === palabras.length - 1) {
            renderizarMensajes();
            scrollToBottom();
        }
        
        await sleep(CONFIG.TYPING_SPEED);
    }
    
    actualizarSesionActual();
}

function mostrarIndicadorEscritura() {
    const container = document.getElementById('messagesContainer');
    if (!container) return;

    // Remover si ya existe
    ocultarIndicadorEscritura();

    const indicador = document.createElement('div');
    indicador.id = 'typingIndicator';
    indicador.className = 'message assistant';
    indicador.innerHTML = `
        <div class="message-content-wrapper">
            <div class="message-avatar">
                <i class="fas fa-scale-balanced fa-bounce"></i>
            </div>
            <div class="message-text" style="display: flex; align-items: center; gap: 8px;">
                <span style="color: var(--text-muted); font-size: 0.9em;">Analizando legislación...</span>
                <div class="typing-dots">
                    <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
                </div>
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

// === HISTORIAL (LOCAL STORAGE) - RESTAURADO COMPLETO ===
function cargarHistorial() {
    try {
        const saved = localStorage.getItem('colepa_conversaciones'); // Usando la key original
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
    
    // Título inteligente basado en el primer mensaje
    const primerMensaje = app.conversacionActual.find(m => m.role === 'user');
    let titulo = 'Nueva Consulta Legal';
    
    if (primerMensaje) {
        titulo = primerMensaje.content.substring(0, 40);
        if (primerMensaje.content.length > 40) titulo += '...';
    }

    const sesionData = {
        id: app.sesionId,
        titulo: titulo,
        mensajes: [...app.conversacionActual], // Copia segura
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

// === ACCIONES DE UI ===
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
}

function cargarConversacion(id) {
    const chat = app.conversaciones.find(c => c.id === id);
    if (chat) {
        app.sesionId = chat.id;
        app.conversacionActual = [...chat.mensajes]; // Copia segura
        renderizarMensajes();
        scrollToBottom();
        
        // En móvil cerrar sidebar automáticamente
        const sidebar = document.getElementById('sidebar');
        if(sidebar) sidebar.classList.remove('active');
        
        // Resaltar activo en sidebar
        renderizarHistorial();
    }
}

function eliminarConversacion(e, id) {
    if (e) e.stopPropagation(); // Evitar abrir el chat al borrar
    
    if(confirm('¿Deseas eliminar este historial permanentemente?')) {
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
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 0.9em;">No hay historial reciente</div>';
        return;
    }
    
    app.conversaciones.forEach(chat => {
        const div = document.createElement('div');
        div.className = `chat-item ${chat.id === app.sesionId ? 'active' : ''}`;
        div.onclick = () => cargarConversacion(chat.id);
        
        div.innerHTML = `
            <div style="flex:1; overflow:hidden; text-overflow:ellipsis;">
                <i class="far fa-comment-dots" style="margin-right:8px; opacity:0.7;"></i>
                ${chat.titulo}
            </div>
            <button class="chat-delete" onclick="eliminarConversacion(event, '${chat.id}')" title="Eliminar">
                <i class="fas fa-trash-alt"></i>
            </button>
        `;
        container.appendChild(div);
    });
}

// === UTILIDADES ===
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
