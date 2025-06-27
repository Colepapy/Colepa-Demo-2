document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const newChatButton = document.querySelector('.new-chat-btn');

    // ✅ URL correcta del backend
    const apiUrl = 'https://colepa-demo-2-production.up.railway.app/consultar';

    chatInput.addEventListener('input', () => {
        sendButton.disabled = chatInput.value.trim() === '';
    });

    chatInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    chatInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    if (newChatButton) {
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

    chatForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        const pregunta = chatInput.value.trim();
        if (!pregunta) return;

        chatInput.value = '';
        chatInput.style.height = 'auto';
        sendButton.disabled = true;

        mostrarMensaje(pregunta, 'user');

        const typingIndicator = mostrarMensaje("COLEPA está redactando la respuesta...", 'bot typing');

        try {
            const respuestaApi = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pregunta: pregunta })
            });

            const datos = await respuestaApi.json();

            if (respuestaApi.ok) {
                const textoRespuesta = datos.fuente
                    ? `${datos.respuesta}\n\n---\nFuente: ${datos.fuente.ley}, Art. ${datos.fuente.articulo_numero}`
                    : datos.respuesta;

                actualizarMensaje(typingIndicator, textoRespuesta, 'bot');
            } else {
                actualizarMensaje(typingIndicator, `Error: ${datos.detail}`, 'bot error');
            }

        } catch (error) {
            console.error('Error de conexión:', error);
            actualizarMensaje(typingIndicator, 'Error de Conexión: No se pudo contactar al servidor de Colepa.', 'bot error');
        }
    });

    function mostrarMensaje(texto, tipo) {
        const messageWrapper = document.createElement('div');
        messageWrapper.classList.add('message');
        if (tipo.includes(' ')) {
            const clases = tipo.split(' ');
            clases.forEach(c => messageWrapper.classList.add(c));
        } else {
            messageWrapper.classList.add(tipo);
        }

        const avatarIcon = tipo.includes('user') ? 'fa-user' : 'fa-balance-scale';
        const senderName = tipo.includes('user') ? 'Tú' : 'COLEPA';

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
        if (nuevaClase) elementoMensaje.classList.add(nuevaClase);

        const textoElemento = elementoMensaje.querySelector('.message-text');
        textoElemento.innerHTML = nuevoTexto.replace(/\n/g, '<br>');
    }
});
