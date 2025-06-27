// Archivo: script.js (Versión Final para Conectar a Railway)

document.addEventListener('DOMContentLoaded', function() {

    // --- 1. IDENTIFICACIÓN DE ELEMENTOS DEL HTML ---
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const newChatButton = document.querySelector('.new-chat-btn');

    // --- 2. ¡CONFIGURACIÓN MÁS IMPORTANTE! ---
    // Esta es la URL pública de tu API que está funcionando en Railway.
    const apiUrl = 'https://colepa-demo-2-production.up.railway.app/consulta';

    // Función para habilitar/deshabilitar el botón de envío
    chatInput.addEventListener('input', () => {
        sendButton.disabled = chatInput.value.trim() === '';
    });

    // --- 3. FUNCIÓN PRINCIPAL AL ENVIAR LA CONSULTA ---
    chatForm.addEventListener('submit', async function(event) {
        event.preventDefault(); // Evita que la página se recargue
        const pregunta = chatInput.value.trim();
        if (!pregunta) return;

        // Limpiar el input y deshabilitar el botón mientras se procesa
        chatInput.value = '';
        sendButton.disabled = true;
        chatInput.style.height = 'auto'; // Resetear altura del textarea

        // Muestra la pregunta del usuario en el chat
        mostrarMensaje(pregunta, 'user');

        // Muestra un indicador de "pensando..."
        const typingIndicator = mostrarMensaje('COLEPA está pensando...', 'bot typing');

        try {
            // 4. LLAMADA A TU API PÚBLICA EN RAILWAY
            const respuestaApi = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pregunta: pregunta })
            });

            // 5. Procesa la respuesta del servidor
            const datos = await respuestaApi.json();

            // Elimina el indicador de "pensando..."
            if (typingIndicator) {
                chatMessages.removeChild(typingIndicator);
            }

            if (respuestaApi.ok) {
                // Si todo salió bien (código 200)
                const textoRespuesta = `${datos.respuesta}\n\n---\nFuente: ${datos.fuente.ley}, Artículo N° ${datos.fuente.articulo_numero}`;
                mostrarMensaje(textoRespuesta, 'bot');
            } else {
                // Si la API devolvió un error (ej: Artículo no encontrado)
                mostrarMensaje(`Error desde la API: ${datos.detail}`, 'bot error');
            }

        } catch (error) {
            // Si hubo un error de conexión (ej: sin internet)
            if (typingIndicator) {
                chatMessages.removeChild(typingIndicator);
            }
            console.error('Error de conexión:', error);
            mostrarMensaje('Error de Conexión: No se pudo contactar al servidor de Colepa. Por favor, revisa tu conexión e inténtalo de nuevo.', 'bot error');
        } finally {
            // Vuelve a habilitar el botón para una nueva consulta
            sendButton.disabled = false;
        }
    });

    // --- 5. FUNCIÓN PARA AÑADIR UN NUEVO MENSAJE AL CHAT ---
    function mostrarMensaje(texto, tipo) {
        const messageWrapper = document.createElement('div');
        messageWrapper.classList.add('message', tipo);

        const avatarIcon = tipo === 'user' ? 'fa-user' : 'fa-balance-scale';
        const senderName = tipo === 'user' ? 'Tú' : 'COLEPA';
        
        // Reemplaza los saltos de línea del texto con etiquetas <br> para que se muestren en HTML
        const textoFormateado = texto.replace(/\n/g, '<br>');

        messageWrapper.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <div class="bot-avatar"><i class="fas ${avatarIcon}"></i></div>
                    <div class="sender-name">${senderName}</div>
                </div>
                <div class="message-text">${textoFormateado}</div>
            </div>
        `;
        
        chatMessages.appendChild(messageWrapper);
        // Hacer scroll automático para ver el último mensaje
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageWrapper; // Devuelve el elemento para poder eliminarlo (útil para el "pensando...")
    }

    // Funcionalidad del botón "Nueva Consulta"
    if(newChatButton) {
        newChatButton.addEventListener('click', () => {
            // Borra todos los mensajes excepto el de bienvenida
            const welcomeMessage = chatMessages.querySelector('.system');
            chatMessages.innerHTML = '';
            if(welcomeMessage) {
                chatMessages.appendChild(welcomeMessage);
            }
        });
    }

    // Auto-ajuste de altura para el textarea
    chatInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
});
    }
});
