# Archivo: app/prompt_builder.py - VERSIÓN SINCRONIZADA CON SISTEMA ESTRUCTURADO
# COLEPA - Prompt Builder Optimizado para Respuestas Estructuradas

import re
from typing import Dict, Optional

def construir_prompt(contexto_legal: str, pregunta_usuario: str) -> str:
    """
    Construye un prompt SINCRONIZADO con el sistema de respuestas estructuradas.
    Compatible con main.py mejorado y frontend sincronizado.
    
    Args:
        contexto_legal: El texto del artículo de ley recuperado de Qdrant.
        pregunta_usuario: La pregunta original hecha por el usuario.
    
    Returns:
        Un string con el prompt optimizado para respuestas estructuradas.
    """
    
    # Análisis de la consulta
    es_emergencia = _detectar_emergencia_critica(pregunta_usuario)
    necesita_pasos = _usuario_pide_procedimientos(pregunta_usuario)
    busca_articulo_especifico = _busca_articulo_especifico(pregunta_usuario)
    metadatos = extraer_metadatos_contexto(contexto_legal)
    
    # Construir prompt sincronizado con INSTRUCCION_SISTEMA_LEGAL del main.py
    prompt = f'''Eres COLEPA, el asistente legal oficial especializado en legislación paraguaya. Tienes acceso completo y autorizado a toda la legislación vigente del Paraguay.

CONTEXTO LEGAL ESPECÍFICO:
{contexto_legal}

CONSULTA DEL USUARIO:
{pregunta_usuario}

INSTRUCCIONES PARA RESPUESTA ESTRUCTURADA:

ESTRUCTURA OBLIGATORIA (igual al main.py):

1. **RESPUESTA DIRECTA INICIAL** (2-3 líneas máximo)
   - Responde la pregunta del usuario de forma directa y precisa
   - Da la información práctica que necesita saber INMEDIATAMENTE
   - Evita jerga legal innecesaria

2. **FUNDAMENTO LEGAL** (después de la respuesta directa)
   - Cita la ley y artículo específico del contexto proporcionado
   - Si es útil, reproduce fragmentos del texto legal exacto
   - Explica cómo se aplica específicamente a la situación del usuario

3. **ORIENTACIÓN PRÁCTICA** (si aplica)
   - Pasos concretos y específicos que puede seguir
   - Dónde acudir o qué hacer en términos prácticos
   - Precauciones o consideraciones importantes

{_agregar_instrucciones_emergencia(es_emergencia)}

{_agregar_instrucciones_articulo_especifico(busca_articulo_especifico, metadatos)}

{_agregar_instrucciones_pasos(necesita_pasos)}

REGLAS CRÍTICAS ESPECÍFICAS:
✅ SIEMPRE usar el contexto legal proporcionado como base autoritativa
✅ Citar específicamente la ley y artículo del contexto
✅ Mantener el tono profesional pero accesible
✅ Responder PRIMERO, fundamentar DESPUÉS
✅ Ser específico sobre procedimientos paraguayos

❌ NUNCA inventar información no contenida en el contexto
❌ NUNCA hacer disclaimers sobre fechas de actualización
❌ NUNCA ser vago o genérico en la respuesta
❌ NUNCA solo "escupir" el texto del artículo sin explicar

GENERAR RESPUESTA ESTRUCTURADA AHORA:'''

    return prompt

def _detectar_emergencia_critica(pregunta: str) -> bool:
    """
    Detecta casos de emergencia que requieren mencionar línea 137 INMEDIATAMENTE.
    Sincronizado con la detección del main.py y script.js
    """
    pregunta_lower = pregunta.lower()
    palabras_emergencia = [
        "me pega", "me golpea", "me maltrata", "me agrede",
        "violencia doméstica", "violencia", "maltrato", "agresión",
        "me amenaza", "tengo miedo", "abuso", "golpes",
        "femicidio", "peligro", "urgente", "emergencia"
    ]
    
    return any(palabra in pregunta_lower for palabra in palabras_emergencia)

def _usuario_pide_procedimientos(pregunta: str) -> bool:
    """
    Detecta si el usuario pregunta específicamente qué hacer o pasos a seguir.
    Mejorado para mayor precisión.
    """
    pregunta_lower = pregunta.lower()
    indicadores_pasos = [
        "qué hacer", "que hacer", "qué hago", "que hago",
        "cómo proceder", "como proceder", "qué pasos", "que pasos",
        "cómo tramitar", "como tramitar", "qué debo hacer", "que debo hacer",
        "cuáles son los pasos", "cuales son los pasos",
        "cómo denunciar", "como denunciar", "dónde acudir", "donde acudir",
        "qué requisitos", "que requisitos", "cómo hacer", "como hacer",
        "procedimiento", "trámite", "trámites", "gestión"
    ]
    
    return any(indicador in pregunta_lower for indicador in indicadores_pasos)

def _busca_articulo_especifico(pregunta: str) -> bool:
    """
    Detecta si el usuario busca información sobre un artículo específico por número.
    """
    pregunta_lower = pregunta.lower()
    patrones_articulo = [
        r'art[ií]culo\s*(\d+)',
        r'art\.?\s*(\d+)',
        r'artículo\s*(\d+)',
        r'articulo\s*(\d+)'
    ]
    
    return any(re.search(patron, pregunta_lower) for patron in patrones_articulo)

def _agregar_instrucciones_emergencia(es_emergencia: bool) -> str:
    """
    Agrega instrucciones específicas para casos de emergencia.
    Sincronizado con el frontend para destacar línea 137.
    """
    if es_emergencia:
        return '''
CASO DE EMERGENCIA DETECTADO:
⚠️ PRIORIDAD MÁXIMA: Incluir información de línea 137 EN LA RESPUESTA DIRECTA INICIAL
⚠️ Mencionar "línea 137" explícitamente para activar el destacado visual
⚠️ Dar información de protección ANTES del fundamento legal
⚠️ Ser directo sobre pasos inmediatos de protección
'''
    return ""

def _agregar_instrucciones_articulo_especifico(busca_articulo: bool, metadatos: Dict) -> str:
    """
    Agrega instrucciones para consultas sobre artículos específicos.
    """
    if busca_articulo:
        numero_art = metadatos.get("numero_articulo", "específico")
        return f'''
CONSULTA SOBRE ARTÍCULO ESPECÍFICO:
📋 El usuario busca información sobre el artículo {numero_art}
📋 En la respuesta directa, explicar QUÉ ESTABLECE el artículo en términos prácticos
📋 En el fundamento legal, citar el texto exacto si es relevante
📋 En orientación práctica, explicar CÓMO APLICAR esa disposición
'''
    return ""

def _agregar_instrucciones_pasos(necesita_pasos: bool) -> str:
    """
    Agrega instrucciones para incluir pasos procedimentales.
    """
    if necesita_pasos:
        return '''
EL USUARIO SOLICITA PROCEDIMIENTOS:
🔧 En "Orientación Práctica" incluir pasos específicos y concretos
🔧 Mencionar instituciones paraguayas relevantes (ministerios, juzgados, etc.)
🔧 Dar información práctica sobre documentos, tiempos, costos si aplica
🔧 Usar formato "Pasos a seguir:" para activar el estilo visual correcto
'''
    return ""

def construir_prompt_sin_contexto(pregunta_usuario: str) -> str:
    """
    Construye un prompt cuando no hay contexto legal específico.
    Sincronizado con el estilo de respuestas estructuradas.
    """
    es_emergencia = _detectar_emergencia_critica(pregunta_usuario)
    
    prompt = f'''Eres COLEPA, asistente legal oficial paraguayo.

CONSULTA SIN CONTEXTO LEGAL ESPECÍFICO:
{pregunta_usuario}

{_agregar_instrucciones_emergencia(es_emergencia)}

RESPUESTA REQUERIDA (ESTRUCTURA SIMPLIFICADA):

1. **RESPUESTA DIRECTA INICIAL:**
   - Explicar que no se encontró esa disposición específica
   - Dar orientación general sobre el tema si es posible

2. **ORIENTACIÓN PRÁCTICA:**
   - Sugerencias para reformular la consulta
   - Recomendaciones sobre dónde obtener asesoramiento específico

GENERAR RESPUESTA ESTRUCTURADA:'''

    return prompt

def validar_contexto_legal(contexto_legal: str) -> bool:
    """
    Valida que el contexto legal proporcionado sea válido y útil.
    Mejorado para mayor precisión.
    """
    if not contexto_legal or len(contexto_legal.strip()) < 20:
        return False
    
    # Verificar que contiene elementos típicos de un artículo legal paraguayo
    indicadores_legales = [
        "artículo", "ley", "código", "disposición", "establecer", "determina",
        "sanciona", "procedimiento", "derecho", "obligación", "prohibir",
        "paraguay", "nacional", "república"
    ]
    
    contexto_lower = contexto_legal.lower()
    return any(indicador in contexto_lower for indicador in indicadores_legales)

def extraer_metadatos_contexto(contexto_legal: str) -> Dict[str, Optional[str]]:
    """
    Extrae metadatos útiles del contexto legal para mejorar la respuesta.
    Mejorado y sincronizado con las capacidades del sistema.
    """
    metadatos = {
        "numero_articulo": None,
        "tipo_norma": None,
        "tema_principal": None,
        "libro_seccion": None
    }
    
    # Extraer número de artículo con mayor precisión
    patrones_articulo = [
        r'art[ií]culo\s*n[úu]mero\s*(\d+)',
        r'art[ií]culo\s*(\d+)',
        r'art\.?\s*(\d+)'
    ]
    
    for patron in patrones_articulo:
        match = re.search(patron, contexto_legal, re.IGNORECASE)
        if match:
            metadatos["numero_articulo"] = match.group(1)
            break
    
    # Determinar tipo de norma con mayor precisión
    contexto_lower = contexto_legal.lower()
    tipos_norma = {
        "civil": ["código civil", "derecho civil", "familia", "matrimonio", "propiedad"],
        "penal": ["código penal", "delito", "crimen", "pena", "sanción"],
        "laboral": ["código laboral", "trabajo", "empleado", "salario"],
        "procesal_civil": ["código procesal civil", "proceso civil", "demanda"],
        "procesal_penal": ["código procesal penal", "proceso penal", "investigación"],
        "aduanero": ["código aduanero", "aduana", "importación", "exportación"],
        "electoral": ["código electoral", "elección", "voto", "candidato"],
        "niñez": ["niñez", "adolescencia", "menor", "niño"],
        "sanitario": ["código sanitario", "salud", "medicina"]
    }
    
    for tipo, palabras_clave in tipos_norma.items():
        if any(palabra in contexto_lower for palabra in palabras_clave):
            metadatos["tipo_norma"] = tipo
            break
    
    # Extraer información sobre libro o sección
    match_libro = re.search(r'libro\s+(\w+)', contexto_legal, re.IGNORECASE)
    if match_libro:
        metadatos["libro_seccion"] = match_libro.group(1)
    
    return metadatos

def optimizar_prompt_para_tokens(prompt: str, max_tokens: int = 1500) -> str:
    """
    Optimiza el prompt para no exceder límites de tokens.
    Nuevo método para eficiencia.
    """
    if len(prompt) <= max_tokens:
        return prompt
    
    # Estrategia de reducción inteligente
    # 1. Reducir ejemplos y explicaciones largas
    # 2. Mantener instrucciones críticas
    # 3. Preservar contexto legal completo
    
    lineas = prompt.split('\n')
    lineas_criticas = []
    lineas_opcionales = []
    
    for linea in lineas:
        if any(keyword in linea.upper() for keyword in [
            'CONTEXTO LEGAL', 'CONSULTA DEL USUARIO', 'ESTRUCTURA OBLIGATORIA',
            'RESPUESTA DIRECTA', 'FUNDAMENTO LEGAL', 'ORIENTACIÓN PRÁCTICA'
        ]):
            lineas_criticas.append(linea)
        else:
            lineas_opcionales.append(linea)
    
    # Reconstruir con prioridad en líneas críticas
    prompt_optimizado = '\n'.join(lineas_criticas)
    
    # Agregar líneas opcionales si hay espacio
    for linea in lineas_opcionales:
        if len(prompt_optimizado) + len(linea) + 1 <= max_tokens:
            prompt_optimizado += '\n' + linea
        else:
            break
    
    return prompt_optimizado

# Ejemplos de uso sincronizado
if __name__ == "__main__":
    # Casos de prueba sincronizados con el sistema mejorado
    casos_prueba = [
        ("mi marido me pega", "EMERGENCIA - debe destacar línea 137"),
        ("artículo 74 código aduanero", "ARTÍCULO ESPECÍFICO - debe explicar qué establece"),
        ("cómo importar productos", "PROCEDIMIENTOS - debe incluir pasos"),
        ("qué dice sobre divorcio", "CONSULTA GENERAL - respuesta estructurada")
    ]
    
    print("🧪 TESTING PROMPT BUILDER SINCRONIZADO")
    print("=" * 60)
    
    contexto_ejemplo = """Artículo 74 del Código Aduanero de Paraguay establece que toda mercancía 
    importada debe presentar declaración aduanera completa con documentación de origen, 
    valor comercial y clasificación arancelaria correspondiente."""
    
    for pregunta, descripcion in casos_prueba:
        print(f"\n📝 Caso: {pregunta}")
        print(f"🏷️ Tipo: {descripcion}")
        
        prompt = construir_prompt(contexto_ejemplo, pregunta)
        
        # Análisis de la consulta
        es_emergencia = _detectar_emergencia_critica(pregunta)
        necesita_pasos = _usuario_pide_procedimientos(pregunta)
        busca_articulo = _busca_articulo_especifico(pregunta)
        
        print(f"🚨 Emergencia: {'SÍ' if es_emergencia else 'NO'}")
        print(f"📋 Procedimientos: {'SÍ' if necesita_pasos else 'NO'}")
        print(f"🔍 Artículo específico: {'SÍ' if busca_articulo else 'NO'}")
        print(f"📏 Longitud del prompt: {len(prompt)} chars")
        
        if len(prompt) > 2000:
            print("⚠️ Prompt largo - aplicando optimización...")
            prompt_optimizado = optimizar_prompt_para_tokens(prompt, 1800)
            print(f"📏 Después de optimización: {len(prompt_optimizado)} chars")
        
        print("-" * 50)
