import os
import requests
import json
from flask import Flask, request, jsonify, send_from_directory, render_template
# Crear la aplicación Flask
app = Flask(__name__, static_url_path='')
app.secret_key = os.environ.get("SESSION_SECRET", "colepa_secret_key_development")
# Webhook URL de n8n
WEBHOOK_URL = "https://mgcapra314.app.n8n.cloud/webhook/Colepa2025"
@app.route('/')
def index():
    """Ruta principal que sirve el archivo index.html"""
    return send_from_directory('.', 'index.html')
@app.route('/style.css')
def styles():
    """Ruta para servir el archivo CSS"""
    return send_from_directory('.', 'style.css')
@app.route('/script.js')
def scripts():
    """Ruta para servir el archivo JavaScript"""
    return send_from_directory('.', 'script.js')
@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint para procesar los mensajes del chat y reenviarlos al n8n"""
    data = request.json
    
    if not data or 'message' not in data:
        return jsonify({"error": "Mensaje no proporcionado"}), 400
    
    # Extraer mensaje y ID de chat
    message = data.get('message')
    chat_id = data.get('chatId', 'chat_default')
    
    try:
        # Reenviar al webhook de n8n
        response = requests.post(
            WEBHOOK_URL,
            json={"message": message, "chatId": chat_id},
            headers={"Content-Type": "application/json"}
        )
        
        # Verificar respuesta
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                "error": f"Error del servidor n8n: {response.status_code}",
                "response": "Lo siento, no pude procesar tu consulta en este momento. Por favor, intenta de nuevo más tarde."
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "response": "Lo siento, hubo un problema al conectar con el servicio. Por favor, verifica tu conexión a internet e intenta de nuevo."
        }), 500
# Ruta para verificar el estado del servidor
@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el servidor está funcionando"""
    return jsonify({"status": "ok", "message": "COLEPA API está funcionando correctamente"})
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
