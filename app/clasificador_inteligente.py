# Archivo: app/clasificador_inteligente.py
# COLEPA - Clasificador Inteligente para Comportamiento Conversacional

import re
import random
import logging
from enum import Enum
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class TipoConsulta(Enum):
    SALUDO = "saludo"
    DESPEDIDA = "despedida"
    CONSULTA_LEGAL = "consulta_legal"
    TEMA_NO_LEGAL = "tema_no_legal"
    CONVERSACION_GENERAL = "conversacion_general"
    AGRADECIMIENTO = "agradecimiento"

class ClasificadorCOLEPA:
    """
    Clasificador inteligente que determina si COLEPA debe:
    1. Responder de forma conversacional (sin búsqueda)
    2. Buscar en la base legal (con búsqueda)
    3. Redireccionar amablemente (temas no legales)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Patrones para detectar diferentes tipos de consulta
        self.patrones = {
            TipoConsulta.SALUDO: [
                r'\b(hola|buenas|buenos días|buenas tardes|buenas noches|saludos|hey|buenas|holi)\b',
                r'como (estas|estás|andas|te va)',
                r'que tal',
                r'buen día',
                r'como va',
                r'que hace'
            ],
            
            TipoConsulta.DESPEDIDA: [
                r'\b(adiós|adios|chau|nos vemos|hasta luego|bye|me voy|hasta pronto)\b',
                r'hasta (la vista|mañana|después)',
                r'que tengas',
                r'me despido',
                r'hasta otra',
                r'nos vemos'
            ],
            
            TipoConsulta.AGRADECIMIENTO: [
                r'\b(gracias|muchas gracias|te agradezco|mil gracias|genial|perfecto|excelente|buenísimo|ok|vale)\b$',
                r'muy (bueno|útil|claro|bien)',
                r'está (claro|perfecto|bien|bueno)',
                r'me sirvió',
                r'entendido',
                r'comprendo'
            ],
            
            TipoConsulta.CONSULTA_LEGAL: [
                # Artículos específicos
                r'\b(artículo|articulo|art\.?|ley|código|decreto|resolución)\s*\d+',
                
                # Códigos legales
                r'\b(constitución|código civil|código penal|código laboral|código tributario|código aduanero)',
                
                # Temas familiares
                r'\b(divorcio|matrimonio|herencia|testamento|sucesión|patrimonio|esposo|esposa|cónyuge)',
                
                # Temas legales generales
                r'\b(contrato|obligación|derecho|legal|jurídico|normativa|denuncia|demanda)',
                
                # Procedimientos judiciales
                r'\b(juicio|tribunal|juzgado|sentencia|proceso|fiscal|abogado)',
                
                # Temas tributarios/aduaneros
                r'\b(impuesto|tributo|fiscal|aduanero|set|senacsa|aduana)',
                
                # Violencia y delitos
                r'\b(violencia|maltrato|agresión|delito|pena|prisión|golpes|abuso|acoso)',
                
                # Temas laborales
                r'\b(trabajo|empleado|empleador|salario|despido|laboral|jefe|sueldo)',
                
                # Preguntas típicas legales
                r'que dice (el|la|los|las)',
                r'como (proceder|hacer|tramitar)',
                r'cuales son (los|las) (requisitos|pasos|documentos)',
                r'es (legal|válido|obligatorio|ilegal)',
                r'tengo derecho',
                r'puedo (demandar|reclamar|exigir|denunciar)',
                r'me pueden',
                r'está permitido',
                r'qué hago si',
                
                # Accidentes y daños
                r'\b(choque|chocaron|atropello|accidente|daños|perjuicios)',
                
                # Menores
                r'\b(menor|niño|hijo|adolescente|adopción|tutela)',
                
                # Términos legales específicos
                r'\b(denuncia|querella|acusación|defensa|prueba|testigo)'
            ],
            
            TipoConsulta.TEMA_NO_LEGAL: [
                # Clima
                r'\b(clima|tiempo|temperatura|lluvia|calor|frío|pronóstico)\b',
                
                # Deportes
                r'\b(fútbol|deportes|cerro|olimpia|libertad|guaraní|partido|gol)\b',
                
                # Comida
                r'\b(receta|cocina|comida|asado|chipa|empanada|sopa|dulce)\b',
                
                # Entretenimiento
                r'\b(música|película|serie|netflix|youtube|canción|artista)\b',
                
                # Medicina/Salud (no legal)
                r'\b(medicina|salud|doctor|enfermedad|síntoma|hospital|pastilla)\b',
                
                # Tecnología
                r'\b(computadora|celular|internet|app|facebook|whatsapp|instagram)\b',
                
                # Preguntas no legales
                r'como (cocinar|hacer comida|preparar|instalar)',
                r'que (película|serie|música|restaurante) recomiendas',
                r'donde (comer|comprar|ir)',
                r'cuando (juega|es|hay)',
                
                # Matemáticas/Tareas
                r'\b(matemática|tarea|ejercicio|resolver|calcular)\b',
                
                # Ubicaciones/Direcciones
                r'como llegar',
                r'donde queda',
                r'que hora',
                
                # Chismes/Entretenimiento
                r'que opinas de',
                r'te gusta',
                r'cual prefieres'
            ]
        }
        
        # Respuestas predefinidas para cada tipo
        self.respuestas = {
            TipoConsulta.SALUDO: [
                "¡Hola! Soy COLEPA, tu asistente legal especializado en la legislación paraguaya. ¿En qué consulta legal puedo ayudarte hoy?",
                "¡Buenas! Muy bien, gracias. Soy COLEPA, estoy aquí para ayudarte con cualquier consulta sobre las leyes de Paraguay. ¿Qué necesitas saber?",
                "¡Hola! Un gusto saludarte. Soy tu asistente legal paraguayo. ¿Hay alguna pregunta legal en la que pueda asistirte?",
                "¡Saludos! Soy COLEPA, especializado en legislación paraguaya. ¿Cómo puedo ayudarte con tus consultas legales?",
                "¡Hola! Todo muy bien por aquí. Soy COLEPA, tu asistente legal. ¿En qué tema legal te puedo ayudar?"
            ],
            
            TipoConsulta.DESPEDIDA: [
                "¡Hasta luego! Que tengas un excelente día. Recuerda que siempre estoy aquí para tus consultas legales. 🇵🇾",
                "¡Nos vemos! Fue un gusto ayudarte. No dudes en volver cuando tengas dudas legales.",
                "¡Chau! Espero haber sido de ayuda. Que todo te vaya muy bien.",
                "¡Adiós! Siempre estaré disponible para tus consultas sobre la legislación paraguaya.",
                "¡Hasta otra! Que tengas un buen día y recuerda que estoy disponible 24/7 para temas legales."
            ],
            
            TipoConsulta.AGRADECIMIENTO: [
                "¡De nada! Me alegra haber podido ayudarte. ¿Hay algo más en lo que pueda asistirte?",
                "¡Un placer! Para eso estoy, para ayudarte con tus consultas legales. ¿Necesitas algo más?",
                "¡Con gusto! Si tienes más dudas legales, no dudes en preguntarme.",
                "¡Perfecto! Me da mucha satisfacción ser útil. ¿Alguna otra consulta legal?",
                "¡Excelente! Me alegra que la información te haya sido útil. ¿Algo más que pueda ayudarte?"
            ],
            
            TipoConsulta.TEMA_NO_LEGAL: [
                "Disculpa, pero me especializo únicamente en consultas sobre las leyes y normativas de Paraguay. ¿Hay alguna pregunta legal en la que pueda asistirte?",
                "Mi área de expertise son las leyes paraguayas. Para ese tipo de consultas, te recomiendo buscar especialistas en el tema. ¿Tienes alguna consulta legal que pueda resolver?",
                "Solo manejo temas legales de Paraguay. ¿Hay alguna normativa o ley sobre la que quieras consultar?",
                "Me especializo únicamente en legislación paraguaya. ¿En qué aspecto legal puedo ayudarte?",
                "No puedo ayudarte con ese tema, pero soy experto en leyes paraguayas. ¿Alguna consulta legal?"
            ]
        }
    
    def clasificar_consulta(self, texto: str) -> TipoConsulta:
        """
        Clasifica el tipo de consulta basado en patrones de texto
        """
        texto_lower = texto.lower().strip()
        
        # Log de la consulta original
        self.logger.info(f"🧠 Clasificando consulta: '{texto[:50]}...'")
        
        # Verificar en orden de prioridad
        for tipo_consulta in [
            TipoConsulta.SALUDO,
            TipoConsulta.DESPEDIDA, 
            TipoConsulta.AGRADECIMIENTO,
            TipoConsulta.CONSULTA_LEGAL,
            TipoConsulta.TEMA_NO_LEGAL
        ]:
            for patron in self.patrones.get(tipo_consulta, []):
                if re.search(patron, texto_lower):
                    self.logger.info(f"✅ Consulta clasificada como: {tipo_consulta.value} (patrón: {patron[:30]})")
                    return tipo_consulta
        
        # Si no coincide con ningún patrón específico
        # Para ser conservadores, asumimos que es consulta legal
        self.logger.info("⚠️ Consulta no clasificada específicamente, asumiendo: consulta_legal")
        return TipoConsulta.CONSULTA_LEGAL
    
    def generar_respuesta_directa(self, tipo_consulta: TipoConsulta) -> Optional[str]:
        """
        Genera respuesta directa para consultas conversacionales
        """
        if tipo_consulta in self.respuestas:
            respuesta = random.choice(self.respuestas[tipo_consulta])
            self.logger.info(f"💬 Respuesta conversacional generada para: {tipo_consulta.value}")
            return respuesta
        
        return None
    
    def requiere_busqueda_legal(self, tipo_consulta: TipoConsulta) -> bool:
        """
        Determina si necesita buscar en la base de datos legal
        """
        tipos_con_busqueda = {
            TipoConsulta.CONSULTA_LEGAL,
            TipoConsulta.CONVERSACION_GENERAL  # Por si acaso
        }
        
        return tipo_consulta in tipos_con_busqueda
    
    def procesar_consulta_completa(self, texto: str) -> Dict:
        """
        Procesamiento completo de la consulta
        
        Returns:
            Dict con: tipo, respuesta_directa, requiere_busqueda, metadata
        """
        tipo_consulta = self.clasificar_consulta(texto)
        respuesta_directa = self.generar_respuesta_directa(tipo_consulta)
        requiere_busqueda = self.requiere_busqueda_legal(tipo_consulta)
        
        resultado = {
            'tipo_consulta': tipo_consulta.value,
            'respuesta_directa': respuesta_directa,
            'requiere_busqueda': requiere_busqueda,
            'es_conversacional': respuesta_directa is not None,
            'metadata': {
                'timestamp': self._get_timestamp(),
                'confidence': self._calcular_confidence(texto, tipo_consulta)
            }
        }
        
        self.logger.info(f"📊 Procesamiento completo - Tipo: {tipo_consulta.value}, "
                        f"Conversacional: {resultado['es_conversacional']}, "
                        f"Buscar: {requiere_busqueda}")
        
        return resultado
    
    def _get_timestamp(self) -> str:
        """Timestamp para logging"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _calcular_confidence(self, texto: str, tipo: TipoConsulta) -> float:
        """
        Calcula nivel de confianza en la clasificación
        """
        texto_lower = texto.lower()
        matches = 0
        total_patrones = len(self.patrones.get(tipo, []))
        
        for patron in self.patrones.get(tipo, []):
            if re.search(patron, texto_lower):
                matches += 1
        
        if total_patrones == 0:
            return 0.5
        
        confidence = min(matches / total_patrones * 2, 1.0)  # Normalizar a 1.0
        return round(confidence, 2)

# Función helper para integración fácil
def clasificar_y_procesar(texto: str) -> Dict:
    """
    Función helper para usar en main.py
    
    Args:
        texto: Consulta del usuario
        
    Returns:
        Dict con información de clasificación y respuesta
    """
    clasificador = ClasificadorCOLEPA()
    return clasificador.procesar_consulta_completa(texto)
