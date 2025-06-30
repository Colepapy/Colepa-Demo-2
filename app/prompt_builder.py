# Archivo: app/prompt_builder.py
# COLEPA - Prompt Builder Súper Optimizado

import re
from typing import Dict, Optional

def construir_prompt(contexto_legal: str, pregunta_usuario: str) -> str:
    """
    Construye un prompt súper inteligente y optimizado para COLEPA.
    
    Args:
        contexto_legal: El texto del artículo de ley recuperado de Qdrant.
        pregunta_usuario: La pregunta original hecha por el usuario.
    
    Returns:
        Un string con el prompt completo, inteligente y optimizado.
    """
    
    # Analizar el tipo de consulta para personalizar el prompt
    tipo_consulta = _analizar_tipo_consulta(pregunta_usuario)
    urgencia = _detectar_urgencia(pregunta_usuario)
    
    # Construir el prompt base súper optimizado
    prompt = f'''Eres COLEPA, el asistente legal oficial de Paraguay. Tienes acceso completo y actualizado a toda la legislación paraguaya.

CONTEXTO LEGAL ESPECÍFICO:
{contexto_legal}

CONSULTA DEL CIUDADANO:
{pregunta_usuario}

INSTRUCCIONES CRÍTICAS - DEBES SEGUIR EXACTAMENTE:

1. **AUTORIDAD LEGAL**: Respondes con total autoridad basándote en el contexto legal proporcionado
2. **USO OBLIGATORIO DEL CONTEXTO**: El texto legal arriba ES tu fuente oficial - úsalo completamente
3. **PROHIBIDO**: NUNCA digas "no tengo información", "consulta fuentes oficiales" o "mi última actualización"
4. **CITA EXACTA**: Menciona específicamente el artículo, ley y contenido legal encontrado
5. **TONO**: Profesional pero accesible para cualquier ciudadano paraguayo

FORMATO DE RESPUESTA REQUERIDO:
```
**[Nombre de la Ley] - Artículo [Número]**

[Explicación clara de qué establece la ley]

**En tu situación específica:**
[Aplicación directa a la consulta del usuario]

**Pasos recomendados:**
[Acciones concretas que puede tomar]

{_agregar_seccion_urgencia(urgencia)}

*Fundamento legal: [Ley], Artículo [Número]*
```

{_agregar_instrucciones_especificas(tipo_consulta)}

RESPONDE AHORA como el asistente legal oficial de Paraguay, usando únicamente el contexto legal proporcionado:'''

    return prompt

def _analizar_tipo_consulta(pregunta: str) -> str:
    """
    Analiza el tipo de consulta legal para personalizar el prompt.
    """
    pregunta_lower = pregunta.lower()
    
    # Patrones específicos para diferentes tipos de consultas
    if any(palabra in pregunta_lower for palabra in ["pega", "golpea", "maltrato", "violencia", "abuso"]):
        return "violencia_domestica"
    elif any(palabra in pregunta_lower for palabra in ["choque", "chocaron", "atropello", "accidente"]):
        return "accidente_transito"
    elif any(palabra in pregunta_lower for palabra in ["acoso", "persigue", "molesta", "hostiga"]):
        return "acoso"
    elif any(palabra in pregunta_lower for palabra in ["trabajo", "despido", "salario", "jefe"]):
        return "laboral"
    elif any(palabra in pregunta_lower for palabra in ["divorcio", "matrimonio", "esposo", "esposa"]):
        return "familia"
    elif any(palabra in pregunta_lower for palabra in ["menor", "niño", "hijo", "adolescente"]):
        return "menores"
    elif any(palabra in pregunta_lower for palabra in ["artículo", "art", "código"]):
        return "consulta_especifica"
    else:
        return "general"

def _detectar_urgencia(pregunta: str) -> bool:
    """
    Detecta si la consulta requiere atención urgente.
    """
    pregunta_lower = pregunta.lower()
    palabras_urgentes = [
        "urgente", "ahora", "inmediato", "hoy", "emergencia", 
        "peligro", "amenaza", "me pega", "me golpea", "violencia",
        "me está", "está pasando", "sucediendo", "policía"
    ]
    
    return any(palabra in pregunta_lower for palabra in palabras_urgentes)

def _agregar_seccion_urgencia(es_urgente: bool) -> str:
    """
    Agrega sección de urgencia si es necesario.
    """
    if es_urgente:
        return '''
**🚨 ATENCIÓN INMEDIATA:**
- En emergencias, llame al 911
- Para violencia doméstica: línea 137 (24 horas)
- Puede acudir a cualquier comisaría para hacer denuncia inmediata
'''
    return ""

def _agregar_instrucciones_especificas(tipo_consulta: str) -> str:
    """
    Agrega instrucciones específicas según el tipo de consulta.
    """
    instrucciones_especificas = {
        "violencia_domestica": """
INSTRUCCIÓN ESPECIAL - VIOLENCIA DOMÉSTICA:
- Prioriza información sobre protección inmediata y denuncia
- Menciona específicamente los derechos de la víctima
- Incluye información sobre medidas de protección disponibles
- Enfatiza que la violencia doméstica es un delito grave
""",
        
        "accidente_transito": """
INSTRUCCIÓN ESPECIAL - ACCIDENTES DE TRÁNSITO:
- Explica tanto la responsabilidad penal como civil
- Menciona los derechos de las víctimas
- Incluye información sobre seguros obligatorios si aplica
- Explica el procedimiento para reclamación de daños
""",
        
        "acoso": """
INSTRUCCIÓN ESPECIAL - ACOSO:
- Define claramente qué constituye acoso según la ley
- Explica las sanciones penales aplicables
- Menciona cómo documentar y denunciar el acoso
- Incluye información sobre medidas de protección
""",
        
        "laboral": """
INSTRUCCIÓN ESPECIAL - DERECHO LABORAL:
- Explica tanto los derechos del trabajador como las obligaciones del empleador
- Menciona procedimientos ante el Ministerio de Trabajo si aplica
- Incluye información sobre indemnizaciones o compensaciones
- Explica plazos legales importantes
""",
        
        "familia": """
INSTRUCCIÓN ESPECIAL - DERECHO DE FAMILIA:
- Explica procedimientos judiciales necesarios
- Menciona derechos y obligaciones de ambas partes
- Incluye información sobre bienes, hijos y alimentos si aplica
- Explica plazos y requisitos legales
""",
        
        "menores": """
INSTRUCCIÓN ESPECIAL - DERECHOS DE MENORES:
- Prioriza el interés superior del menor
- Explica procedimientos de protección integral
- Menciona instituciones especializadas (SNNA, Consejerías)
- Incluye información sobre derechos fundamentales del menor
""",
        
        "consulta_especifica": """
INSTRUCCIÓN ESPECIAL - CONSULTA DE ARTÍCULO ESPECÍFICO:
- Cita textualmente el artículo encontrado
- Explica el significado en términos comprensibles
- Proporciona ejemplos prácticos de aplicación
- Menciona artículos relacionados si es relevante
""",
        
        "general": """
INSTRUCCIÓN ESPECIAL - CONSULTA GENERAL:
- Proporciona una explicación completa y didáctica
- Usa ejemplos prácticos para clarificar conceptos
- Menciona pasos concretos que el ciudadano puede seguir
- Incluye referencias a instituciones relevantes
"""
    }
    
    return instrucciones_especificas.get(tipo_consulta, instrucciones_especificas["general"])

def construir_prompt_sin_contexto(pregunta_usuario: str) -> str:
    """
    Construye un prompt cuando no hay contexto legal específico disponible.
    
    Args:
        pregunta_usuario: La pregunta original hecha por el usuario.
    
    Returns:
        Un prompt optimizado para casos sin contexto específico.
    """
    
    tipo_consulta = _analizar_tipo_consulta(pregunta_usuario)
    urgencia = _detectar_urgencia(pregunta_usuario)
    
    prompt = f'''Eres COLEPA, el asistente legal oficial de Paraguay.

SITUACIÓN: No se encontró un artículo específico para esta consulta en la base de datos legal.

CONSULTA DEL CIUDADANO:
{pregunta_usuario}

INSTRUCCIONES:
1. Reconoce que no encontraste información específica para esa consulta
2. Proporciona orientación general sobre el tema si puedes
3. Sugiere reformular la consulta con términos más específicos
4. Recomienda instituciones o profesionales relevantes

{_agregar_seccion_urgencia(urgencia)}

FORMATO DE RESPUESTA:
```
**Consulta Legal - {tipo_consulta.replace('_', ' ').title()}**

No encontré esa disposición específica en mi consulta de la base legal.

**Orientación general:**
[Información general sobre el tema si es posible]

**Para obtener respuesta específica:**
- Reformule su consulta con términos más específicos
- Mencione el código o ley específica si la conoce
- Use números de artículo si busca disposiciones particulares

**Instituciones relevantes:**
[Lista de instituciones donde puede obtener ayuda]

*Para asesoramiento personalizado, consulte siempre con un abogado especializado.*
```

RESPONDE AHORA:'''

    return prompt

def validar_contexto_legal(contexto_legal: str) -> bool:
    """
    Valida que el contexto legal proporcionado sea válido y útil.
    
    Args:
        contexto_legal: El texto del contexto legal a validar.
    
    Returns:
        True si el contexto es válido, False en caso contrario.
    """
    if not contexto_legal or len(contexto_legal.strip()) < 20:
        return False
    
    # Verificar que contiene elementos típicos de un artículo legal
    indicadores_legales = [
        "artículo", "ley", "código", "disposición", "establecer", "determina",
        "sanciona", "procedimiento", "derecho", "obligación", "prohibir"
    ]
    
    contexto_lower = contexto_legal.lower()
    return any(indicador in contexto_lower for indicador in indicadores_legales)

def extraer_metadatos_contexto(contexto_legal: str) -> Dict[str, Optional[str]]:
    """
    Extrae metadatos útiles del contexto legal para mejorar la respuesta.
    
    Args:
        contexto_legal: El texto del contexto legal.
    
    Returns:
        Diccionario con metadatos extraídos.
    """
    metadatos = {
        "numero_articulo": None,
        "tipo_norma": None,
        "tema_principal": None
    }
    
    # Extraer número de artículo
    match_articulo = re.search(r'art[ií]culo\s*(\d+)', contexto_legal, re.IGNORECASE)
    if match_articulo:
        metadatos["numero_articulo"] = match_articulo.group(1)
    
    # Determinar tipo de norma
    contexto_lower = contexto_legal.lower()
    if "código civil" in contexto_lower:
        metadatos["tipo_norma"] = "civil"
    elif "código penal" in contexto_lower:
        metadatos["tipo_norma"] = "penal"
    elif "código laboral" in contexto_lower:
        metadatos["tipo_norma"] = "laboral"
    
    # Determinar tema principal
    if any(palabra in contexto_lower for palabra in ["matrimonio", "divorcio", "familia"]):
        metadatos["tema_principal"] = "familia"
    elif any(palabra in contexto_lower for palabra in ["delito", "pena", "prisión"]):
        metadatos["tema_principal"] = "penal"
    elif any(palabra in contexto_lower for palabra in ["trabajo", "empleado", "salario"]):
        metadatos["tema_principal"] = "laboral"
    
    return metadatos
