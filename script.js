// Archivo: script.js (Versión Definitiva con Manejo de Fuente Nula)

document.addEventListener('DOMContentLoaded', function() {

    // --- 1. IDENTIFICACIÓN DE ELEMENTOS DEL HTML ---
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const newChatButton = document.querySelector('.new-chat-btn');

    // --- 2. URL PÚBLICA DE TU API EN RAILWAY ---
    const apiUrl = 'https://colepa-demo-2-production.up.railway.app/consulta';

    // --- LÓGICA DE LA INTERFAZ DE USUARIO ---
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

        mostrarMensaje(pregunta, 'user');
        const typingIndicator = mostrarMensaje("COLEPA está pensando...", 'bot typing');

        try {
            const respuestaApi = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pregunta: pregunta })
            });
            
            const datos = await respuestaApi.json();
            
            if (respuestaApi.ok) {
                let textoRespuesta;
                
                // --- ¡AQUÍ ESTÁ LA CORRECCIÓN CLAVE! ---
                // Verificamos si la respuesta incluye una 'fuente' antes de intentar mostrarla.
                if (datos.fuente && datos.fuente.ley && datos.fuente.articulo_numero) {
                    // Si hay fuente, la formateamos
                    textoRespuesta = `${datos.respuesta}\n\n---\nFuente: ${datos.fuente.ley}, Art. ${datos.fuente.articulo_numero}`;
                } else {
                    // Si no hay fuente, es una respuesta conversacional y mostramos solo el texto.
                    textoRespuesta = datos.respuesta;
                }
                actualizarMensaje(typingIndicator, textoRespuesta, 'bot');
            } else {
                actualizarMensaje(typingIndicator, `Error: ${datos.detail}`, 'bot-error');
            }

        } catch (error) {
            console.error('Error de conexión:', error);
            actualizarMensaje(typingIndicator, 'Error de Conexión: No se pudo contactar al servidor de Colepa.', 'bot-error');
        }
    });

    // --- 5. FUNCIONES PARA MANEJAR EL CHAT ---
    function mostrarMensaje(texto, tipo) {
        const messageWrapper = document.createElement('div');
        const classes = tipo.split(' ');
        messageWrapper.classList.add('message', ...classes);
        
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
        elementoMensaje.classList.remove('bot-error'); 
        if(nuevaClase) {
            const classes = nuevaClase.split(' ');
            elementoMensaje.classList.add(...classes);
        }
        
        const textoElemento = elementoMensaje.querySelector('.message-text');
        textoElemento.innerHTML = nuevoTexto.replace(/\n/g, '<br>');
    }
});
