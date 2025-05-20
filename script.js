// COLEPA - Consulta de Leyes del Paraguay
// Lógica de chat, integración con n8n y manejo de interfaz

const webhookUrl = 'https://mgcapra314.app.n8n.cloud/webhook/Colepa2025';
const historyKey = 'colepa_chat_history';
const chatWindow = document.getElementById('chat-window');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const typingIndicator = document.getElementById('typing-indicator');
const errorMessage = document.getElementById('error-message');
const historyList = document.getElementById('history-list');
const newConversationBtn = document.getElementById('new-conversation');

let conversation = [];

// Inicializar
window.onload = () => {
    cargarHistorial();
    renderizarConversacion();
};

// Evento de envío de mensaje
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const pregunta = userInput.value.trim();
    if (!pregunta) return;
    agregarMensaje('user', pregunta);
    userInput.value = '';
    mostrarIndicador(true);
    mostrarError('');
    try {
        const respuesta = await enviarPregunta(pregunta);
        agregarMensaje('bot', respuesta);
        guardarHistorial();
    } catch (err) {
        mostrarError(err.message);
        agregarMensaje('bot', 'Lo siento, ocurrió un error al procesar tu consulta.');
    } finally {
        mostrarIndicador(false);
    }
});

// Nueva conversación
newConversationBtn.addEventListener('click', () => {
    conversation = [];
    renderizarConversacion();
    mostrarError('');
});

// Cargar historial desde localStorage
function cargarHistorial() {
    const guardado = localStorage.getItem(historyKey);
    if (guardado) {
        try {
            conversation = JSON.parse(guardado);
        } catch {
            conversation = [];
        }
    }
    actualizarSidebar();
}

// Guardar historial en localStorage
function guardarHistorial() {
    localStorage.setItem(historyKey, JSON.stringify(conversation));
    actualizarSidebar();
}

// Actualizar lista de historial
function actualizarSidebar() {
    historyList.innerHTML = '';
    if (!conversation.length) return;
    conversation.forEach((msg, idx) => {
        if (msg.role === 'user') {
            const li = document.createElement('li');
            li.textContent = msg.content.length > 32 ? msg.content.slice(0, 32) + '…' : msg.content;
            li.title = msg.content;
            li.onclick = () => mostrarSoloMensaje(idx);
            historyList.appendChild(li);
        }
    });
}

// Mostrar solo un mensaje del historial
function mostrarSoloMensaje(idx) {
    const userMsg = conversation[idx];
    const botMsg = conversation[idx+1];
    if (userMsg && botMsg && botMsg.role === 'bot') {
        chatWindow.innerHTML = '';
        renderMensaje(userMsg);
        renderMensaje(botMsg);
    }
}

// Renderizar toda la conversación
function renderizarConversacion() {
    chatWindow.innerHTML = '';
    conversation.forEach(renderMensaje);
}

// Agregar mensaje a la conversación
function agregarMensaje(role, content) {
    conversation.push({ role, content });
    renderMensaje({ role, content });
}

// Renderizar un mensaje
function renderMensaje({ role, content }) {
    const div = document.createElement('div');
    div.className = 'message ' + (role === 'user' ? 'user' : 'bot');
    div.innerHTML = `
        <div class="avatar">${role === 'user' ? '👤' : '<img src="assets/img/balanza.png" alt="Bot" style="width:28px;height:28px;">'}</div>
        <div class="message-content">${formatearRespuesta(content)}</div>
    `;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Mostrar/ocultar indicador de escritura
function mostrarIndicador(mostrar) {
    typingIndicator.style.display = mostrar ? 'block' : 'none';
}

// Mostrar mensaje de error
function mostrarError(msg) {
    errorMessage.textContent = msg;
    errorMessage.style.display = msg ? 'block' : 'none';
}

// Enviar pregunta al webhook n8n
async function enviarPregunta(pregunta) {
    try {
        const response = await fetch(webhookUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ pregunta })
        });
        if (!response.ok) {
            if (response.status === 0) throw new Error('Servidor no responde.');
            throw new Error(`Error del servidor: ${response.status}`);
        }
        let data;
        try {
            data = await response.json();
        } catch {
            throw new Error('La respuesta del servidor no es JSON válido.');
        }
        if (!data || typeof data.respuesta !== 'string' || !data.respuesta.trim()) {
            throw new Error('El servidor no devolvió una respuesta válida.');
        }
        return data.respuesta;
    } catch (err) {
        if (err.name === 'TypeError') {
            throw new Error('Problema de red o CORS. Verifica tu conexión.');
        }
        throw err;
    }
}

// Formatear respuesta para mejor legibilidad
function formatearRespuesta(texto) {
    // Puedes mejorar el formateo (enlaces, negritas, etc.) aquí
    return texto.replace(/\n/g, '<br>');
}
