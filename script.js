// Configuración de la API n8n
const N8N_WEBHOOK_URL = 'https://mgcapra314.app.n8n.cloud/webhook/Colepa2025'; // ✅ Tu webhook

async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');

    if (!userInput.value.trim()) return;

    // Mensaje del usuario
    const userDiv = document.createElement('div');
    userDiv.className = 'message user-message';
    userDiv.innerHTML = `
        <div class="message-content">${userInput.value}</div>
        <div class="message-icon">🧑💻</div>
    `;
    chatMessages.appendChild(userDiv);

    // Mensaje de carga del bot
    const botDiv = document.createElement('div');
    botDiv.className = 'message bot-message';
    botDiv.innerHTML = `
        <div class="message-content"><div class="loading-dots">⏳ Procesando consulta</div></div>
        <div class="message-icon">⚖️</div>
    `;
    chatMessages.appendChild(botDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        // Llamada a tu API de n8n
        const response = await fetch(N8N_WEBHOOK_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // 🔐 Si necesitas autenticación, agrega:
                // 'Authorization': 'Bearer TU_API_KEY'
            },
            body: JSON.stringify({
                question: userInput.value.trim(),
                metadata: {
                    user_ip: 'TU_IP',  // Opcional: Agrega datos útiles
                    timestamp: new Date().toISOString()
                }
            })
        });

        if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
        
        const data = await response.json();
        
        // Actualizar respuesta del bot
        botDiv.querySelector('.message-content').innerHTML = `
            ${data.answer} 
            <div class="legal-reference">📚 Fuente: ${data.law_source || "Leyes de Paraguay"}</div>
        `;

    } catch (error) {
        botDiv.querySelector('.message-content').innerHTML = `
            ❌ Error: ${error.message}. 
            <em>Intenta nuevamente o contacta al soporte.</em>
        `;
    } finally {
        userInput.value = '';
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Animación de carga
document.querySelector('.loading-dots').innerHTML = 
    '⏳ Procesando' + '<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>';
