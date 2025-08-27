# Archivo: app/prompt_builder.py - COLEPA CHATGPT LEGAL PARAGUAYO

from typing import Dict, List, Optional
import re

class COLEPAPromptBuilder:
    """
    Constructor de prompts para COLEPA - ChatGPT especializado en leyes paraguayas
    Conversacional, amigable, pero estrictamente limitado al área legal
    """
    
    def __init__(self):
        self.plantillas_especializadas = {
            'consulta_especifica': self._plantilla_consulta_especifica,
            'conversacional': self._plantilla_conversacional,
            'rechazo_no_legal': self._plantilla_rechazo_no_legal
        }
    
    def construir_prompt(self, 
                        contexto_legal: str, 
                        pregunta_usuario: str,
                        metadata: Optional[Dict] = None) -> str:
        """
        Construye prompt para COLEPA como ChatGPT legal paraguayo
        
        Args:
            contexto_legal: Texto legal del Qdrant (puede estar vacío para chat general)
            pregunta_usuario: Pregunta del usuario
            metadata: Info adicional del sistema
        """
        
        # Determinar tipo de interacción
        tipo_interaccion = self._determinar_tipo_interaccion(
            pregunta_usuario, contexto_legal, metadata
        )
        
        # Generar prompt según el tipo
        constructor = self.plantillas_especializadas[tipo_interaccion]
        return constructor(contexto_legal, pregunta_usuario, metadata)
    
    def _determinar_tipo_interaccion(self, pregunta: str, contexto: str, metadata: Optional[Dict]) -> str:
        """
        Determina si es consulta específica, conversacional o rechazo
        """
        pregunta_lower = pregunta.lower()
        
        # Si hay contexto del Qdrant, es consulta específica
        if contexto and contexto.strip():
            return 'consulta_especifica'
        
        # Si no es tema legal, rechazo
        if not self._es_tema_legal(pregunta):
            return 'rechazo_no_legal'
        
        # Si es tema legal pero sin contexto específico, conversacional
        return 'conversacional'
    
    def _es_tema_legal(self, pregunta: str) -> bool:
        """Valida si la pregunta es del ámbito legal paraguayo"""
        pregunta_lower = pregunta.lower()
        
        # Saludos y conversación general - PERMITIR
        saludos = ['hola', 'buenos días', 'buenas tardes', 'buenas noches', 'hey', 'qué tal', 'como estas']
        if any(saludo in pregunta_lower for saludo in saludos):
            return True
        
        # Términos legales - PERMITIR
        terminos_legales = [
            'artículo', 'articulo', 'ley', 'código', 'codigo', 'decreto', 'resolución',
            'derecho', 'legal', 'jurídico', 'norma', 'normativa', 'disposición',
            'constitución', 'constitucion', 'reglamento', 'ordenanza', 'sentencia',
            'contrato', 'obligación', 'delito', 'proceso', 'juicio', 'demanda',
            'matrimonio', 'divorcio', 'herencia', 'testamento', 'propiedad',
            'trabajo', 'empleado', 'salario', 'despido', 'indemnización',
            'penal', 'civil', 'laboral', 'procesal', 'administrativo', 'comercial',
            'paraguay', 'paraguayo', 'paraguaya', 'guaraní', 'congreso nacional',
            'corte suprema', 'ministerio público', 'defensoría', 'abogado',
            'tratado', 'convenio', 'mercosur', 'derechos humanos', 'aduanero'
        ]
        
        if any(term in pregunta_lower for term in terminos_legales):
            return True
        
        # Preguntas sobre COLEPA - PERMITIR
        if 'colepa' in pregunta_lower or 'qué puedes hacer' in pregunta_lower:
            return True
        
        # Rechazar temas claramente no legales
        terminos_no_legales = [
            'receta', 'cocina', 'comida', 'deporte', 'fútbol', 'música',
            'película', 'juego', 'videojuego', 'programación', 'python',
            'matemática', 'física', 'química', 'biología', 'medicina',
            'clima', 'tiempo', 'turismo', 'viaje', 'hotel'
        ]
        
        if any(term in pregunta_lower for term in terminos_no_legales):
            return False
            
        return True  # En caso de duda, permitir
    
    def _plantilla_consulta_especifica(self, contexto_legal: str, pregunta_usuario: str, metadata: Optional[Dict]) -> str:
        """Plantilla para consultas con información específica del Qdrant"""
        
        codigo_fuente = metadata.get('codigo', 'Legislación Paraguaya') if metadata else 'Legislación Paraguaya'
        
        return f"""Eres COLEPA, un asistente de IA especializado en legislación paraguaya. Tienes personalidad amigable y conversacional, pero te limitas estrictamente al área legal paraguaya.

INFORMACIÓN LEGAL DISPONIBLE EN TU BASE DE DATOS:
{contexto_legal}

CONSULTA DEL USUARIO:
{pregunta_usuario}

PERSONALIDAD Y COMPORTAMIENTO:
- Eres amigable, profesional y conversacional como ChatGPT
- Tienes conocimiento especializado en leyes paraguayas
- Explains conceptos legales de manera clara y accesible
- Mantienes un tono profesional pero cercano
- SOLO usas información de tu base de datos para cuestiones jurídicas específicas

INSTRUCCIONES PARA RESPONDER:
1. Responde de manera conversacional y amigable
2. Explica brevemente qué establece la norma consultada
3. Proporciona el texto legal exacto de tu base de datos
4. Puedes agregar contexto legal general si es relevante
5. Si te preguntan algo fuera del área legal, redirige amablemente

FORMATO DE RESPUESTA:

[Respuesta conversacional introduciendo el tema]

**Explicación:**
[Explicación clara y accesible de qué establece la norma - 2-3 líneas máximo]

**Texto legal exacto:**
{codigo_fuente}
[Copia textual exacta de la información de tu base de datos]

[Cierre conversacional, pregunta si necesita más información o aclaraciones]

Responde de manera amigable y profesional:"""

    def _plantilla_conversacional(self, contexto_legal: str, pregunta_usuario: str, metadata: Optional[Dict]) -> str:
        """Plantilla para conversación general sobre temas legales sin contexto específico"""
        
        return f"""Eres COLEPA, un asistente de IA especializado en legislación paraguaya. Tienes personalidad amigable y conversacional como ChatGPT.

CONSULTA DEL USUARIO:
{pregunta_usuario}

PERSONALIDAD Y COMPORTAMIENTO:
- Eres amigable, profesional y conversacional
- Te especializas exclusivamente en legislación paraguaya e internacional aplicable en Paraguay
- Tienes amplio conocimiento legal pero solo respondes sobre derecho paraguayo
- Mantienes conversaciones naturales sobre temas legales
- Puedes saludar, despedirte y mantener conversación amigable
- Explains conceptos legales de manera clara y accesible

INSTRUCCIONES PARA ESTA RESPUESTA:
1. Responde de manera conversacional y natural
2. Si es un saludo, responde amigablemente y ofrece ayuda legal
3. Si preguntan qué puedes hacer, explica que eres experto en leyes paraguayas
4. Para consultas legales generales, da información general pero sugiere consultas específicas
5. Mantén el foco en legislación paraguaya siempre
6. Si no tienes información específica, sé honesto pero mantente conversacional

EJEMPLO DE RESPUESTA:
- Para saludos: "¡Hola! Soy COLEPA, tu asistente especializado en legislación paraguaya. ¿En qué tema legal puedo ayudarte hoy?"
- Para preguntas generales: Responde conversacionalmente pero enfocándote en derecho paraguayo

Responde de manera amigable y conversacional:"""

    def _plantilla_rechazo_no_legal(self, contexto_legal: str, pregunta_usuario: str, metadata: Optional[Dict]) -> str:
        """Plantilla para rechazar consultas no legales de manera amigable"""
        
        return f"""Eres COLEPA, un asistente de IA especializado exclusivamente en legislación paraguaya.

CONSULTA DEL USUARIO:
{pregunta_usuario}

INSTRUCCIONES:
El usuario preguntó sobre algo que NO es del área legal. Responde de manera amigable pero firme que solo te especializas en legislación paraguaya.

RESPUESTA REQUERIDA:
Responde de manera conversacional y amigable, algo como:
"¡Hola! Me especializo exclusivamente en legislación paraguaya y normas internacionales aplicables en Paraguay. Para consultas sobre [tema que preguntó], te recomiendo buscar un especialista en esa área. 

¿Hay algún tema legal paraguayo en el que pueda ayudarte? Puedo explicarte sobre códigos, leyes, decretos, procedimientos legales, derechos y todo lo relacionado con el sistema jurídico paraguayo."

Mantén un tono amigable pero redirige hacia temas legales:"""


# Función de compatibilidad con el sistema actual
def construir_prompt(contexto_legal: str, pregunta_usuario: str, metadata: Optional[Dict] = None) -> str:
    """
    Función wrapper para mantener compatibilidad con el sistema actual
    """
    builder = COLEPAPromptBuilder()
    return builder.construir_prompt(contexto_legal, pregunta_usuario, metadata)
