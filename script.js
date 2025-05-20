document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const newChatBtn = document.querySelector('.new-chat-btn');
    
    // State variables
    let isWaitingForResponse = false;
    let chatHistory = [];
    let currentChatId = generateChatId();
    
    // Webhook URL de n8n - conexión directa
    const webhookUrl = 'https://mgcapra314.app.n8n.cloud/webhook/Colepa2025';
    
    // Enable/disable send button based on input content
    chatInput.addEventListener('input', function() {
        sendButton.disabled = chatInput.value.trim() === '' || isWaitingForResponse;
        
        // Auto resize textarea
        chatInput.style.height = 'auto';
        chatInput.style.height = (chatInput.scrollHeight) + 'px';
    });
    
    // Handle new chat button click
    newChatBtn.addEventListener('click', function() {
        startNewChat();
    });
    
    // Handle form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = chatInput.value.trim();
        if (message === '' || isWaitingForResponse) return;
        
        sendMessage(message);
    });
    
    // Function to start a new chat
    function startNewChat() {
        currentChatId = generateChatId();
        chatMessages.innerHTML = '';
        
        // Add welcome message
        const welcomeMessage = {
            role: 'system',
            content: `
                <p>¡Bienvenido a COLEPA - Consulta de Leyes del Paraguay!</p>
                <p>Soy tu asistente legal virtual. Puedo responder preguntas sobre leyes paraguayas y brindarte información legal precisa.</p>
                <p>¿En qué puedo ayudarte hoy?</p>
            `
        };
        
        addMessageToUI(welcomeMessage);
        updateChatHistory();
        
        // Reset input
        chatInput.value = '';
        chatInput.style.height = 'auto';
        sendButton.disabled = true;
    }
    
    // Function to send message to n8n agent
    async function sendMessage(message) {
        // Add user message to UI
        const userMessage = {
            role: 'user',
            content: message
        };
        addMessageToUI(userMessage);
        
        // Clear input and disable send button
        chatInput.value = '';
        chatInput.style.height = 'auto';
        sendButton.disabled = true;
        isWaitingForResponse = true;
        
        // Show typing indicator
        showTypingIndicator();
        
        try {
            // Enviamos un JSON con una estructura muy simple - solo el mensaje
            console.log("Enviando mensaje simple:", message);
            console.log("Webhook URL:", webhookUrl);
            
            const response = await fetch(webhookUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    pregunta: message  // Cambiado de 'texto' a 'pregunta'
                })
            });
            
            if (!response.ok) {
                throw new Error(`Error HTTP: ${response.status}`);
            }
            
            // Capturar el texto completo de la respuesta
            const responseText = await response.text();
            console.log("Respuesta completa (texto):", responseText);
            
            let botResponseText = "";
            
            // Intentamos procesar la respuesta
            if (responseText && responseText.length > 0) {
                try {
                    // Intenta parse como JSON
                    const data = JSON.parse(responseText);
                    console.log("Respuesta parseada como JSON:", data);
                    
                    // Según tu configuración en Respond to Webhook, buscamos 'respuesta'
                    if (data.respuesta) {
                        botResponseText = data.respuesta;
                    } else if (data.output) {
                        botResponseText = data.output;
                    } else if (typeof data === 'string') {
                        botResponseText = data;
                    } else {
                        // Si llegamos aquí, no encontramos un campo de respuesta conocido
                        botResponseText = JSON.stringify(data, null, 2);
                    }
                } catch (jsonError) {
                    console.error('Error al parsear JSON:', jsonError);
                    botResponseText = responseText;
                }
            } else {
                botResponseText = "Respuesta vacía del servidor. Por favor, revisa la configuración del nodo 'AI Agent' en n8n.";
            }
            
            // Remove typing indicator
            hideTypingIndicator();
            
            // Add bot response to UI
            const botMessage = {
                role: 'system',
                content: formatBotResponse(botResponseText)
            };
            addMessageToUI(botMessage);
            
            // Save to chat history
            saveChatMessage(userMessage, botMessage);
            
        } catch (error) {
            console.error('Error completo:', error);
            
            // Remove typing indicator
            hideTypingIndicator();
            
            // Add error message to UI with más detalles
            const errorMessage = {
                role: 'system',
                content: `
                    <p>Lo siento, ha ocurrido un error al comunicarse con el servidor.</p>
                    <p>Por favor, intenta con estas acciones:</p>
                    <ul>
                        <li>Verifica que el flujo de trabajo en n8n esté activo (indicador verde)</li>
                        <li>Comprueba la configuración de los nodos 'AI Agent' y 'Respond to Webhook'</li>
                        <li>Asegúrate de que la base de datos Qdrant esté respondiendo</li>
                    </ul>
                    <p><small>Detalles técnicos: ${error.message}</small></p>
                `
            };
            addMessageToUI(errorMessage);
        }
        
        isWaitingForResponse = false;
    }
    
    // Function to add a message to the UI
    function addMessageToUI(message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        
        if (message.role === 'user') {
            messageDiv.classList.add('user');
            messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="message-text">${escapeHTML(message.content)}</div>
                </div>
            `;
        } else {
            messageDiv.classList.add('system');
            messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="message-header">
                        <div class="bot-avatar">
                            <i class="fas fa-balance-scale"></i>
                        </div>
                        <div class="bot-name">COLEPA</div>
                    </div>
                    <div class="message-text">${message.content}</div>
                </div>
            `;
        }
        
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Function to show typing indicator
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.classList.add('typing-indicator');
        typingDiv.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;
        chatMessages.appendChild(typingDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Function to hide typing indicator
    function hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    // Function to format bot response
    function formatBotResponse(text) {
        // Replace URLs with clickable links
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        text = text.replace(urlRegex, function(url) {
            return `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
        });
        
        // Wrap paragraphs in <p> tags
        const paragraphs = text.split('\n\n');
        return paragraphs.map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
    }
    
    // Function to save chat messages
    function saveChatMessage(userMessage, botMessage) {
        const chatEntry = {
            id: Date.now(),
            chatId: currentChatId,
            userMessage: userMessage.content,
            botMessage: botMessage.content,
            timestamp: new Date().toISOString()
        };
        
        chatHistory.push(chatEntry);
        
        // Only keep the most recent 10 chats
        if (chatHistory.length > 50) {
            chatHistory = chatHistory.slice(-50);
        }
        
        updateChatHistory();
        
        // Save to localStorage
        try {
            localStorage.setItem('colepa_chat_history', JSON.stringify(chatHistory));
        } catch (e) {
            console.error('Error saving to localStorage:', e);
        }
    }
    
    // Function to update chat history UI
    function updateChatHistory() {
        const historyContainer = document.querySelector('.chat-history');
        historyContainer.innerHTML = '';
        
        // Get unique chat IDs and the most recent message from each
        const uniqueChats = {};
        for (const chat of chatHistory) {
            if (!uniqueChats[chat.chatId] || 
                new Date(chat.timestamp) > new Date(uniqueChats[chat.chatId].timestamp)) {
                uniqueChats[chat.chatId] = chat;
            }
        }
        
        // Create a history item for each unique chat
        for (const chatId in uniqueChats) {
            const chat = uniqueChats[chatId];
            const historyItem = document.createElement('div');
            historyItem.classList.add('history-item');
            if (chatId === currentChatId) {
                historyItem.classList.add('active');
            }
            
            // Create a truncated preview of the user message
            const previewText = chat.userMessage.length > 25 
                ? chat.userMessage.substring(0, 25) + '...' 
                : chat.userMessage;
            
            historyItem.innerHTML = `
                <i class="fas fa-comment"></i>
                <span>${escapeHTML(previewText)}</span>
            `;
            
            historyItem.addEventListener('click', function() {
                loadChat(chat.chatId);
            });
            
            historyContainer.appendChild(historyItem);
        }
    }
    
    // Function to load a specific chat
    function loadChat(chatId) {
        currentChatId = chatId;
        chatMessages.innerHTML = '';
        
        // Filter chat history for the selected chat
        const chatMessages = chatHistory.filter(chat => chat.chatId === chatId);
        
        // Sort by timestamp
        chatMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        // Add messages to UI
        for (const chat of chatMessages) {
            const userMessage = {
                role: 'user',
                content: chat.userMessage
            };
            const botMessage = {
                role: 'system',
                content: chat.botMessage
            };
            
            addMessageToUI(userMessage);
            addMessageToUI(botMessage);
        }
        
        updateChatHistory();
    }
    
    // Helper function to generate a chat ID
    function generateChatId() {
        return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    // Helper function to escape HTML
    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag]));
    }
    
    // Load chat history from localStorage on page load
    function loadChatHistory() {
        try {
            const savedHistory = localStorage.getItem('colepa_chat_history');
            if (savedHistory) {
                chatHistory = JSON.parse(savedHistory);
                updateChatHistory();
            }
        } catch (e) {
            console.error('Error loading from localStorage:', e);
        }
    }
    
    // Handle sidebar toggle on mobile
    function setupMobileSidebar() {
        // Check if we're on mobile
        if (window.innerWidth <= 768) {
            const sidebar = document.querySelector('.sidebar');
            
            // Create toggle button if it doesn't exist
            if (!document.querySelector('.menu-toggle')) {
                const menuToggle = document.createElement('div');
                menuToggle.className = 'menu-toggle';
                menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
                document.querySelector('.chat-header').prepend(menuToggle);
                
                // Add event listener
                menuToggle.addEventListener('click', function() {
                    sidebar.classList.toggle('open');
                });
            }
        }
    }
    
    // Initialize sidebar for mobile
    setupMobileSidebar();
    
    // Add resize listener for mobile sidebar
    window.addEventListener('resize', setupMobileSidebar);
    
    // Initialize chat
    loadChatHistory();
    startNewChat();
});
