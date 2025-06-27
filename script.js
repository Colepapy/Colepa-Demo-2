// Archivo: script.js (Para Colepa)

document.addEventListener('DOMContentLoaded', function() {

    // --- 1. IDENTIFICACIÓN DE ELEMENTOS DEL HTML ---
    // Usamos los IDs que encontré en tu archivo index.html
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');

    // --- 2. ¡CONFIGURACIÓN MÁS IMPORTANTE! ---
    // Reemplaza el texto de abajo con la URL pública real que te dio Railway
    const apiUrl = 'https://TU-URL-PUBLICA-DE-RAILWAY-AQUI/consulta';

    // Función para habilitar/deshabilitar el botón de envío
    chatInput.addEventListener('input', () => {
        if (chatInput.value.trim() !== '') {
            sendButton.disabled = false;
        } else {
            sendButton.disabled = true;
        }
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

        // --- Muestra la pregunta del usuario en el chat ---
        mostrarMensaje(pregunta, 'user');

        // --- Muestra un indicador de "pensando..." ---
        const typingIndicator = mostrarMensaje('COLEPA está pensando...', 'bot typing');

        try {
            // 4. LLAMADA A TU API EN RAILWAY
            const respuestaApi = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pregunta: pregunta })
            });

            const datos = await respuestaApi.json();

            // Elimina el indicador de "pensando..."
            chatMessages.removeChild(typingIndicator);

            if (respuestaApi.ok) {
                // Si todo salió bien, muestra la respuesta de la IA
                const textoRespuesta = `${datos.respuesta}\n\n---\nFuente: ${datos.fuente.ley}, Artículo N° ${datos.fuente.articulo_numero}`;
                mostrarMensaje(textoRespuesta, 'bot');
            } else {
                // Si la API devuelve un error
                mostrarMensaje(`Error: ${datos.detail}`, 'bot error');
            }

        } catch (error) {
            // Elimina el indicador de "pensando..."
            chatMessages.removeChild(typingIndicator);
            console.error('Error de conexión:', error);
            mostrarMensaje('Error de Conexión: No se pudo contactar al servidor de Colepa.', 'bot error');
        }
    });

    // --- 5. FUNCIÓN PARA MOSTRAR MENSAJES EN EL CHAT ---
    function mostrarMensaje(texto, tipo) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', tipo);

        let avatarHtml = '';
        let senderName = '';

        if (tipo.includes('bot')) {
            avatarHtml = `<div class="bot-avatar"><i class="fas fa-balance-scale"></i></div>`;
            senderName = 'COLEPA';
        } else { // Usuario
            avatarHtml = `<div class="user-avatar"><i class="fas fa-user"></i></div>`;
            senderName = 'Tú';
        }

        // Reemplaza los saltos de línea del texto con etiquetas <br> para que se muestren en HTML
        const textoFormateado = texto.replace(/\n/g, '<br>');

        messageElement.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    ${avatarHtml}
                    <div class="sender-name">${senderName}</div>
                </div>
                <div class="message-text">${textoFormateado}</div>
            </div>
        `;
        
        chatMessages.appendChild(messageElement);
        // Hacer scroll automático para ver el último mensaje
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageElement; // Devuelve el elemento para poder eliminarlo (útil para el "pensando...")
    }

    // Auto-ajuste de altura para el textarea
    chatInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
});
