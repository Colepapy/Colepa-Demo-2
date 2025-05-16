import os
import requests
import json
import logging
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Crear la aplicación Flask
app = Flask(__name__, static_url_path='')
app.secret_key = os.environ.get("SESSION_SECRET", "colepa_secret_key_development")
# Habilitar CORS para todas las rutas
CORS(app)
# Configurar la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# Webhook URL de n8n
WEBHOOK_URL = "https://mgcapra314.app.n8n.cloud/webhook/Colepa2025"
# Modelo para guardar las conversaciones
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(100), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Conversation {self.id}>'
# Modelo para estadísticas
class Statistic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query_count = db.Column(db.Integer, default=0)
    unique_users = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Statistic {self.id}>'
# Crear tablas en la base de datos
with app.app_context():
    db.create_all()
    
    # Inicializar estadísticas si no existen
    if not Statistic.query.first():
        initial_stats = Statistic()
        db.session.add(initial_stats)
        db.session.commit()
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
    logger.debug(f"Received chat request: {data}")
    
    if not data or 'message' not in data:
        return jsonify({"error": "Mensaje no proporcionado"}), 400
    
    # Extraer mensaje y ID de chat
    message = data.get('message')
    chat_id = data.get('chatId', 'chat_default')
    
    try:
        # Actualizar estadísticas
        stats = Statistic.query.first()
        if stats:
            stats.query_count += 1
            db.session.commit()
        
        # Registrar consulta en la base de datos
        conversation = Conversation()
        conversation.chat_id = chat_id
        conversation.user_message = message
        db.session.add(conversation)
        db.session.commit()
        
        # Formato correcto para el webhook de n8n - enviar texto plano sin formato
        webhook_data = {
            "message": message,
            "chatId": chat_id,
            "query": message  # Añadiendo campo alternativo por si n8n espera este nombre
        }
        
        logger.debug(f"Sending to webhook: {webhook_data}")
        
        # Reenviar al webhook de n8n
        response = requests.post(
            WEBHOOK_URL,
            json=webhook_data,
            headers={"Content-Type": "application/json"}
        )
        
        logger.debug(f"Webhook response status: {response.status_code}")
        logger.debug(f"Webhook response content: {response.text[:200]}...")  # Log primeros 200 caracteres
        
        # Verificar respuesta
        if response.status_code == 200:
            try:
                response_data = response.json()
                
                # Identificar el campo de respuesta en los datos recibidos
                bot_response = ''
                
                # Intentar varios formatos comunes de respuesta
                if 'response' in response_data:
                    bot_response = response_data['response']
                elif 'respuesta' in response_data:
                    bot_response = response_data['respuesta']
                elif 'answer' in response_data:
                    bot_response = response_data['answer']
                elif 'text' in response_data:
                    bot_response = response_data['text']
                else:
                    # Si no encontramos un campo conocido, usar todo el contenido
                    bot_response = str(response_data)
                
                # Actualizar la respuesta en la base de datos
                conversation.bot_response = bot_response
                db.session.commit()
                
                # Asegurar que el formato de respuesta sea consistente para el frontend
                return jsonify({"response": bot_response})
            except ValueError as e:
                logger.error(f"Error parsing JSON response: {e}")
                return jsonify({
                    "error": "Formato de respuesta inválido del webhook",
                    "response": "Lo siento, hubo un problema con la respuesta del asistente. Por favor, intenta de nuevo."
                }), 500
        else:
            error_msg = f"Error del servidor n8n: {response.status_code}"
            logger.error(error_msg)
            return jsonify({
                "error": error_msg,
                "response": "Lo siento, no pude procesar tu consulta en este momento. Por favor, intenta de nuevo más tarde."
            }), 500
            
    except Exception as e:
        logger.error(f"Exception in chat endpoint: {str(e)}")
        return jsonify({
            "error": str(e),
            "response": "Lo siento, hubo un problema al conectar con el servicio. Por favor, verifica tu conexión a internet e intenta de nuevo."
        }), 500
# Ruta para verificar el estado del servidor
@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el servidor está funcionando"""
    return jsonify({
        "status": "ok", 
        "message": "COLEPA API está funcionando correctamente",
        "database": "connected" if db else "disconnected"
    })
# Ruta para obtener estadísticas básicas
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Endpoint para obtener estadísticas básicas"""
    stats = Statistic.query.first()
    
    if not stats:
        return jsonify({"error": "No se encontraron estadísticas"}), 404
    
    # Contar usuarios únicos basados en chat_ids distintos
    unique_chats = db.session.query(Conversation.chat_id).distinct().count()
    stats.unique_users = unique_chats
    stats.last_updated = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        "total_queries": stats.query_count,
        "unique_users": stats.unique_users,
        "last_updated": stats.last_updated.isoformat()
    })
# Ruta para ejecutar un test de conexión con el webhook
@app.route('/api/test-webhook', methods=['GET'])
def test_webhook():
    """Endpoint para probar la conexión con el webhook de n8n"""
    try:
        response = requests.post(
            WEBHOOK_URL,
            json={"message": "Prueba de conexión", "chatId": "test_connection"},
            headers={"Content-Type": "application/json"}
        )
        
        status_code = response.status_code
        try:
            content = response.json()
        except:
            content = {"text": response.text[:200]}
            
        return jsonify({
            "status": "success" if status_code == 200 else "error",
            "status_code": status_code,
            "response": content
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
