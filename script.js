document.addEventListener('DOMContentLoaded', function() {

    // Identifica los elementos de tu página por su ID
    const formularioConsulta = document.getElementById('chat-form');
    const cajaDePregunta = document.getElementById('chat-input');
    const botonEnviar = document.getElementById('send-button');
    const areaRespuesta = document.getElementById('chat-messages');

    // ¡LA LÍNEA MÁS IMPORTANTE! Pega aquí la URL pública que te dio Railway
    const apiUrl = 'https://colepa-demo-2-production.up.railway.app
';

    // Esta función se activa cuando el usuario envía el formulario
    formularioConsulta.addEventListener('submit', async function(event) {
        event.preventDefault(); // Evita que la página se recargue

        const pregunta = cajaDePregunta.value.trim();
        if (!pregunta) return;

        // Limpia el input y muestra un estado de "cargando"
        cajaDePregunta.value = '';
        botonEnviar.disabled = true;
        mostrarMensaje(pregunta, 'user'); // Muestra la pregunta del usuario
        const typingIndicator = mostrarMensaje('COLEPA está pensando...', 'bot typing'); // Muestra "pensando..."

        try {
            // Llama a tu API pública en Railway
            const respuestaApi = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pregunta: pregunta })
            });

            // Elimina el indicador de "pensando..."
            areaRespuesta.removeChild(typingIndicator);
            const datos = await respuestaApi.json();

            if (respuestaApi.ok) {
                // Si todo salió bien, muestra la respuesta formateada
                const textoRespuesta = `${datos.respuesta}\n\n---\nFuente: ${datos.fuente.ley}, Artículo N° ${datos.fuente.articulo_numero}`;
                mostrarMensaje(textoRespuesta, 'bot');
            } else {
                mostrarMensaje(`Error: ${datos.detail}`, 'bot error');
            }

        } catch (error) {
            areaRespuesta.removeChild(typingIndicator);
            console.error('Error de conexión:', error);
            mostrarMensaje('Error de Conexión: No se pudo contactar al servidor de Colepa.', 'bot error');
        } finally {
            botonEnviar.disabled = false;
        }
    });

    function mostrarMensaje(texto, tipo) {
        // (Aquí va la lógica para crear y añadir los divs de mensaje al chat, como en el ejemplo anterior)
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', tipo);
        // ... (código para construir el HTML del mensaje)
        areaRespuesta.appendChild(messageElement);
        areaRespuesta.scrollTop = areaRespuesta.scrollHeight;
        return messageElement;
    }
});
