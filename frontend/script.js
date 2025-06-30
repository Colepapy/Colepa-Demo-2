/**
 * COLEPA - Sistema Legal Profesional
 * JavaScript Futurista - Experiencia Premium tipo GPT
 */

// === CONFIGURACIÓN AVANZADA ===
const CONFIG = {
    // API Configuration
    API_BASE_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000' 
        : 'https://colepa-demo-2-production.up.railway.app',
    
    // Límites y configuraciones
    MAX_MESSAGE_LENGTH: 2000,
    MAX_HISTORY_ITEMS: 50,
    TYPING_SPEED: 25, // ms por carácter para efecto de escritura
    AUTO_SAVE_INTERVAL: 10000, // 10 segundos
    
    // Endpoints
    ENDPOINTS: {
        CONSULTA: '/api/consulta',
        HEALTH: '/api/health',
        CODIGOS: '/api/codigos'
    },

    // Mensajes del sistema
    MESSAGES: {
        CONNECTING: 'Conectando con el sistema legal...',
        ANALYZING: 'Analizando consulta legal...',
        SEARCHING: 'Buscando en la legislación paraguaya...',
        GENERATING: 'Generando respuesta profesional...',
        ERROR_CONNECTION: 'Error de conexión. Verifique su internet.',
        ERROR_SERVER: 'El servidor está temporalmente no disponible.',
        ERROR_UNKNOWN: 'Ha ocurrido un error inesperado.'
    }
};

// === ESTADO AVANZADO DE LA APLICACIÓN ===
class AppState {
    constructor() {
        this.conversacionActual = [];
        this.historialSesiones = this.cargarHistorial();
        this.sesionActualId = null;
        this.estaEscribiendo = false;
        this.estaCargando = false;
        this.sistemaOnline = true;
        this.ultimaActividad = Date.now();
        this.timeoutIds = new Map();
    }

    // Gestión de historial mejorada
    cargarHistorial() {
        try {
            const historial = localStorage.getItem('colepa_historial_v2');
            const data = historial ? JSON.parse(historial) : [];
            return Array.isArray(data) ? data : [];
        } catch (error) {
            console.error('Error cargando historial:', error);
            return [];
        }
    }

    guardarHistorial() {
        try {
            // Limitar tamaño del historial
            const historialLimitado = this.historialSesiones.slice(0, CONFIG.MAX_HISTORY_ITEMS);
            localStorage.setItem('colepa_historial_v2', JSON.stringify(historialLimitado));
            
            // Guardar timestamp de última actividad
            localStorage.setItem('colepa_last_activity', Date.now().toString());
        } catch (error) {
            console.error('Error guardando historial:', error);
            mostrarNotificacion('Error guardando el historial', 'warning');
        }
    }

    // Gestión de sesiones avanzada
    crearNuevaSesion() {
        this.sesionActualId = 'sesion_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        this.conversacionActual = [];
        
        const nuevaSesion = {
            id: this.sesionActualId,
            titulo: 'Nueva Consulta Legal',
            mensajes: [],
            fechaCreacion: new Date().toISOString(),
            ultimaActividad: new Date().toISOString(),
            metadatos: {
                version: '2.0',
                totalMensajes: 0,
                duracionSesion: 0
            }
        };
        
        this.historialSesiones.unshift(nuevaSesion);
        this.limitarHistorial();
        this.guardarHistorial();
        
        return this.sesionActualId;
    }

    agregarMensaje(role, content, metadatos = {}) {
        const mensaje = {
            id: 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5),
            role,
            content,
            timestamp: new Date().toISOString(),
            metadatos: {
                ...metadatos,
                caracterCount: content.length,
                processingTime: metadatos.processingTime || null
            }
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
            sesion.ultimaActividad = new Date().toISOString();
            
            // Actualizar título inteligentemente
            if (sesion.titulo === 'Nueva Consulta Legal') {
                const primerMensajeUsuario = this.conversacionActual.find(m => m.role === 'user');
                if (primerMensajeUsuario) {
                    sesion.titulo = this.generarTituloInteligente(primerMensajeUsuario.content);
                }
            }
            
            // Actualizar metadatos
            sesion.metadatos.totalMensajes = this.conversacionActual.length;
            sesion.metadatos.duracionSesion = Date.now() - new Date(sesion.fechaCreacion).getTime();
            
            this.guardarHistorial();
        }
    }

    generarTituloInteligente(primerMensaje) {
        const palabrasClave = {
            'civil': 'Consulta Civil',
            'penal': 'Consulta Penal', 
            'laboral': 'Consulta Laboral',
            'matrimonio': 'Matrimonio y Familia',
            'divorcio': 'Divorcio',
            'trabajo': 'Derechos Laborales',
            'violencia': 'Violencia y Protección',
            'robo': 'Delitos contra la Propiedad',
            'artículo': 'Consulta Específica'
        };

        for (const [palabra, titulo] of Object.entries(palabrasClave)) {
            if (primerMensaje.toLowerCase().includes(palabra)) {
                return titulo;
            }
        }

        // Fallback: usar las primeras palabras
        const palabras = primerMensaje.split(' ').slice(0, 4).join(' ');
        return palabras.length > 40 ? palabras.substring(0, 40) + '...' : palabras;
    }

    cargarSesion(sesionId) {
        const sesion = this.historialSesiones.find(s => s.id === sesionId);
        if (sesion) {
            this.sesionActualId = sesionId;
            this.conversacionActual = [...sesion.mensajes];
            return true;
        }
        return false;
    }

    eliminarSesion(sesionId) {
        this.historialSesiones = this.historialSesiones.filter(s => s.id !== sesionId);
        if (this.sesionActualId === sesionId) {
            this.crearNuevaSesion();
        }
        this.guardarHistorial();
    }

    limitarHistorial() {
        if (this.historialSesiones.length > CONFIG.MAX_HISTORY_ITEMS) {
            this.historialSesiones = this.historialSesiones.slice(0, CONFIG.MAX_HISTORY_ITEMS);
        }
    }
}

// === INSTANCIA GLOBAL ===
const app = new AppState();

// === ELEMENTOS DEL DOM ===
let elementos = {};

// === INICIALIZACIÓN AVANZADA ===
document.addEventListener('DOMContentLoaded', function() {
    inicializarElementos();
    inicializarEventListeners();
    inicializarApp();
    verificarEstadoSistema();
    configurarMejorasUX();
});

function inicializarElementos() {
    elementos = {
        // Contenedores principales
        sidebar: document.getElementById('sidebar'),
        chatMessages: document.getElementById('chatMessages'),
        chatHistory: document.getElementById('chatHistory'),
        
        // Formulario e input
        chatForm: document.getElementById('chatForm'),
        chatInput: document.getElementById('chatInput'),
        sendButton: document.getElementById('sendButton'),
        charCounter: document.getElementById('charCounter'),
        
        // Controles
        newChatBtn: document.getElementById('newChatBtn'),
        sidebarToggle: document.getElementById('sidebarToggle'),
        
        // Estados y overlays
        loadingOverlay: document.getElementById('loadingOverlay'),
        toastContainer: document.getElementById('toastContainer'),
        modalOverlay: document.getElementById('modalOverlay'),
        systemStatus: document.getElementById('systemStatus'),
        
        // Headers
        currentChatTitle: document.getElementById('currentChatTitle')
    };

    // Verificar elementos críticos
    const elementosCriticos = ['chatForm', 'chatInput', 'sendButton', 'chatMessages'];
    for (const elemento of elementosCriticos) {
        if (!elementos[elemento]) {
            console.error(`Elemento crítico no encontrado: ${elemento}`);
        }
    }
}

function inicializarEventListeners() {
    // Formulario principal
    if (elementos.chatForm) {
        elementos.chatForm.addEventListener('submit', manejarEnvioMensaje);
    }
    
    if (elementos.chatInput) {
        elementos.chatInput.addEventListener('input', manejarInputChange);
        elementos.chatInput.addEventListener('keydown', manejarTeclasInput);
        elementos.chatInput.addEventListener('focus', () => {
            elementos.chatInput.parentElement.classList.add('focused');
        });
        elementos.chatInput.addEventListener('blur', () => {
            elementos.chatInput.parentElement.classList.remove('focused');
        });
    }
    
    // Botones principales
    if (elementos.newChatBtn) {
        elementos.newChatBtn.addEventListener('click', iniciarNuevaConsulta);
    }
    
    if (elementos.sidebarToggle) {
        elementos.sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    // Auto-redimensionar textarea
    if (elementos.chatInput) {
        elementos.chatInput.addEventListener('input', autoRedimensionarTextarea);
    }
    
    // Gestión de conexión
    window.addEventListener('online', manejarConexionOnline);
    window.addEventListener('offline', manejarConexionOffline);
    
    // Auto-guardado inteligente
    setInterval(() => {
        if (app.conversacionActual.length > 0) {
            app.guardarHistorial();
        }
    }, CONFIG.AUTO_SAVE_INTERVAL);
    
    // Atajos de teclado avanzados
    document.addEventListener('keydown', manejarAtajosTeclado);
    
    // Prevenir pérdida de datos
    window.addEventListener('beforeunload', (e) => {
        if (app.conversacionActual.length > 0 && app.estaCargando) {
            e.preventDefault();
            e.returnValue = '';
        }
        app.guardarHistorial();
    });
}

function inicializarApp() {
    iniciarNuevaConsulta();
    renderizarHistorial();
    mostrarMensajeBienvenida();
    
    // Focus inicial en el input
    if (elementos.chatInput) {
        setTimeout(() => elementos.chatInput.focus(), 100);
    }
    
    // Cargar estado del sistema
    actualizarEstadoSistema();
}

function configurarMejorasUX() {
    // Lazy loading para el historial
    if (elementos.chatHistory) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Cargar más historial si es necesario
                    cargarMasHistorial();
                }
            });
        });
        
        const sentinel = document.createElement('div');
        sentinel.style.height = '1px';
        elementos.chatHistory.appendChild(sentinel);
        observer.observe(sentinel);
    }
    
    // Detectar inactividad
    let inactivityTimer;
    const reiniciarTimerInactividad = () => {
        clearTimeout(inactivityTimer);
        app.ultimaActividad = Date.now();
        inactivityTimer = setTimeout(() => {
            // Guardar estado después de inactividad
            app.guardarHistorial();
        }, 300000); // 5 minutos
    };
    
    ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
        document.addEventListener(event, reiniciarTimerInactividad, true);
    });
}

// === GESTIÓN DE MENSAJES AVANZADA ===
async function manejarEnvioMensaje(event) {
    event.preventDefault();
    
    if (app.estaCargando) {
        mostrarNotificacion('Espere a que termine la consulta actual', 'warning');
        return;
    }
    
    const mensaje = elementos.chatInput.value.trim();
    if (!mensaje) return;
    
    if (mensaje.length > CONFIG.MAX_MESSAGE_LENGTH) {
        mostrarNotificacion(`El mensaje excede ${CONFIG.MAX_MESSAGE_LENGTH} caracteres`, 'error');
        return;
    }
    
    // Verificar conexión
    if (!app.sistemaOnline) {
        mostrarNotificacion('Sin conexión. Verifique su internet.', 'error');
        return;
    }
    
    // Si no hay sesión, crear una nueva
    if (!app.sesionActualId) {
        app.crearNuevaSesion();
    }
    
    // Agregar mensaje del usuario
    app.agregarMensaje('user', mensaje);
    renderizarMensajes();
    renderizarHistorial();
    
    // Limpiar input con animación
    elementos.chatInput.value = '';
    elementos.chatInput.style.height = 'auto';
    actualizarContadorCaracteres();
    actualizarEstadoBotonEnvio();
    
    // Procesar consulta
    await procesarConsultaLegal(mensaje);
}

async function procesarConsultaLegal(mensajeUsuario) {
    const startTime = Date.now();
    app.estaCargando = true;
    
    try {
        // Mostrar estados de carga progresivos
        await mostrarEstadosCarga();
        
        // Enviar consulta a la API
        const respuesta = await enviarConsultaAPI();
        
        if (respuesta && respuesta.respuesta) {
            // Calcular tiempo de procesamiento
            const processingTime = Date.now() - startTime;
            
            // Agregar respuesta con efecto de escritura
            await mostrarRespuestaConEscritura(respuesta, processingTime);
            
            // Actualizar historial
            renderizarHistorial();
            
        } else {
            throw new Error('Respuesta vacía del servidor');
        }
        
    } catch (error) {
        console.error('Error procesando consulta:', error);
        await manejarErrorConsulta(error);
        
    } finally {
        ocultarIndicadorCarga();
        app.estaCargando = false;
        actualizarEstadoBotonEnvio();
        
        // Enfocar input después de un momento
        setTimeout(() => {
            if (elementos.chatInput) {
                elementos.chatInput.focus();
            }
        }, 500);
    }
}

async function mostrarEstadosCarga() {
    const estados = [
        CONFIG.MESSAGES.CONNECTING,
        CONFIG.MESSAGES.ANALYZING,
        CONFIG.MESSAGES.SEARCHING,
        CONFIG.MESSAGES.GENERATING
    ];
    
    mostrarIndicadorCarga();
    
    for (let i = 0; i < estados.length; i++) {
        actualizarTextoIndicadorCarga(estados[i]);
        await sleep(800 + Math.random() * 400); // 800-1200ms por estado
    }
}

async function mostrarRespuestaConEscritura(respuestaAPI, processingTime) {
    const contenidoRespuesta = respuestaAPI.respuesta || 'Lo siento, no pude generar una respuesta.';
    const metadatos = {
        fuente: respuestaAPI.fuente,
        recomendaciones: respuestaAPI.recomendaciones,
        processingTime: processingTime
    };
    
    // Ocultar indicador de carga
    ocultarIndicadorCarga();
    
    // Mostrar indicador de escritura
    mostrarIndicadorEscritura();
    
    // Simular pausa antes de empezar a escribir
    await sleep(500);
    
    // Agregar mensaje vacío
    const mensajeBot = app.agregarMensaje('assistant', '', metadatos);
    const indexMensaje = app.conversacionActual.length - 1;
    
    // Ocultar indicador de escritura y empezar a escribir
    ocultarIndicadorEscritura();
    renderizarMensajes();
    
    // Efecto de escritura palabra por palabra
    const palabras = contenidoRespuesta.split(' ');
    let contenidoActual = '';
    
    for (let i = 0; i < palabras.length; i++) {
        if (i > 0) contenidoActual += ' ';
        contenidoActual += palabras[i];
        
        // Actualizar mensaje
        app.conversacionActual[indexMensaje].content = contenidoActual;
        renderizarMensajes();
        scrollToBottom();
        
        // Velocidad variable basada en puntuación
        let delay = CONFIG.TYPING_SPEED;
        const ultimaChar = palabras[i].slice(-1);
        if (['.', '!', '?'].includes(ultimaChar)) {
            delay *= 3; // Pausa más larga después de oraciones
        } else if ([',', ';', ':'].includes(ultimaChar)) {
            delay *= 2; // Pausa media después de comas
        }
        
        await sleep(delay + Math.random() * 20);
    }
    
    // Actualizar con contenido final
    app.conversacionActual[indexMensaje].content = contenidoRespuesta;
    app.actualizarSesionActual();
    renderizarMensajes();
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
            'Accept': 'application/json',
            'User-Agent': 'COLEPA-Web-Client/2.0'
        },
        body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
        let errorMessage = CONFIG.MESSAGES.ERROR_SERVER;
        
        if (response.status === 503) {
            errorMessage = 'Servicio temporalmente no disponible';
        } else if (response.status === 429) {
            errorMessage = 'Demasiadas consultas. Espere un momento';
        } else if (response.status === 500) {
            errorMessage = 'Error interno del servidor';
        }
        
        throw new Error(errorMessage);
    }
    
    return await response.json();
}

async function manejarErrorConsulta(error) {
    let mensajeError = CONFIG.MESSAGES.ERROR_UNKNOWN;
    let tipoError = 'error';
    
    if (!navigator.onLine) {
        mensajeError = CONFIG.MESSAGES.ERROR_CONNECTION;
        app.sistemaOnline = false;
    } else if (error.message.includes('503')) {
        mensajeError = 'El sistema está sobrecargado. Intente en unos momentos.';
        tipoError = 'warning';
    } else if (error.message.includes('429')) {
        mensajeError = 'Ha excedido el límite de consultas. Espere antes de continuar.';
        tipoError = 'warning';
    } else if (error.message) {
        mensajeError = error.message;
    }
    
    // Agregar mensaje de error al chat
    const mensajeErrorCompleto = `**Error del Sistema**

${mensajeError}

**Sugerencias:**
- Verifique su conexión a internet
- Intente reformular su consulta
- Si el problema persiste, refresque la página

*Para asistencia técnica, contacte al administrador del sistema.*`;
    
    app.agregarMensaje('assistant', mensajeErrorCompleto, { 
        error: true, 
        errorType: tipoError,
        errorMessage: error.message 
    });
    
    renderizarMensajes();
    mostrarNotificacion(mensajeError, tipoError);
    
    // Actualizar estado del sistema
    actualizarEstadoSistema();
}

// === RENDERIZADO AVANZADO ===
function renderizarMensajes() {
    if (!elementos.chatMessages) return;
    
    if (app.conversacionActual.length === 0) {
        mostrarMensajeBienvenida();
        return;
    }
    
    elementos.chatMessages.innerHTML = '';
    
    app.conversacionActual.forEach((mensaje, index) => {
        const elementoMensaje = crearElementoMensaje(mensaje, index);
        elementos.chatMessages.appendChild(elementoMensaje);
    });
    
    scrollToBottom();
}

function crearElementoMensaje(mensaje, index) {
    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${mensaje.role}`;
    wrapper.setAttribute('data-message-id', mensaje.id || index);
    
    const esUsuario = mensaje.role === 'user';
    const nombreSender = esUsuario ? 'Usted' : 'COLEPA';
    const iconoAvatar = esUsuario ? 'fa-user' : 'fa-balance-scale';
    const claseAvatar = esUsuario ? 'user-avatar' : 'bot-avatar';
    
    let contenidoHTML = formatearContenidoMensaje(mensaje.content);
    
    // Agregar fuente legal si existe
    if (mensaje.metadatos && mensaje.metadatos.fuente) {
        contenidoHTML += crearSeccionFuenteLegal(mensaje.metadatos.fuente);
    }
    
    // Agregar recomendaciones si existen
    if (mensaje.metadatos && mensaje.metadatos.recomendaciones) {
        contenidoHTML += crearSeccionRecomendaciones(mensaje.metadatos.recomendaciones);
    }
    
    const badgeOficial = !esUsuario ? '<span class="message-badge">OFICIAL</span>' : '';
    const tiempoFormateado = formatearTiempo(mensaje.timestamp);
    
    // Indicador de procesamiento si existe
    const processingInfo = mensaje.metadatos && mensaje.metadatos.processingTime 
        ? `<span class="processing-time" title="Tiempo de procesamiento">${mensaje.metadatos.processingTime}ms</span>`
        : '';
    
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
                    <span class="message-time">${tiempoFormateado}</span>
                    ${processingInfo}
                </div>
                <div class="message-text">
                    ${contenidoHTML}
                </div>
            </div>
        </div>
    `;
    
    return wrapper;
}

function formatearContenidoMensaje(contenido) {
    return contenido
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code style="background: rgba(255,255,255,0.1); padding: 2px 4px; border-radius: 3px;">$1</code>')
        .replace(/\n/g, '<br>')
        .replace(/###\s(.*?)(?=\n|$)/g, '<h4 style="color: var(--accent-gold); margin: 1rem 0 0.5rem;">$1</h4>')
        .replace(/##\s(.*?)(?=\n|$)/g, '<h3 style="color: var(--primary-blue); margin: 1rem 0 0.5rem;">$1</h3>')
        .replace(/#\s(.*?)(?=\n|$)/g, '<h2 style="color: var(--gray-100); margin: 1rem 0 0.5rem;">$1</h2>');
}

function crearSeccionFuenteLegal(fuente) {
    if (!fuente || !fuente.ley) return '';
    
    return `
        <div class="legal-source">
            <div class="source-header">
                <i class="fas fa-book-open"></i>
                <span>Fuente Legal Oficial</span>
            </div>
            <div class="source-details">
                <strong>${fuente.ley}</strong>
                ${fuente.articulo_numero ? `, Artículo ${fuente.articulo_numero}` : ''}
                ${fuente.libro ? `<br><small>Libro: ${fuente.libro}</small>` : ''}
                ${fuente.titulo ? `<br><small>Título: ${fuente.titulo}</small>` : ''}
            </div>
        </div>
    `;
}

function crearSeccionRecomendaciones(recomendaciones) {
    if (!recomendaciones || recomendaciones.length === 0) return '';
    
    const listaRecomendaciones = recomendaciones
        .map(rec => `<li style="margin-bottom: 0.5rem;">${rec}</li>`)
        .join('');
    
    return `
        <div class="legal-source" style="border-color: #f59e0b; background: rgba(245, 158, 11, 0.05);">
            <div class="source-header" style="color: #f59e0b;">
                <i class="fas fa-exclamation-triangle"></i>
                <span>Recomendaciones Importantes</span>
            </div>
            <div class="source-details">
                <ul style="margin-left: 1.5rem; padding-left: 0;">
                    ${listaRecomendaciones}
                </ul>
            </div>
        </div>
    `;
}

function mostrarMensajeBienvenida() {
    if (!elementos.chatMessages) return;
    
    // El mensaje de bienvenida ya está en el HTML, no necesitamos recrearlo
    // Solo asegurarse de que esté visible
    const welcomeElement = elementos.chatMessages.querySelector('.welcome-message');
    if (welcomeElement) {
        welcomeElement.style.display = 'block';
    }
}

function renderizarHistorial() {
    if (!elementos.chatHistory) return;
    
    elementos.chatHistory.innerHTML = '';
    
    if (app.historialSesiones.length === 0) {
        elementos.chatHistory.innerHTML = `
            <div style="padding: 1rem; text-align: center; color: var(--gray-500); font-size: 0.875rem;">
                <i class="fas fa-inbox" style="font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.3;"></i>
                <br>No hay consultas anteriores
            </div>
        `;
        return;
    }
    
    app.historialSesiones.slice(0, 20).forEach(sesion => {
        const item = document.createElement('div');
        item.className = 'history-item';
        if (sesion.id === app.sesionActualId) {
            item.classList.add('active');
        }
        
        const totalMensajes = sesion.metadatos ? sesion.metadatos.totalMensajes : sesion.mensajes.length;
        const tiempoRelativo = formatearTiempo(sesion.ultimaActividad);
        
        item.innerHTML = `
            <div class="history-title" onclick="cargarSesion('${sesion.id}')">${sesion.titulo}</div>
            <div class="history-time">${tiempoRelativo} • ${totalMensajes} mensajes</div>
        `;
        
        elementos.chatHistory.appendChild(item);
    });
}

// === INDICADORES VISUALES AVANZADOS ===
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

function actualizarTextoIndicadorCarga(texto, subtexto = '') {
    const loadingText = document.querySelector('.loading-text');
    const loadingSubtext = document.querySelector('.loading-subtext');
    
    if (loadingText) {
        loadingText.textContent = texto;
    }
    if (loadingSubtext) {
        loadingSubtext.textContent = subtexto;
    }
}

function mostrarIndicadorEscritura() {
    // Crear y mostrar indicador de escritura temporal
    const indicador = document.createElement('div');
    indicador.id = 'typing-indicator';
    indicador.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-avatar">
                <i class="fas fa-balance-scale"></i>
            </div>
            <span class="typing-text">COLEPA está escribiendo</span>
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    
    if (elementos.chatMessages) {
        elementos.chatMessages.
elementos.chatMessages.appendChild(indicador);
       scrollToBottom();
   }
}

function ocultarIndicadorEscritura() {
   const indicador = document.getElementById('typing-indicator');
   if (indicador) {
       indicador.remove();
   }
}

// === GESTIÓN DE EVENTOS AVANZADA ===
function manejarInputChange() {
   actualizarContadorCaracteres();
   actualizarEstadoBotonEnvio();
   
   // Auto-save del borrador
   const borrador = elementos.chatInput.value;
   if (borrador.length > 10) {
       localStorage.setItem('colepa_draft', borrador);
   } else {
       localStorage.removeItem('colepa_draft');
   }
}

function actualizarContadorCaracteres() {
   if (!elementos.charCounter || !elementos.chatInput) return;
   
   const longitud = elementos.chatInput.value.length;
   elementos.charCounter.textContent = `${longitud}/${CONFIG.MAX_MESSAGE_LENGTH}`;
   
   elementos.charCounter.className = 'char-counter';
   if (longitud > CONFIG.MAX_MESSAGE_LENGTH * 0.9) {
       elementos.charCounter.classList.add('warning');
   }
   if (longitud > CONFIG.MAX_MESSAGE_LENGTH) {
       elementos.charCounter.classList.add('error');
   }
}

function actualizarEstadoBotonEnvio() {
   if (!elementos.sendButton || !elementos.chatInput) return;
   
   const tieneContenido = elementos.chatInput.value.trim().length > 0;
   const noExcedeLimite = elementos.chatInput.value.length <= CONFIG.MAX_MESSAGE_LENGTH;
   const puedeEnviar = tieneContenido && noExcedeLimite && !app.estaCargando && app.sistemaOnline;
   
   elementos.sendButton.disabled = !puedeEnviar;
   
   // Cambiar icono según estado
   const icono = elementos.sendButton.querySelector('i');
   if (icono) {
       if (app.estaCargando) {
           icono.className = 'fas fa-spinner fa-spin';
       } else if (!app.sistemaOnline) {
           icono.className = 'fas fa-exclamation-triangle';
       } else {
           icono.className = 'fas fa-paper-plane';
       }
   }
}

function manejarTeclasInput(event) {
   if (event.key === 'Enter' && !event.shiftKey) {
       event.preventDefault();
       if (elementos.chatForm) {
           elementos.chatForm.dispatchEvent(new Event('submit'));
       }
   }
   
   // Restaurar borrador en foco si existe
   if (event.key === 'Tab' && elementos.chatInput.value === '') {
       const borrador = localStorage.getItem('colepa_draft');
       if (borrador) {
           elementos.chatInput.value = borrador;
           manejarInputChange();
           autoRedimensionarTextarea();
       }
   }
}

function manejarAtajosTeclado(event) {
   // Ctrl/Cmd + Enter para enviar forzado
   if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
       if (!app.estaCargando && elementos.chatInput && elementos.chatInput.value.trim()) {
           elementos.chatForm.dispatchEvent(new Event('submit'));
       }
   }
   
   // Ctrl/Cmd + N para nueva consulta
   if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
       event.preventDefault();
       iniciarNuevaConsulta();
   }
   
   // Ctrl/Cmd + / para enfocar input
   if ((event.ctrlKey || event.metaKey) && event.key === '/') {
       event.preventDefault();
       if (elementos.chatInput) {
           elementos.chatInput.focus();
       }
   }
   
   // Escape para cancelar carga o enfocar input
   if (event.key === 'Escape') {
       if (app.estaCargando) {
           // En implementación real, cancelar request aquí
           mostrarNotificacion('Operación cancelada por el usuario', 'info');
       } else if (elementos.chatInput) {
           elementos.chatInput.focus();
       }
   }
}

function autoRedimensionarTextarea() {
   if (!elementos.chatInput) return;
   
   elementos.chatInput.style.height = 'auto';
   const nuevaAltura = Math.min(elementos.chatInput.scrollHeight, 120);
   elementos.chatInput.style.height = nuevaAltura + 'px';
}

// === GESTIÓN DE CONEXIÓN ===
function manejarConexionOnline() {
   app.sistemaOnline = true;
   actualizarEstadoSistema();
   mostrarNotificacion('Conexión restaurada', 'success');
   verificarEstadoSistema();
}

function manejarConexionOffline() {
   app.sistemaOnline = false;
   actualizarEstadoSistema();
   mostrarNotificacion('Sin conexión a internet', 'warning');
}

// === ESTADO DEL SISTEMA ===
async function verificarEstadoSistema() {
   try {
       const response = await fetch(CONFIG.API_BASE_URL + CONFIG.ENDPOINTS.HEALTH, {
           method: 'GET',
           headers: { 'Accept': 'application/json' }
       });
       
       app.sistemaOnline = response.ok;
       
       if (response.ok) {
           const data = await response.json();
           console.log('✅ Estado del sistema:', data);
       }
   } catch (error) {
       app.sistemaOnline = false;
       console.error('❌ Error verificando estado:', error);
   }
   
   actualizarEstadoSistema();
   
   // Verificar cada 30 segundos
   setTimeout(verificarEstadoSistema, 30000);
}

function actualizarEstadoSistema() {
   if (!elementos.systemStatus) return;
   
   const indicador = elementos.systemStatus.querySelector('.status-indicator');
   const texto = elementos.systemStatus.querySelector('.status-text');
   
   if (app.sistemaOnline) {
       if (indicador) indicador.style.background = 'var(--success)';
       if (texto) texto.textContent = 'Sistema Operativo';
   } else {
       if (indicador) indicador.style.background = 'var(--error)';
       if (texto) texto.textContent = 'Sistema Fuera de Línea';
   }
   
   actualizarEstadoBotonEnvio();
}

// === NOTIFICACIONES AVANZADAS ===
function mostrarNotificacion(mensaje, tipo = 'info', duracion = 5000) {
   if (!elementos.toastContainer) return;
   
   const toast = document.createElement('div');
   toast.className = `toast ${tipo}`;
   
   const iconos = {
       success: 'fa-check-circle',
       error: 'fa-exclamation-circle',
       warning: 'fa-exclamation-triangle',
       info: 'fa-info-circle'
   };
   
   toast.innerHTML = `
       <div class="toast-content">
           <div class="toast-icon">
               <i class="fas ${iconos[tipo] || iconos.info}"></i>
           </div>
           <div class="toast-message">${mensaje}</div>
           <button class="toast-close" onclick="this.parentElement.parentElement.remove()">
               <i class="fas fa-times"></i>
           </button>
       </div>
   `;
   
   elementos.toastContainer.appendChild(toast);
   
   // Auto-remove
   setTimeout(() => {
       if (toast.parentNode) {
           toast.style.animation = 'toastSlideOut 0.3s ease-in';
           setTimeout(() => toast.remove(), 300);
       }
   }, duracion);
}

// === UTILIDADES AVANZADAS ===
function sleep(ms) {
   return new Promise(resolve => setTimeout(resolve, ms));
}

function scrollToBottom() {
   requestAnimationFrame(() => {
       if (elementos.chatMessages) {
           elementos.chatMessages.scrollTop = elementos.chatMessages.scrollHeight;
       }
   });
}

function formatearTiempo(timestamp) {
   if (!timestamp) return 'Ahora';
   
   const fecha = new Date(timestamp);
   const ahora = new Date();
   const diff = ahora - fecha;
   
   const minutos = Math.floor(diff / (1000 * 60));
   const horas = Math.floor(diff / (1000 * 60 * 60));
   const dias = Math.floor(diff / (1000 * 60 * 60 * 24));
   
   if (minutos < 1) return 'Ahora';
   if (minutos < 60) return `${minutos}m`;
   if (horas < 24) return `${horas}h`;
   if (dias < 7) return `${dias}d`;
   
   return fecha.toLocaleDateString('es-PY', { 
       day: 'numeric', 
       month: 'short',
       year: fecha.getFullYear() !== ahora.getFullYear() ? 'numeric' : undefined
   });
}

function cargarMasHistorial() {
   // Implementar carga lazy del historial si es necesario
   console.log('Cargando más historial...');
}

// === FUNCIONES PÚBLICAS ===
window.iniciarNuevaConsulta = function() {
   // Limpiar borrador
   localStorage.removeItem('colepa_draft');
   
   app.crearNuevaSesion();
   renderizarMensajes();
   renderizarHistorial();
   
   if (elementos.chatInput) {
       elementos.chatInput.focus();
   }
   
   if (elementos.currentChatTitle) {
       elementos.currentChatTitle.textContent = 'Nueva Consulta Legal';
   }
   
   mostrarNotificacion('Nueva consulta iniciada', 'success', 2000);
};

window.cargarSesion = function(sesionId) {
   if (app.cargarSesion(sesionId)) {
       renderizarMensajes();
       renderizarHistorial();
       
       const sesion = app.historialSesiones.find(s => s.id === sesionId);
       if (elementos.currentChatTitle && sesion) {
           elementos.currentChatTitle.textContent = sesion.titulo;
       }
       
       scrollToBottom();
       mostrarNotificacion('Consulta cargada', 'success', 2000);
   }
};

window.eliminarSesion = function(sesionId) {
   if (confirm('¿Está seguro de que desea eliminar esta consulta?')) {
       app.eliminarSesion(sesionId);
       renderizarMensajes();
       renderizarHistorial();
       mostrarNotificacion('Consulta eliminada', 'success', 3000);
   }
};

window.enviarEjemplo = function(texto) {
   if (elementos.chatInput) {
       elementos.chatInput.value = texto;
       manejarInputChange();
       autoRedimensionarTextarea();
       elementos.chatInput.focus();
       
       // Auto-enviar después de un momento para que el usuario vea el texto
       setTimeout(() => {
           if (elementos.chatForm) {
               elementos.chatForm.dispatchEvent(new Event('submit'));
           }
       }, 500);
   }
};

window.toggleSidebar = function() {
   if (elementos.sidebar) {
       elementos.sidebar.classList.toggle('open');
   }
};

window.limpiarChat = function() {
   if (app.conversacionActual.length === 0) {
       iniciarNuevaConsulta();
       return;
   }
   
   if (confirm('¿Está seguro de que desea iniciar una nueva consulta?')) {
       iniciarNuevaConsulta();
   }
};

window.exportarConsulta = function() {
   if (app.conversacionActual.length === 0) {
       mostrarNotificacion('No hay conversación para exportar', 'warning');
       return;
   }
   
   if (elementos.modalOverlay) {
       elementos.modalOverlay.classList.add('active');
   }
};

window.cerrarModal = function() {
   if (elementos.modalOverlay) {
       elementos.modalOverlay.classList.remove('active');
   }
};

window.exportar = function(formato) {
   if (app.conversacionActual.length === 0) {
       mostrarNotificacion('No hay conversación para exportar', 'warning');
       return;
   }
   
   const sesion = app.historialSesiones.find(s => s.id === app.sesionActualId);
   const titulo = sesion ? sesion.titulo : 'Consulta Legal';
   const fecha = new Date().toLocaleDateString('es-PY');
   const hora = new Date().toLocaleTimeString('es-PY');
   
   let contenido = '';
   
   if (formato === 'json') {
       // Exportar como JSON estructurado
       const dataExport = {
           titulo: titulo,
           fecha: fecha,
           hora: hora,
           version: '2.0',
           totalMensajes: app.conversacionActual.length,
           mensajes: app.conversacionActual.map(msg => ({
               id: msg.id,
               role: msg.role,
               content: msg.content,
               timestamp: msg.timestamp,
               metadatos: msg.metadatos
           })),
           metadatos: {
               duracionSesion: sesion ? sesion.metadatos.duracionSesion : null,
               exportadoEn: new Date().toISOString()
           }
       };
       
       contenido = JSON.stringify(dataExport, null, 2);
       
   } else {
       // Exportar como texto plano
       contenido = `COLEPA - Consulta Legal Oficial\n`;
       contenido += `===============================\n\n`;
       contenido += `Título: ${titulo}\n`;
       contenido += `Fecha: ${fecha} - ${hora}\n`;
       contenido += `Total de mensajes: ${app.conversacionActual.length}\n`;
       contenido += `${'='.repeat(50)}\n\n`;
       
       app.conversacionActual.forEach((mensaje, index) => {
           const rol = mensaje.role === 'user' ? 'USUARIO' : 'COLEPA';
           const tiempo = formatearTiempo(mensaje.timestamp);
           
           contenido += `[${index + 1}] ${rol} (${tiempo})\n`;
           contenido += `${'-'.repeat(30)}\n`;
           contenido += `${mensaje.content}\n\n`;
           
           if (mensaje.metadatos && mensaje.metadatos.fuente) {
               contenido += `📖 Fuente Legal: ${mensaje.metadatos.fuente.ley}`;
               if (mensaje.metadatos.fuente.articulo_numero) {
                   contenido += `, Artículo ${mensaje.metadatos.fuente.articulo_numero}`;
               }
               contenido += `\n\n`;
           }
           
           if (mensaje.metadatos && mensaje.metadatos.processingTime) {
               contenido += `⏱️ Tiempo de procesamiento: ${mensaje.metadatos.processingTime}ms\n\n`;
           }
       });
       
       contenido += `${'='.repeat(50)}\n`;
       contenido += `Exportado desde COLEPA - Sistema Legal de Paraguay\n`;
       contenido += `${new Date().toISOString()}\n\n`;
       contenido += `AVISO LEGAL: Esta información es de carácter general y no sustituye\n`;
       contenido += `el asesoramiento profesional de un abogado especializado.\n`;
   }
   
   // Crear y descargar archivo
   const mimeType = formato === 'json' ? 'application/json' : 'text/plain';
   const extension = formato === 'json' ? 'json' : 'txt';
   
   const blob = new Blob([contenido], { type: `${mimeType};charset=utf-8` });
   const url = URL.createObjectURL(blob);
   const a = document.createElement('a');
   
   a.href = url;
   a.download = `colepa_${titulo.replace(/[^a-zA-Z0-9]/g, '_')}_${fecha.replace(/\//g, '-')}.${extension}`;
   document.body.appendChild(a);
   a.click();
   document.body.removeChild(a);
   URL.revokeObjectURL(url);
   
   cerrarModal();
   mostrarNotificacion(`Consulta exportada como ${extension.toUpperCase()}`, 'success');
};

// === INICIALIZACIÓN FINAL ===
// Auto-restaurar borrador si existe
document.addEventListener('DOMContentLoaded', () => {
   setTimeout(() => {
       const borrador = localStorage.getItem('colepa_draft');
       if (borrador && elementos.chatInput && elementos.chatInput.value === '') {
           elementos.chatInput.value = borrador;
           manejarInputChange();
           autoRedimensionarTextarea();
           
           // Mostrar notificación sutil
           mostrarNotificacion('Borrador restaurado', 'info', 3000);
       }
   }, 1000);
});

// === DEBUGGING (Solo en desarrollo) ===
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
   window.COLEPA_DEBUG = {
       app,
       CONFIG,
       elementos,
       mostrarNotificacion,
       verificarEstadoSistema,
       renderizarMensajes,
       renderizarHistorial
   };
   console.log('🔧 Modo debug activado. Acceso: window.COLEPA_DEBUG');
}
