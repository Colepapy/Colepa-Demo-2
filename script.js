// Archivo: script.js (Versión Final y Definitiva para Colepa)

document.addEventListener('DOMContentLoaded', function() {

    // --- 1. IDENTIFICACIÓN DE ELEMENTOS DEL HTML ---
    // Estos son los IDs de tu archivo index.html
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const newChatButton = document.querySelector('.new-chat-btn');

    // --- 2. URL PÚBLICA DE TU API EN RAILWAY ---
    // Esta es la dirección correcta de tu "cerebro"
    const apiUrl = 'https://colepa-demo-2-production.up.railway.app/consulta';

    // --- LÓGICA DE LA INTERFAZ DE USUARIO ---

    // Habilitar/deshabilitar el botón de envío
    chatInput.addEventListener('input', () => {
        sendButton.disabled = chatInput.value.trim() === '';
    });
    
    // Lógica para "Enter" (enviar) y "Shift + Enter" (nueva línea)
    chatInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // Auto-ajuste de altura para el cuadro de texto
    chatInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
    
    // Funcionalidad del botón "Nueva Consulta"
    if(newChatButton) {
        newChatButton.addEventListener('click', () => {
            const welcomeMessageHTML = `
                <div class="message system">
                    <div class="message-content">
                        <div class="message-header">
                            <div class="bot-avatar"><i class="fas fa-balance-scale"></i></div>
                            <div class="bot-name">COLEPA</div>
                        </div>
                        <div class="message-text">
                            <p>¡Bienvenido a COLEPA - Consulta de Leyes del Paraguay!</p>
                            <p>Soy tu asistente legal virtual. ¿En qué puedo ayudarte hoy?</p>
                        </div>
                    </div>
                </div>`;
            chatMessages.innerHTML = welcomeMessageHTML;
        });
    }

    // --- 3. FUNCIÓN PRINCIPAL AL ENVIAR LA CONSULTA ---
    chatForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        const pregunta = chatInput.value.trim();
        if (!pregunta) return;

        chatInput.value = '';
        chatInput.style.height = 'auto';
        sendButton.disabled = true;

        // Muestra la pregunta del usuario en el chat
        mostrarMensaje(pregunta, 'user');
        
        // Muestra el indicador de "pensando..."
        const typingIndicator = mostrarMensaje("COLEPA está pensando...", 'bot typing');

        try {
            // --- 4. CONEXIÓN CON TU API DE FASTAPI ---
            const respuestaApi = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pregunta: pregunta })
            });

            const datos = await respuestaApi.json();
            
            // Reemplaza el mensaje "pensando" con la respuesta real
            if (respuestaApi.ok) {
                const textoRespuesta = `${datos.respuesta}\n\n---\nFuente: ${datos.fuente.ley}, Art. ${datos.fuente.articulo_numero}`;
                actualizarMensaje(typingIndicator, textoRespuesta, 'bot');
            } else {
                actualizarMensaje(typingIndicator, `Error: ${datos.detail}`, 'bot error');
            }

        } catch (error) {
            console.error('Error de conexión:', error);
            actualizarMensaje(typingIndicator, 'Error de Conexión: No se pudo contactar al servidor de Colepa.', 'bot error');
        }
    });

    // --- 5. FUNCIONES PARA MANEJAR EL CHAT ---
    function mostrarMensaje(texto, tipo) {
        const messageWrapper = document.createElement('div');
        messageWrapper.classList.add('message', tipo);
        const avatarIcon = tipo === 'user' ? 'fa-user' : 'fa-balance-scale';
        const senderName = tipo === 'user' ? 'Tú' : 'COLEPA';
        
        messageWrapper.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <div class="bot-avatar"><i class="fas ${avatarIcon}"></i></div>
                    <div class="sender-name">${senderName}</div>
                </div>
                <div class="message-text">${texto.replace(/\n/g, '<br>')}</div>
            </div>
        `;
        
        chatMessages.appendChild(messageWrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return messageWrapper;
    }
    
    function actualizarMensaje(elementoMensaje, nuevoTexto, nuevaClase) {
        elementoMensaje.classList.remove('typing');
        if(nuevaClase) elementoMensaje.classList.add(nuevaClase);
        
        const textoElemento = elementoMensaje.querySelector('.message-text');
        textoElemento.innerHTML = nuevoTexto.replace(/\n/g, '<br>');
    }
});
