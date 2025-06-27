// Archivo: script.js (Versión Definitiva - Experiencia de Chat Completa)

document.addEventListener('DOMContentLoaded', function() {

    // --- 1. IDENTIFICACIÓN DE ELEMENTOS DEL HTML ---
    // Usamos los IDs exactos de tu archivo index.html
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const newChatButton = document.querySelector('.new-chat-btn');

    // --- 2. ¡CONFIGURACIÓN MÁS IMPORTANTE! ---
    // Esta es tu URL pública real de Railway. Ya está configurada.
    const apiUrl = 'https://colepa-demo-2-production.up.railway.app/consulta';

    // --- LÓGICA DE LA INTERFAZ DE USUARIO ---

    // Habilitar/deshabilitar el botón de envío si hay texto o no
    chatInput.addEventListener('input', () => {
        sendButton.disabled = chatInput.value.trim() === '';
    });
    
    // Lógica para "Enter" (enviar) y "Shift + Enter" (nueva línea)
    chatInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); // Previene el salto de línea por defecto
            chatForm.dispatchEvent(new Event('submit')); // Dispara el envío del formulario
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
        event.preventDefault(); // Evita que la página se recargue
        const pregunta = chatInput.value.trim();
        if (!pregunta) return;

        // Limpiar el input y deshabilitar el botón
        chatInput.value = '';
        chatInput.style.height = 'auto';
        sendButton.disabled = true;

        // Muestra la pregunta del usuario en el chat
        mostrarMensaje(pregunta, 'user');
        
        // Muestra un indicador de "pensando..."
        const typingIndicator = mostrarMensaje("...", 'bot typing');

        // --- 4. CONEXIÓN CON TU API DE FASTAPI EN RAILWAY ---
        try {
            const respuestaApi = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pregunta: pregunta })
            });

            const datos = await respuestaApi.json();
            
            if (respuestaApi.ok) {
                // Si todo salió bien, actualiza el mensaje de "pensando" con la respuesta real
                const textoRespuesta = `${datos.respuesta}\n\n---\nFuente: ${datos.fuente.ley}, Art. ${datos.fuente.articulo_numero}`;
                actualizarMensaje(typingIndicator, textoRespuesta, 'bot');
            } else {
                // Si la API devolvió un error
                actualizarMensaje(typingIndicator, `Error: ${datos.detail}`, 'bot error');
            }

        } catch (error) {
            // Si hubo un error de conexión
            console.error('Error de conexión:', error);
            actualizarMensaje(typingIndicator, 'Error de Conexión: No se pudo contactar al servidor de Colepa.', 'bot error');
        }
    });

    // --- 5. FUNCIONES AUXILIARES PARA MOSTRAR MENSAJES ---
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
        if(nuevaClase) {
            elementoMensaje.classList.add(nuevaClase);
        }
        const textoElemento = elementoMensaje.querySelector('.message-text');
        textoElemento.innerHTML = nuevoTexto.replace(/\n/g, '<br>');
    }
});
