# Archivo: app/prompt_builder.py - VERSION MEJORADA PARA COLEPA v4.0

from typing import Dict, List, Optional
import re

class COLEPAPromptBuilder:
    """
    Constructor de prompts inteligente para COLEPA con especialización jurídica paraguaya
    """
    
    def __init__(self):
        self.plantillas_especializadas = {
            'codigo_civil': self._plantilla_codigo_civil,
            'codigo_penal': self._plantilla_codigo_penal,
            'codigo_laboral': self._plantilla_codigo_laboral,
            'constitucion': self._plantilla_constitucion,
            'codigo_procesal': self._plantilla_codigo_procesal,
            'default': self._plantilla_general
        }
    
    def construir_prompt(self, 
                        contexto_legal: str, 
                        pregunta_usuario: str,
                        metadata: Optional[Dict] = None) -> str:
        """
        Construye un prompt optimizado según el tipo de consulta legal
        
        Args:
            contexto_legal: Texto legal extraído de la base vectorial
            pregunta_usuario: Consulta del usuario
            metadata: Información adicional (código, artículo, etc.)
        """
        
        # FILTRO LEGAL ESTRICTO - Validar que sea consulta legal
        if not self._es_consulta_legal_valida(pregunta_usuario, contexto_legal):
            return self._prompt_rechazo_no_legal()
        
        # Detectar tipo de consulta
        tipo_consulta = self._detectar_tipo_consulta(contexto_legal, pregunta_usuario, metadata)
        
        # Extraer elementos jurídicos
        elementos = self._extraer_elementos_juridicos(contexto_legal, metadata)
        
        # Seleccionar plantilla especializada
        constructor = self.plantillas_especializadas.get(tipo_consulta, self.plantillas_especializadas['default'])
        
        # Construir prompt optimizado para tokens
        return constructor(contexto_legal, pregunta_usuario, elementos)
    
    def _es_consulta_legal_valida(self, pregunta: str, contexto: str) -> bool:
        """
        Valida que la consulta sea del área legal paraguaya o internacional
        """
        pregunta_lower = pregunta.lower()
        contexto_lower = contexto.lower() if contexto else ""
        
        # Términos legales válidos - amplio pero específico
        terminos_legales = [
            # Derecho general
            'artículo', 'articulo', 'ley', 'código', 'decreto', 'resolución',
            'derecho', 'legal', 'jurídico', 'norma', 'normativa', 'disposición',
            'constitución', 'constitucion', 'reglamento', 'ordenanza',
            
            # Instituciones jurídicas
            'contrato', 'obligación', 'delito', 'proceso', 'juicio', 'demanda',
            'matrimonio', 'divorcio', 'herencia', 'testamento', 'propiedad',
            'trabajo', 'empleado', 'salario', 'despido', 'indemnización',
            'penal', 'civil', 'laboral', 'procesal', 'administrativo',
            
            # Específicos Paraguay
            'paraguay', 'paraguayo', 'paraguaya', 'guaraní', 'congreso nacional',
            'corte suprema', 'ministerio público', 'defensoría',
            
            # Derecho internacional
            'tratado', 'convenio internacional', 'mercosur', 'unasur',
            'derechos humanos', 'derecho internacional'
        ]
        
        # Si hay contexto legal, es válida
        if contexto and any(term in contexto_lower for term in terminos_legales):
            return True
            
        # Validar pregunta contiene términos legales
        if any(term in pregunta_lower for term in terminos_legales):
            return True
            
        # Rechazar consultas claramente no legales
        terminos_no_legales = [
            'receta', 'cocina', 'comida', 'deporte', 'fútbol', 'música',
            'película', 'juego', 'videojuego', 'programación', 'código python',
            'matemática', 'física', 'química', 'biología', 'medicina',
            'historia', 'geografía', 'literatura', 'poesía', 'novela',
            'clima', 'tiempo', 'turismo', 'viaje', 'hotel', 'restaurante'
        ]
        
        if any(term in pregunta_lower for term in terminos_no_legales):
            return False
            
        return True  # En caso de duda, permitir (el contexto legal decidirá)
    
    def _prompt_rechazo_no_legal(self) -> str:
        """
        Prompt para rechazar consultas no legales
        """
        return """Eres COLEPA, asistente legal especializado exclusivamente en legislación paraguaya.

INSTRUCCIONES ESTRICTAS:
Responde ÚNICAMENTE: "COLEPA está especializado exclusivamente en legislación paraguaya y normas internacionales aplicables en Paraguay. Para consultas sobre otros temas, por favor contacte un especialista apropiado."

NO RESPONDAS NADA MÁS. NO EXPLIQUES. NO AGREGUES INFORMACIÓN.

Responde:"""
        """Detecta el tipo de consulta para usar la plantilla apropiada"""
        
        if metadata and 'codigo' in metadata:
            codigo = metadata['codigo'].lower()
            if 'civil' in codigo:
                return 'codigo_civil'
            elif 'penal' in codigo:
                return 'codigo_penal'
            elif 'laboral' in codigo or 'trabajo' in codigo:
                return 'codigo_laboral'
            elif 'procesal' in codigo:
                return 'codigo_procesal'
            elif 'constitucion' in codigo:
                return 'constitucion'
        
        # Detección por contenido
        texto_completo = f"{contexto} {pregunta}".lower()
        
        if any(term in texto_completo for term in ['delito', 'pena', 'sanción', 'penal']):
            return 'codigo_penal'
        elif any(term in texto_completo for term in ['contrato', 'obligación', 'civil', 'patrimonio']):
            return 'codigo_civil'
        elif any(term in texto_completo for term in ['trabajo', 'empleado', 'salario', 'laboral']):
            return 'codigo_laboral'
        elif any(term in texto_completo for term in ['proceso', 'juicio', 'demanda', 'procesal']):
            return 'codigo_procesal'
        elif any(term in texto_completo for term in ['constitución', 'derecho fundamental']):
            return 'constitucion'
            
        return 'default'
    
    def _extraer_elementos_juridicos(self, contexto: str, metadata: Optional[Dict]) -> Dict:
        """Extrae elementos jurídicos relevantes del contexto"""
        
        elementos = {
            'articulos': self._extraer_numeros_articulo(contexto),
            'codigo_fuente': metadata.get('codigo', 'Legislación Paraguaya') if metadata else 'Legislación Paraguaya',
            'tiene_sanciones': 'sanción' in contexto.lower() or 'pena' in contexto.lower(),
            'tiene_procedimientos': any(term in contexto.lower() for term in ['procedimiento', 'trámite', 'proceso']),
            'es_definicion': 'se entiende por' in contexto.lower() or 'definición' in contexto.lower()
        }
        
        return elementos
    
    def _extraer_numeros_articulo(self, contexto: str) -> List[str]:
        """Extrae números de artículos mencionados"""
        patron = r'[Aa]rt(?:ículo|iculo)?\s*(\d+)'
        matches = re.findall(patron, contexto)
        return matches
    
    def _plantilla_general(self, contexto_legal: str, pregunta_usuario: str, elementos: Dict) -> str:
        """Plantilla general optimizada para tokens"""
        
        return f"""Eres COLEPA, asistente legal paraguayo. SOLO usa información de tu base de datos legal.

NORMATIVA DISPONIBLE EN BASE DE DATOS:
{contexto_legal}

CONSULTA:
{pregunta_usuario}

INSTRUCCIONES ESTRICTAS:
1. USA ÚNICAMENTE la información proporcionada arriba
2. NO inventes ni agregues información externa
3. Si no tienes el texto específico, di: "No tengo esa información en mi base de datos"
4. Respuesta técnica y concisa
5. Si no es tema legal: "COLEPA solo responde consultas de legislación paraguaya"

FORMATO OBLIGATORIO:

**ANÁLISIS:**
[Explicación técnica SOLO basada en el texto proporcionado - máximo 3 líneas]

**FUNDAMENTO LEGAL:**
{elementos['codigo_fuente']}
[COPIA EXACTA del texto legal proporcionado arriba]

Responde usando SOLO la información de tu base de datos:"""

    def _plantilla_codigo_civil(self, contexto_legal: str, pregunta_usuario: str, elementos: Dict) -> str:
        """Plantilla civil optimizada"""
        
        return f"""COLEPA - Derecho Civil Paraguayo. SOLO usa tu base de datos legal.

TEXTO DISPONIBLE EN BASE DE DATOS:
{contexto_legal}

CONSULTA:
{pregunta_usuario}

INSTRUCCIONES: USA ÚNICAMENTE el texto proporcionado arriba. NO inventes.

**ANÁLISIS CIVIL:**
[Institución jurídica, elementos, efectos SOLO del texto arriba - máximo 3 líneas]

**FUNDAMENTO:**
Código Civil Paraguayo
[COPIA EXACTA del texto proporcionado]

Responde SOLO con información de tu base de datos:"""

    def _plantilla_codigo_penal(self, contexto_legal: str, pregunta_usuario: str, elementos: Dict) -> str:
        """Plantilla penal optimizada"""
        
        return f"""COLEPA - Derecho Penal Paraguayo. SOLO usa tu base de datos legal.

TEXTO DISPONIBLE EN BASE DE DATOS:
{contexto_legal}

CONSULTA:
{pregunta_usuario}

INSTRUCCIONES: USA ÚNICAMENTE el texto proporcionado arriba. NO inventes.

**ANÁLISIS PENAL:**
[Tipo objetivo/subjetivo, bien jurídico, sanción SOLO del texto arriba - máximo 3 líneas]

**FUNDAMENTO:**
Código Penal Paraguayo
[COPIA EXACTA del texto proporcionado]

Responde SOLO con información de tu base de datos:"""

    def _plantilla_codigo_laboral(self, contexto_legal: str, pregunta_usuario: str, elementos: Dict) -> str:
        """Plantilla laboral optimizada"""
        
        return f"""COLEPA - Derecho Laboral Paraguayo. SOLO usa tu base de datos legal.

TEXTO DISPONIBLE EN BASE DE DATOS:
{contexto_legal}

CONSULTA:
{pregunta_usuario}

INSTRUCCIONES: USA ÚNICAMENTE el texto proporcionado arriba. NO inventes.

**ANÁLISIS LABORAL:**
[Derechos/obligaciones, principio protectorio SOLO del texto arriba - máximo 3 líneas]

**FUNDAMENTO:**
Código Laboral Paraguayo
[COPIA EXACTA del texto proporcionado]

Responde SOLO con información de tu base de datos:"""

    def _plantilla_constitucion(self, contexto_legal: str, pregunta_usuario: str, elementos: Dict) -> str:
        """Plantilla constitucional optimizada"""
        
        return f"""COLEPA - Derecho Constitucional Paraguayo. SOLO usa tu base de datos legal.

TEXTO DISPONIBLE EN BASE DE DATOS:
{contexto_legal}

CONSULTA:
{pregunta_usuario}

INSTRUCCIONES: USA ÚNICAMENTE el texto proporcionado arriba. NO inventes.

**ANÁLISIS CONSTITUCIONAL:**
[Derecho fundamental/principio, alcance, garantías SOLO del texto arriba - máximo 3 líneas]

**FUNDAMENTO:**
Constitución Nacional del Paraguay
[COPIA EXACTA del texto proporcionado]

Responde SOLO con información de tu base de datos:"""

    def _plantilla_codigo_procesal(self, contexto_legal: str, pregunta_usuario: str, elementos: Dict) -> str:
        """Plantilla procesal optimizada"""
        
        return f"""COLEPA - Derecho Procesal Paraguayo. SOLO usa tu base de datos legal.

TEXTO DISPONIBLE EN BASE DE DATOS:
{contexto_legal}

CONSULTA:
{pregunta_usuario}

INSTRUCCIONES: USA ÚNICAMENTE el texto proporcionado arriba. NO inventes.

**ANÁLISIS PROCESAL:**
[Acto procesal, requisitos, plazos, efectos SOLO del texto arriba - máximo 3 líneas]

**FUNDAMENTO:**
{elementos['codigo_fuente']}
[COPIA EXACTA del texto proporcionado]

Responde SOLO con información de tu base de datos:"""


# Función de compatibilidad con el sistema actual
def construir_prompt(contexto_legal: str, pregunta_usuario: str, metadata: Optional[Dict] = None) -> str:
    """
    Función wrapper para mantener compatibilidad con el sistema actual
    """
    builder = COLEPAPromptBuilder()
    return builder.construir_prompt(contexto_legal, pregunta_usuario, metadata)
