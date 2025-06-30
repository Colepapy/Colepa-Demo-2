# Archivo: app/prompt_builder.py - VERSIÓN OPTIMIZADA PARA RESPUESTAS CORTAS
# COLEPA - Prompt Builder Súper Optimizado y ECONÓMICO

import re
from typing import Dict, Optional

def construir_prompt(contexto_legal: str, pregunta_usuario: str) -> str:
    """
    Construye un prompt OPTIMIZADO para respuestas CORTAS y ECONÓMICAS.
    
    Args:
        contexto_legal: El texto del artículo de ley recuperado de Qdrant.
        pregunta_usuario: La pregunta original hecha por el usuario.
    
    Returns:
        Un string con el prompt optimizado para respuestas concisas.
    """
    
    # Analizar si el usuario pide pasos/procedimientos específicos
    necesita_pasos = _usuario_pide_procedimientos(pregunta_usuario)
    urgencia = _detectar_urgencia(pregunta_usuario)
    
    # Construir el prompt súper conciso
    prompt = f'''Eres COLEPA, asistente legal de Paraguay. Responde de forma CONCISA y DIRECTA.

CONTEXTO LEGAL:
{contexto_legal}

CONSULTA:
{pregunta_usuario}

INSTRUCCIONES CRÍTICAS:
1. RESPUESTA CORTA: Máximo 3-4 líneas de explicación
2. FORMATO EXACTO requerido:
```
**[Nombre de la Ley] - Artículo [Número]**

[Explicación BREVE de qué establece la ley - máximo 2-3 líneas]

---

*Fuente: [Ley], Artículo [Número]*
```

3. PROHIBIDO agregar:
   - "En tu situación específica:"
   - "Pasos recomendados:" (SOLO si el usuario pregunta QUÉ HACER)
   - Explicaciones largas o redundantes
   - Texto de relleno

4. INCLUIR SOLO SI SE PREGUNTA explícitamente "qué hacer", "qué pasos", "cómo proceder":
   - Entonces SÍ agregar sección de pasos

{_agregar_instruccion_pasos(necesita_pasos)}

{_agregar_seccion_urgencia_corta(urgencia)}

RESPONDE AHORA de forma CONCISA:'''

    return prompt

def _usuario_pide_procedimientos(pregunta: str) -> bool:
    """
    Detecta si el usuario pregunta específicamente qué hacer o pasos a seguir.
    """
    pregunta_lower = pregunta.lower()
    indicadores_pasos = [
        "qué hacer", "que hacer", "qué hago", "que hago",
        "cómo proceder", "como proceder", "qué pasos", "que pasos",
        "cómo tramitar", "como tramitar", "qué debo hacer", "que debo hacer",
        "cuáles son los pasos", "cuales son los pasos",
        "cómo denunciar", "como denunciar", "dónde acudir", "donde acudir",
        "qué requisitos", "que requisitos", "cómo hacer", "como hacer"
    ]
    
    return any(indicador in pregunta_lower for indicador in indicadores_pasos)

def _detectar_urgencia(pregunta: str) -> bool:
    """
    Detecta si la consulta requiere atención urgente.
    """
    pregunta_lower = pregunta.lower()
    palabras_urgentes = [
        "urgente", "emergencia", "peligro", "amenaza", 
        "me pega", "me golpea", "violencia", "maltrato",
        "me está", "está pasando", "ahora"
    ]
    
    return any(palabra in pregunta_lower for palabra in palabras_urgentes)

def _agregar_instruccion_pasos(necesita_pasos: bool) -> str:
    """
    Agrega instrucción para incluir pasos solo si se solicita.
    """
    if necesita_pasos:
        return '''
5. EL USUARIO PREGUNTA QUÉ HACER - Agregar sección:
**Pasos recomendados:**
- [2-3 pasos específicos máximo]
'''
    return ""

def _agregar_seccion_urgencia_corta(es_urgente: bool) -> str:
    """
    Agrega sección de urgencia MUY corta si es necesario.
    """
    if es_urgente:
        return '''
6. CASO URGENTE - Agregar al final:
**🚨 Urgente:** Línea 137 - Denuncia inmediata en comisarías
'''
    return ""

def construir_prompt_sin_contexto(pregunta_usuario: str) -> str:
    """
    Construye un prompt CORTO cuando no hay contexto legal específico.
    """
    
    prompt = f'''Eres COLEPA, asistente legal paraguayo.

CONSULTA SIN CONTEXTO ESPECÍFICO:
{pregunta_usuario}

RESPUESTA REQUERIDA (CORTA):
```
**Consulta Legal**

No encontré esa disposición específica en mi base legal.

**Sugerencias:**
- Reformule con términos más específicos
- Mencione el código o artículo específico

*Para asesoramiento personalizado, consulte un abogado especializado.*
```

RESPONDE de forma CONCISA:'''

    return prompt

def validar_contexto_legal(contexto_legal: str) -> bool:
    """
    Valida que el contexto legal proporcionado sea válido y útil.
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
    
    return metadatos

# Ejemplos de uso optimizado
if __name__ == "__main__":
    # Casos de prueba para respuestas cortas
    casos_prueba = [
        ("¿Qué dice el artículo 95?", "SIN procedimientos"),
        ("¿Qué dice el artículo 95 y qué debo hacer?", "CON procedimientos"),
        ("Mi esposo me pega", "URGENCIA"),
        ("¿Cuáles son los requisitos para casarse?", "CON procedimientos")
    ]
    
    print("🧪 TESTING PROMPT OPTIMIZADO PARA AHORRO")
    print("=" * 50)
    
    contexto_ejemplo = "Artículo 95 del Código Civil establece que..."
    
    for pregunta, tipo in casos_prueba:
        print(f"\n📝 Caso: {pregunta}")
        print(f"🏷️ Tipo: {tipo}")
        
        prompt = construir_prompt(contexto_ejemplo, pregunta)
        necesita_pasos = _usuario_pide_procedimientos(pregunta)
        
        print(f"🔍 Detecta procedimientos: {'SÍ' if necesita_pasos else 'NO'}")
        print(f"📏 Longitud del prompt: {len(prompt)} chars")
        print("---")
