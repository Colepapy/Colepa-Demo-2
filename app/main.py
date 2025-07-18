# COLEPA - Asistente Legal Gubernamental
# Backend FastAPI Mejorado para Consultas Legales Oficiales - VERSIÓN PREMIUM

import os
import re
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Verificar y configurar OpenAI
try:
    from openai import OpenAI
    from dotenv import load_dotenv
    
    load_dotenv()
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_AVAILABLE = True
    logger.info("✅ OpenAI configurado correctamente")
except ImportError as e:
    logger.warning(f"⚠️ OpenAI no disponible: {e}")
    OPENAI_AVAILABLE = False
    openai_client = None

# Importaciones locales con fallback
try:
    from app.vector_search import buscar_articulo_relevante, buscar_articulo_por_numero
    from app.prompt_builder import construir_prompt
    VECTOR_SEARCH_AVAILABLE = True
    logger.info("✅ Módulos de búsqueda vectorial cargados")
except ImportError:
    logger.warning("⚠️ Módulos de búsqueda no encontrados, usando funciones mock")
    VECTOR_SEARCH_AVAILABLE = False
    
    def buscar_articulo_relevante(query_vector, collection_name):
        return {
            "pageContent": "Contenido de ejemplo del artículo", 
            "nombre_ley": "Código Civil", 
            "numero_articulo": "123"
        }
    
    def buscar_articulo_por_numero(numero, collection_name):
        return {
            "pageContent": f"Contenido del artículo {numero}", 
            "nombre_ley": "Código Civil", 
            "numero_articulo": str(numero)
        }
    
    def construir_prompt(contexto_legal, pregunta_usuario):
        return f"Contexto Legal: {contexto_legal}\n\nPregunta del Usuario: {pregunta_usuario}"

# ========== NUEVO: CLASIFICADOR INTELIGENTE ==========
try:
    from app.clasificador_inteligente import clasificar_y_procesar
    CLASIFICADOR_AVAILABLE = True
    logger.info("✅ Clasificador inteligente cargado")
except ImportError:
    logger.warning("⚠️ Clasificador no encontrado, modo básico")
    CLASIFICADOR_AVAILABLE = False
    
    def clasificar_y_procesar(texto):
        return {
            'tipo_consulta': 'consulta_legal',
            'respuesta_directa': None,
            'requiere_busqueda': True,
            'es_conversacional': False
        }

# === MODELOS PYDANTIC ===
class MensajeChat(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=3000)
    timestamp: Optional[datetime] = None

class ConsultaRequest(BaseModel):
    historial: List[MensajeChat] = Field(..., min_items=1, max_items=20)
    metadatos: Optional[Dict[str, Any]] = None

class FuenteLegal(BaseModel):
    ley: str
    articulo_numero: str
    libro: Optional[str] = None
    titulo: Optional[str] = None

class ConsultaResponse(BaseModel):
    respuesta: str
    fuente: Optional[FuenteLegal] = None
    recomendaciones: Optional[List[str]] = None
    tiempo_procesamiento: Optional[float] = None
    es_respuesta_oficial: bool = True

class StatusResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    servicios: Dict[str, str]
    colecciones_disponibles: int

# ========== NUEVOS MODELOS PARA MÉTRICAS ==========
class MetricasCalidad(BaseModel):
    consulta_id: str
    tiene_contexto: bool
    relevancia_contexto: float
    longitud_respuesta: int
    tiempo_procesamiento: float
    codigo_identificado: str
    articulo_encontrado: Optional[str] = None

# === CONFIGURACIÓN DEL SISTEMA ===
MAPA_COLECCIONES = {
    "Código Aduanero": "colepa_aduanero_maestro",
    "Código Civil": "colepa_civil_maestro", 
    "Código Electoral": "colepa_electoral_maestro",
    "Código Laboral": "colepa_laboral_maestro",
    "Código de la Niñez y la Adolescencia": "colepa_ninezadolescencia_maestro",
    "Código de Organización Judicial": "colepa_organizacion_judicial_maestro",
    "Código Penal": "colepa_penal_maestro",
    "Código Procesal Civil": "colepa_procesal_civil_maestro",
    "Código Procesal Penal": "colepa_procesal_penal_maestro",
    "Código Sanitario": "colepa_sanitario_maestro"
}

PALABRAS_CLAVE_EXPANDIDAS = {
    "Código Civil": [
        "civil", "matrimonio", "divorcio", "propiedad", "contratos", "familia", 
        "herencia", "sucesión", "sociedad conyugal", "bien ganancial", "patria potestad",
        "tutela", "curatela", "adopción", "filiación", "alimentos", "régimen patrimonial",
        "esposo", "esposa", "cónyuge", "pareja", "hijos", "padres"
    ],
    "Código Penal": [
        "penal", "delito", "crimen", "pena", "prisión", "robo", "homicidio", "hurto",
        "estafa", "violación", "agresión", "lesiones", "amenaza", "extorsión", "secuestro",
        "narcotráfico", "corrupción", "fraude", "violencia doméstica", "femicidio",
        "pega", "golpea", "golpes", "maltrato", "abuso", "acoso", "persigue", "molesta",
        "choque", "chocaron", "atropello", "accidente", "atropelló"
    ],
    "Código Laboral": [
        "laboral", "trabajo", "empleado", "salario", "vacaciones", "despido", "contrato laboral",
        "indemnización", "aguinaldo", "licencia", "maternidad", "seguridad social", "sindicato",
        "huelga", "jornada laboral", "horas extras", "jubilación", "accidente laboral",
        "jefe", "patrón", "empleador", "trabajador", "sueldo"
    ],
    "Código Procesal Civil": [
        "proceso civil", "demanda", "juicio civil", "sentencia", "apelación", "recurso",
        "prueba", "testigo", "peritaje", "embargo", "medida cautelar", "ejecución",
        "daños", "perjuicios", "responsabilidad civil", "indemnización"
    ],
    "Código Procesal Penal": [
        "proceso penal", "acusación", "juicio penal", "fiscal", "defensor", "imputado",
        "querella", "investigación", "allanamiento", "detención", "prisión preventiva",
        "denuncia", "denunciar", "comisaría", "policía"
    ],
    "Código Aduanero": [
        "aduana", "aduanero", "importación", "exportación", "aranceles", "tributo aduanero", "mercancía",
        "declaración aduanera", "régimen aduanero", "zona franca", "contrabando", "depósito", "habilitación"
    ],
    "Código Electoral": [
        "electoral", "elecciones", "voto", "candidato", "sufragio", "padrón electoral",
        "tribunal electoral", "campaña electoral", "partido político", "referendum"
    ],
    "Código de la Niñez y la Adolescencia": [
        "menor", "niño", "adolescente", "tutela", "adopción", "menor infractor",
        "protección integral", "derechos del niño", "consejería", "medida socioeducativa",
        "hijo", "hija", "niños", "niñas", "menores"
    ],
    "Código de Organización Judicial": [
        "judicial", "tribunal", "juez", "competencia", "jurisdicción", "corte suprema",
        "juzgado", "fuero", "instancia", "sala", "magistrado", "secretario judicial"
    ],
    "Código Sanitario": [
        "sanitario", "salud", "medicina", "hospital", "clínica", "medicamento",
        "profesional sanitario", "epidemia", "vacuna", "control sanitario"
    ]
}

# ========== CONFIGURACIÓN DE TOKENS OPTIMIZADA ==========
MAX_TOKENS_INPUT_CONTEXTO = 400      # Máximo tokens para contexto legal
MAX_TOKENS_RESPUESTA = 300           # Máximo tokens para respuesta
MAX_TOKENS_SISTEMA = 180             # Máximo tokens para prompt sistema

# ========== PROMPT PREMIUM COMPACTO ==========
INSTRUCCION_SISTEMA_LEGAL_PREMIUM = """
COLEPA - Asistente jurídico Paraguay. Respuesta obligatoria:

**DISPOSICIÓN:** [Ley + Artículo específico]
**FUNDAMENTO:** [Texto normativo textual]  
**APLICACIÓN:** [Cómo aplica a la consulta]

Máximo 250 palabras. Solo use contexto proporcionado. Terminología jurídica precisa.
"""

# ========== NUEVA FUNCIÓN: VALIDADOR DE CONTEXTO ==========
def validar_calidad_contexto(contexto: Optional[Dict], pregunta: str) -> tuple[bool, float]:
    """
    Valida si el contexto encontrado es realmente relevante para la pregunta.
    Retorna (es_valido, score_relevancia)
    """
    if not contexto or not contexto.get("pageContent"):
        return False, 0.0
    
    try:
        texto_contexto = contexto.get("pageContent", "").lower()
        pregunta_lower = pregunta.lower()
        
        # Extraer palabras clave de la pregunta
        palabras_pregunta = set(re.findall(r'\b\w+\b', pregunta_lower))
        palabras_contexto = set(re.findall(r'\b\w+\b', texto_contexto))
        
        # Calcular intersección
        interseccion = palabras_pregunta & palabras_contexto
        
        if len(palabras_pregunta) == 0:
            return False, 0.0
            
        score_basico = len(interseccion) / len(palabras_pregunta)
        
        # Bonus por palabras clave jurídicas importantes
        palabras_juridicas = {"artículo", "código", "ley", "disposición", "norma", "legal"}
        bonus_juridico = len(interseccion & palabras_juridicas) * 0.1
        
        # Bonus por números de artículo coincidentes
        numeros_pregunta = set(re.findall(r'\d+', pregunta))
        numeros_contexto = set(re.findall(r'\d+', texto_contexto))
        bonus_numeros = len(numeros_pregunta & numeros_contexto) * 0.2
        
        score_final = score_basico + bonus_juridico + bonus_numeros
        
        # Umbral de calidad: debe tener al menos 30% de relevancia
        es_valido = score_final >= 0.3 and len(texto_contexto.strip()) >= 50
        
        logger.info(f"🎯 Validación contexto - Score: {score_final:.2f}, Válido: {es_valido}")
        return es_valido, score_final
        
    except Exception as e:
        logger.error(f"❌ Error validando contexto: {e}")
        return False, 0.0

# ========== NUEVA FUNCIÓN: BÚSQUEDA MULTI-MÉTODO ==========
def buscar_con_manejo_errores(pregunta: str, collection_name: str) -> Optional[Dict]:
    """
    Búsqueda robusta con múltiples métodos y validación de calidad.
    """
    contexto_final = None
    metodo_exitoso = None
    
    # Método 1: Búsqueda por número de artículo específico
    numero_articulo = extraer_numero_articulo_mejorado(pregunta)
    if numero_articulo and VECTOR_SEARCH_AVAILABLE:
        try:
            logger.info(f"🎯 Método 1: Búsqueda por artículo {numero_articulo}")
            contexto = buscar_articulo_por_numero(numero_articulo, collection_name)
            
            if contexto:
                es_valido, score = validar_calidad_contexto(contexto, pregunta)
                if es_valido:
                    contexto_final = contexto
                    metodo_exitoso = f"Búsqueda exacta Art. {numero_articulo}"
                    logger.info(f"✅ Método 1 exitoso - Score: {score:.2f}")
                else:
                    logger.warning(f"⚠️ Método 1 - Contexto no válido (Score: {score:.2f})")
        except Exception as e:
            logger.error(f"❌ Error en Método 1: {e}")
    
    # Método 2: Búsqueda semántica con embeddings
    if not contexto_final and OPENAI_AVAILABLE and VECTOR_SEARCH_AVAILABLE:
        try:
            logger.info("🔍 Método 2: Búsqueda semántica con embeddings")
            
            # Optimizar consulta para embeddings
            consulta_optimizada = f"{pregunta} legislación paraguay derecho"
            
            embedding_response = openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=consulta_optimizada
            )
            query_vector = embedding_response.data[0].embedding
            
            contexto = buscar_articulo_relevante(query_vector, collection_name)
            
            if contexto:
                es_valido, score = validar_calidad_contexto(contexto, pregunta)
                if es_valido and score >= 0.4:  # Umbral más alto para semántica
                    contexto_final = contexto
                    metodo_exitoso = f"Búsqueda semántica (Score: {score:.2f})"
                    logger.info(f"✅ Método 2 exitoso - Score: {score:.2f}")
                else:
                    logger.warning(f"⚠️ Método 2 - Contexto no válido (Score: {score:.2f})")
                    
        except Exception as e:
            logger.error(f"❌ Error en Método 2: {e}")
    
    # Método 3: Búsqueda por palabras clave específicas (fallback)
    if not contexto_final and numero_articulo and VECTOR_SEARCH_AVAILABLE:
        try:
            logger.info("🔄 Método 3: Búsqueda fallback por palabras clave")
            
            # Crear vector dummy y usar filtros más amplios
            contexto = buscar_articulo_relevante([0.1] * 1536, collection_name)
            
            if contexto:
                es_valido, score = validar_calidad_contexto(contexto, pregunta)
                if es_valido and score >= 0.2:  # Umbral más bajo para fallback
                    contexto_final = contexto
                    metodo_exitoso = f"Búsqueda fallback (Score: {score:.2f})"
                    logger.info(f"✅ Método 3 exitoso - Score: {score:.2f}")
                    
        except Exception as e:
            logger.error(f"❌ Error en Método 3: {e}")
    
    if contexto_final:
        logger.info(f"🎉 Contexto encontrado usando: {metodo_exitoso}")
        return contexto_final
    else:
        logger.warning("❌ Ningún método de búsqueda encontró contexto válido")
        return None

# === CONFIGURACIÓN DE FASTAPI ===
app = FastAPI(
    title="COLEPA - Asistente Legal Oficial",
    description="Sistema de consultas legales basado en la legislación paraguaya",
    version="3.2.0-PREMIUM",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.colepa.com",
        "https://colepa.com", 
        "https://colepa-demo-2.vercel.app",
        "http://localhost:3000",
        "http://localhost:8080"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ========== MÉTRICAS EN MEMORIA PARA DEMO ==========
metricas_sistema = {
    "consultas_procesadas": 0,
    "contextos_encontrados": 0,
    "tiempo_promedio": 0.0,
    "ultima_actualizacion": datetime.now()
}

# === FUNCIONES AUXILIARES MEJORADAS ===
def extraer_numero_articulo_mejorado(texto: str) -> Optional[int]:
    """
    Extracción mejorada y más precisa de números de artículo
    """
    texto_lower = texto.lower()
    
    # Patrones más específicos y completos
    patrones = [
        r'art[ií]culo\s*(?:n[úu]mero\s*)?(\d+)',
        r'art\.?\s*(\d+)',
        r'artículo\s*(\d+)',
        r'articulo\s*(\d+)',
        r'art\s+(\d+)',
        r'(?:^|\s)(\d+)(?:\s|$)',  # Número solo si está aislado
    ]
    
    for patron in patrones:
        matches = re.finditer(patron, texto_lower)
        for match in matches:
            try:
                numero = int(match.group(1))
                if 1 <= numero <= 9999:  # Rango razonable para artículos
                    logger.info(f"🔍 Número de artículo extraído: {numero} con patrón: {patron}")
                    return numero
            except (ValueError, IndexError):
                continue
    
    logger.info(f"🔍 No se encontró número de artículo en: {texto[:50]}...")
    return None

def clasificar_consulta_inteligente(pregunta: str) -> str:
    """
    Clasificación inteligente mejorada con mejor scoring
    """
    pregunta_lower = pregunta.lower()
    scores = {}
    
    # Búsqueda por palabras clave con peso ajustado
    for ley, palabras in PALABRAS_CLAVE_EXPANDIDAS.items():
        score = 0
        for palabra in palabras:
            if palabra in pregunta_lower:
                # Mayor peso para coincidencias exactas de palabras completas
                if f" {palabra} " in f" {pregunta_lower} ":
                    score += 5
                elif palabra in pregunta_lower:
                    score += 2
        
        if score > 0:
            scores[ley] = score
    
    # Búsqueda por menciones explícitas de códigos (peso muy alto)
    for ley in MAPA_COLECCIONES.keys():
        ley_lower = ley.lower()
        # Buscar nombre completo
        if ley_lower in pregunta_lower:
            scores[ley] = scores.get(ley, 0) + 20
        
        # Buscar versiones sin "código"
        ley_sin_codigo = ley_lower.replace("código ", "").replace("código de ", "")
        if ley_sin_codigo in pregunta_lower:
            scores[ley] = scores.get(ley, 0) + 15
    
    # Patrones específicos mejorados para casos reales
    patrones_especiales = {
        r'violen(cia|to|tar)|agre(sión|dir)|golpe|maltrato|femicidio|pega|abuso': "Código Penal",
        r'matrimonio|divorcio|esposo|esposa|cónyuge|familia|pareja': "Código Civil", 
        r'trabajo|empleo|empleado|jefe|patrón|salario|sueldo|laboral': "Código Laboral",
        r'menor|niño|niña|adolescente|hijo|hija|adopción': "Código de la Niñez y la Adolescencia",
        r'elección|elecciones|voto|votar|candidato|político|electoral': "Código Electoral",
        r'choque|chocaron|atropello|atropelló|accidente|daños|perjuicios': "Código Procesal Civil",
        r'denuncia|fiscal|delito|acusado|penal|proceso penal|comisaría': "Código Procesal Penal",
        r'aduana|aduanero|importa|exporta|mercancía|depósito': "Código Aduanero",
        r'salud|medicina|médico|hospital|sanitario': "Código Sanitario",
        r'acoso|persigue|molesta|hostiga': "Código Penal"
    }
    
    for patron, ley in patrones_especiales.items():
        if re.search(patron, pregunta_lower):
            scores[ley] = scores.get(ley, 0) + 12
    
    # Determinar la mejor clasificación
    if scores:
        mejor_ley = max(scores.keys(), key=lambda k: scores[k])
        score_final = scores[mejor_ley]
        logger.info(f"📚 Consulta clasificada como: {mejor_ley} (score: {score_final})")
        return MAPA_COLECCIONES[mejor_ley]
    
    # Default: Código Civil (más general)
    logger.info("📚 Consulta no clasificada específicamente, usando Código Civil por defecto")
    return MAPA_COLECCIONES["Código Civil"]

def clasificar_consulta_con_ia_robusta(pregunta: str) -> str:
    """
    SÚPER ENRUTADOR: Clasificación robusta usando IA con límites de tokens
    """
    if not OPENAI_AVAILABLE or not openai_client:
        logger.warning("⚠️ OpenAI no disponible, usando clasificación básica")
        return clasificar_consulta_inteligente(pregunta)
    
    # PROMPT ULTRA-COMPACTO PARA CLASIFICACIÓN
    prompt_clasificacion = f"""Clasifica esta consulta legal paraguaya en uno de estos códigos:

CÓDIGOS:
1. Código Civil - matrimonio, divorcio, familia, propiedad, contratos
2. Código Penal - delitos, violencia, agresión, robo, homicidio  
3. Código Laboral - trabajo, empleo, salarios, despidos
4. Código Procesal Civil - demandas civiles, daños, perjuicios
5. Código Procesal Penal - denuncias penales, investigaciones
6. Código Aduanero - aduana, importación, exportación
7. Código Electoral - elecciones, votos, candidatos
8. Código de la Niñez y la Adolescencia - menores, niños
9. Código de Organización Judicial - tribunales, jueces
10. Código Sanitario - salud, medicina, hospitales

CONSULTA: "{pregunta[:150]}"

Responde solo el nombre exacto (ej: "Código Penal")"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # Modelo más económico
            messages=[{"role": "user", "content": prompt_clasificacion}],
            temperature=0.1,
            max_tokens=20,  # ULTRA LÍMITE para clasificación
            timeout=10  # Timeout reducido
        )
        
        codigo_identificado = response.choices[0].message.content.strip()
        
        # LOG DE TOKENS
        if hasattr(response, 'usage'):
            logger.info(f"💰 Clasificación - Tokens: {response.usage.total_tokens}")
        
        # Mapear respuesta a colección
        if codigo_identificado in MAPA_COLECCIONES:
            collection_name = MAPA_COLECCIONES[codigo_identificado]
            logger.info(f"🎯 IA clasificó: {codigo_identificado} → {collection_name}")
            return collection_name
        else:
            # Fuzzy matching para nombres similares
            for codigo_oficial in MAPA_COLECCIONES.keys():
                if any(word in codigo_identificado.lower() for word in codigo_oficial.lower().split()):
                    collection_name = MAPA_COLECCIONES[codigo_oficial]
                    logger.info(f"🎯 IA clasificó (fuzzy): {codigo_identificado} → {codigo_oficial}")
                    return collection_name
            
            # Fallback
            logger.warning(f"⚠️ IA devolvió código no reconocido: {codigo_identificado}")
            return clasificar_consulta_inteligente(pregunta)
            
    except Exception as e:
        logger.error(f"❌ Error en clasificación con IA: {e}")
        return clasificar_consulta_inteligente(pregunta)

def truncar_contexto_inteligente(contexto: str, max_tokens: int = MAX_TOKENS_INPUT_CONTEXTO) -> str:
    """
    Trunca el contexto legal manteniendo las partes más importantes
    """
    if not contexto:
        return ""
    
    # Estimación: 1 token ≈ 4 caracteres en español
    max_chars = max_tokens * 4
    
    if len(contexto) <= max_chars:
        return contexto
    
    # Priorizar texto que contenga artículos específicos
    lineas = contexto.split('\n')
    lineas_prioritarias = []
    lineas_normales = []
    
    for linea in lineas:
        if any(palabra in linea.lower() for palabra in ['artículo', 'artículo', 'art.', 'establece', 'dispone']):
            lineas_prioritarias.append(linea)
        else:
            lineas_normales.append(linea)
    
    # Reconstruir con prioridades
    texto_final = '\n'.join(lineas_prioritarias)
    
    # Agregar líneas normales si hay espacio
    chars_restantes = max_chars - len(texto_final)
    for linea in lineas_normales:
        if len(texto_final) + len(linea) + 1 <= max_chars:
            texto_final += '\n' + linea
        else:
            break
    
    # Si aún es muy largo, truncar al final
    if len(texto_final) > max_chars:
        texto_final = texto_final[:max_chars-10] + "... [TEXTO TRUNCADO]"
    
    logger.info(f"📏 Contexto truncado: {len(contexto)} → {len(texto_final)} chars")
    return texto_final

def generar_respuesta_legal_premium(historial: List[MensajeChat], contexto: Optional[Dict] = None) -> str:
    """
    Generación de respuesta legal PREMIUM con límites estrictos de tokens
    """
    if not OPENAI_AVAILABLE or not openai_client:
        return generar_respuesta_con_contexto(historial[-1].content, contexto)
    
    try:
        pregunta_actual = historial[-1].content
        
        # Validar contexto antes de procesar
        if contexto:
            es_valido, score_relevancia = validar_calidad_contexto(contexto, pregunta_actual)
            if not es_valido:
                logger.warning(f"⚠️ Contexto no válido (score: {score_relevancia:.2f}), generando respuesta sin contexto")
                contexto = None
        
        # Preparar mensajes para OpenAI con LÍMITES ESTRICTOS
        mensajes = [{"role": "system", "content": INSTRUCCION_SISTEMA_LEGAL_PREMIUM}]
        
        # Construcción del prompt con CONTROL DE TOKENS
        if contexto and contexto.get("pageContent"):
            ley = contexto.get('nombre_ley', 'Legislación paraguaya')
            articulo = contexto.get('numero_articulo', 'N/A')
            contenido_legal = contexto.get('pageContent', '')
            
            # TRUNCAR CONTEXTO INTELIGENTEMENTE
            contenido_truncado = truncar_contexto_inteligente(contenido_legal)
            
            # PROMPT COMPACTO OPTIMIZADO
            prompt_profesional = f"""CONSULTA: {pregunta_actual[:200]}

NORMA: {ley} - Art. {articulo}
TEXTO: {contenido_truncado}

Responda en formato estructurado."""
            
            mensajes.append({"role": "user", "content": prompt_profesional})
            logger.info(f"📖 Prompt generado - Chars: {len(prompt_profesional)}")
        else:
            # Sin contexto - RESPUESTA ULTRA COMPACTA
            prompt_sin_contexto = f"""CONSULTA: {pregunta_actual[:150]}

Sin normativa específica encontrada. Respuesta profesional breve."""
            
            mensajes.append({"role": "user", "content": prompt_sin_contexto})
            logger.info("📝 Prompt sin contexto - Modo compacto")
        
        # Llamada a OpenAI con LÍMITES ESTRICTOS
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=mensajes,
            temperature=0.1,
            max_tokens=MAX_TOKENS_RESPUESTA,  # LÍMITE ESTRICTO
            presence_penalty=0,
            frequency_penalty=0,
            timeout=25  # Timeout reducido
        )
        
        respuesta = response.choices[0].message.content
        
        # LOG DE TOKENS UTILIZADOS
        if hasattr(response, 'usage'):
            tokens_input = response.usage.prompt_tokens
            tokens_output = response.usage.completion_tokens
            tokens_total = response.usage.total_tokens
            logger.info(f"💰 Tokens utilizados - Input: {tokens_input}, Output: {tokens_output}, Total: {tokens_total}")
        
        logger.info("✅ Respuesta premium generada con límites estrictos")
        return respuesta
        
    except Exception as e:
        logger.error(f"❌ Error con OpenAI en modo premium: {e}")
        return generar_respuesta_con_contexto(historial[-1].content, contexto)

def generar_respuesta_con_contexto(pregunta: str, contexto: Optional[Dict] = None) -> str:
    """
    Respuesta directa PREMIUM usando el contexto de Qdrant
    """
    if contexto and contexto.get("pageContent"):
        ley = contexto.get('nombre_ley', 'Legislación paraguaya')
        articulo = contexto.get('numero_articulo', 'N/A')
        contenido = contexto.get('pageContent', '')
        
        # Formato profesional estructurado
        response = f"""**DISPOSICIÓN LEGAL**
{ley}, Artículo {articulo}

**FUNDAMENTO NORMATIVO**
{contenido}

**APLICACIÓN JURÍDICA**
La disposición citada responde directamente a la consulta planteada sobre "{pregunta}".

---
*Fuente: {ley}, Artículo {articulo}*
*Para asesoramiento específico, consulte con profesional del derecho especializado.*"""
        
        logger.info(f"✅ Respuesta premium generada con contexto: {ley} Art. {articulo}")
        return response
    else:
        return f"""**CONSULTA LEGAL - INFORMACIÓN NO DISPONIBLE**

No se encontró disposición normativa específica aplicable a: "{pregunta}"

**RECOMENDACIONES PROCESALES:**
1. **Reformule la consulta** con mayor especificidad técnica
2. **Especifique el cuerpo normativo** de su interés (Código Civil, Penal, etc.)
3. **Indique número de artículo** si conoce la disposición específica

**ÁREAS DE CONSULTA DISPONIBLES:**
- Normativa civil (familia, contratos, propiedad)
- Normativa penal (delitos, procedimientos)
- Normativa laboral (relaciones de trabajo)
- Normativa procesal (procedimientos judiciales)

*Para consultas específicas sobre casos particulares, diríjase a profesional del derecho competente.*"""

def extraer_fuente_legal(contexto: Optional[Dict]) -> Optional[FuenteLegal]:
    """
    Extrae información de la fuente legal del contexto
    """
    if not contexto:
        return None
    
    return FuenteLegal(
        ley=contexto.get("nombre_ley", "No especificada"),
        articulo_numero=str(contexto.get("numero_articulo", "N/A")),
        libro=contexto.get("libro"),
        titulo=contexto.get("titulo")
    )

def actualizar_metricas(tiene_contexto: bool, tiempo_procesamiento: float, codigo: str, articulo: Optional[str] = None):
    """
    Actualiza métricas del sistema para monitoreo en tiempo real
    """
    global metricas_sistema
    
    metricas_sistema["consultas_procesadas"] += 1
    if tiene_contexto:
        metricas_sistema["contextos_encontrados"] += 1
    
    # Actualizar tiempo promedio
    total_consultas = metricas_sistema["consultas_procesadas"]
    tiempo_anterior = metricas_sistema["tiempo_promedio"]
    metricas_sistema["tiempo_promedio"] = ((tiempo_anterior * (total_consultas - 1)) + tiempo_procesamiento) / total_consultas
    
    metricas_sistema["ultima_actualizacion"] = datetime.now()
    
    logger.info(f"📊 Métricas actualizadas - Consultas: {total_consultas}, Contextos: {metricas_sistema['contextos_encontrados']}")

# === MIDDLEWARE ===
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host
    logger.info(f"📥 {request.method} {request.url.path} - IP: {client_ip}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"📤 {response.status_code} - {process_time:.2f}s")
    
    return response

# === ENDPOINTS ===
@app.get("/", response_model=StatusResponse)
async def sistema_status():
    """Estado del sistema COLEPA"""
    return StatusResponse(
        status="✅ Sistema COLEPA Premium Operativo",
        timestamp=datetime.now(),
        version="3.2.0-PREMIUM",
        servicios={
            "openai": "disponible" if OPENAI_AVAILABLE else "no disponible",
            "busqueda_vectorial": "disponible" if VECTOR_SEARCH_AVAILABLE else "modo_demo",
            "base_legal": "legislación paraguaya completa",
            "modo": "PREMIUM - Demo Congreso Nacional"
        },
        colecciones_disponibles=len(MAPA_COLECCIONES)
    )

@app.get("/api/health")
async def health_check():
    """Verificación de salud detallada"""
    health_status = {
        "sistema": "operativo",
        "timestamp": datetime.now().isoformat(),
        "version": "3.2.0-PREMIUM",
        "modo": "Demo Congreso Nacional",
        "servicios": {
            "openai": "❌ no disponible",
            "qdrant": "❌ no disponible" if not VECTOR_SEARCH_AVAILABLE else "✅ operativo",
            "base_legal": "✅ cargada",
            "validacion_contexto": "✅ activa",
            "busqueda_multi_metodo": "✅ activa"
        }
    }
    
    if OPENAI_AVAILABLE and openai_client:
        try:
            # Test mínimo de OpenAI
            openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                timeout=10
            )
            health_status["servicios"]["openai"] = "✅ operativo"
        except Exception as e:
            health_status["servicios"]["openai"] = f"❌ error: {str(e)[:50]}"
    
    return health_status

@app.get("/api/codigos")
async def listar_codigos_legales():
    """Lista todos los códigos legales disponibles"""
    return {
        "codigos_disponibles": list(MAPA_COLECCIONES.keys()),
        "total_codigos": len(MAPA_COLECCIONES),
        "descripcion": "Códigos legales completos de la República del Paraguay",
        "ultima_actualizacion": "2024",
        "cobertura": "Legislación nacional vigente",
        "modo": "PREMIUM - Optimizado para profesionales del derecho"
    }

# ========== NUEVO ENDPOINT: MÉTRICAS CON TOKENS ==========
@app.get("/api/metricas")
async def obtener_metricas():
    """Métricas del sistema con tracking de tokens para control de costos"""
    global metricas_sistema
    
    # Calcular porcentaje de éxito
    total_consultas = metricas_sistema["consultas_procesadas"]
    contextos_encontrados = metricas_sistema["contextos_encontrados"]
    
    porcentaje_exito = (contextos_encontrados / total_consultas * 100) if total_consultas > 0 else 0
    
    return {
        "estado_sistema": "✅ PREMIUM OPERATIVO",
        "version": "3.2.0-PREMIUM-OPTIMIZADO",
        "timestamp": datetime.now().isoformat(),
        "metricas": {
            "total_consultas_procesadas": total_consultas,
            "contextos_legales_encontrados": contextos_encontrados,
            "porcentaje_exito": round(porcentaje_exito, 1),
            "tiempo_promedio_respuesta": round(metricas_sistema["tiempo_promedio"], 2),
            "ultima_actualizacion": metricas_sistema["ultima_actualizacion"].isoformat()
        },
        "optimizacion_tokens": {
            "max_tokens_respuesta": MAX_TOKENS_RESPUESTA,
            "max_tokens_contexto": MAX_TOKENS_INPUT_CONTEXTO,
            "max_tokens_sistema": MAX_TOKENS_SISTEMA,
            "modelo_clasificacion": "gpt-3.5-turbo (económico)",
            "modelo_respuesta": "gpt-4-turbo-preview (calidad)"
        },
        "configuracion": {
            "validacion_contexto_activa": True,
            "busqueda_multi_metodo": True,
            "formato_profesional": True,
            "control_costos_activo": True,
            "optimizado_para": "Congreso Nacional de Paraguay"
        }
    }

# ========== NUEVO ENDPOINT: TEST OPENAI ==========
@app.get("/api/test-openai")
async def test_openai_connection():
    """Test de conexión con OpenAI para diagnóstico"""
    if not OPENAI_AVAILABLE or not openai_client:
        return {
            "estado": "❌ OpenAI no disponible",
            "error": "Cliente OpenAI no inicializado",
            "recomendacion": "Verificar OPENAI_API_KEY en variables de entorno"
        }
    
    try:
        start_time = time.time()
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test de conexión COLEPA"}],
            max_tokens=10,
            timeout=10
        )
        
        tiempo_respuesta = time.time() - start_time
        
        return {
            "estado": "✅ OpenAI operativo",
            "modelo": "gpt-3.5-turbo",
            "tiempo_respuesta": round(tiempo_respuesta, 2),
            "respuesta_test": response.choices[0].message.content,
            "tokens_utilizados": response.usage.total_tokens if hasattr(response, 'usage') else 0
        }
        
    except Exception as e:
        return {
            "estado": "❌ Error en OpenAI",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ========== ENDPOINT PRINCIPAL OPTIMIZADO PREMIUM ==========
@app.post("/api/consulta", response_model=ConsultaResponse)
async def procesar_consulta_legal_premium(
    request: ConsultaRequest, 
    background_tasks: BackgroundTasks
):
    """
    Endpoint principal PREMIUM para consultas legales oficiales del Congreso Nacional
    """
    start_time = time.time()
    
    try:
        historial = request.historial
        pregunta_actual = historial[-1].content
        
        # ========== LÍMITE DE HISTORIAL PARA EVITAR ERROR 422 ==========
        MAX_HISTORIAL = 3  # Solo últimos 3 mensajes para modo premium
        if len(historial) > MAX_HISTORIAL:
            historial_limitado = historial[-MAX_HISTORIAL:]
            logger.info(f"⚠️ Historial limitado a {len(historial_limitado)} mensajes (modo premium)")
        else:
            historial_limitado = historial
        
        logger.info(f"🏛️ Nueva consulta PREMIUM: {pregunta_actual[:100]}...")
        
        # ========== CLASIFICACIÓN INTELIGENTE ==========
        if CLASIFICADOR_AVAILABLE:
            logger.info("🧠 Iniciando clasificación inteligente premium...")
            clasificacion = clasificar_y_procesar(pregunta_actual)
            
            # Si es una consulta conversacional
            if clasificacion['es_conversacional'] and clasificacion['respuesta_directa']:
                logger.info("💬 Respuesta conversacional directa...")
                
                tiempo_procesamiento = time.time() - start_time
                actualizar_metricas(False, tiempo_procesamiento, "conversacional")
                
                return ConsultaResponse(
                    respuesta=clasificacion['respuesta_directa'],
                    fuente=None,
                    recomendaciones=None,
                    tiempo_procesamiento=round(tiempo_procesamiento, 2),
                    es_respuesta_oficial=True
                )
            
            # Si no requiere búsqueda (tema no legal)
            if not clasificacion['requiere_busqueda']:
                logger.info("🚫 Consulta no legal, redirigiendo profesionalmente...")
                
                respuesta_profesional = """**CONSULTA FUERA DEL ÁMBITO LEGAL**

COLEPA se especializa exclusivamente en normativa jurídica paraguaya. La consulta planteada no corresponde al ámbito de aplicación del sistema.

**ÁMBITOS DE COMPETENCIA:**
- Legislación civil, penal y procesal
- Normativa laboral y administrativa  
- Códigos especializados (aduanero, electoral, sanitario)
- Organización judicial

Para consultas de otra naturaleza, diríjase a los servicios especializados correspondientes."""
                
                tiempo_procesamiento = time.time() - start_time
                actualizar_metricas(False, tiempo_procesamiento, "no_legal")
                
                return ConsultaResponse(
                    respuesta=respuesta_profesional,
                    fuente=None,
                    recomendaciones=None,
                    tiempo_procesamiento=round(tiempo_procesamiento, 2),
                    es_respuesta_oficial=True
                )
        
        # ========== CLASIFICACIÓN Y BÚSQUEDA PREMIUM ==========
        collection_name = clasificar_consulta_con_ia_robusta(pregunta_actual)
        logger.info(f"📚 Código legal identificado (PREMIUM): {collection_name}")
        
        # ========== BÚSQUEDA MULTI-MÉTODO CON VALIDACIÓN ==========
        contexto = None
        if VECTOR_SEARCH_AVAILABLE:
            contexto = buscar_con_manejo_errores(pregunta_actual, collection_name)
        
        # Validar contexto final con estándares premium
        contexto_valido = False
        if contexto and isinstance(contexto, dict) and contexto.get("pageContent"):
            es_valido, score_relevancia = validar_calidad_contexto(contexto, pregunta_actual)
            if es_valido and score_relevancia >= 0.3:  # Umbral premium
                contexto_valido = True
                logger.info(f"📖 Contexto PREMIUM validado:")
                logger.info(f"   - Ley: {contexto.get('nombre_ley', 'N/A')}")
                logger.info(f"   - Artículo: {contexto.get('numero_articulo', 'N/A')}")
                logger.info(f"   - Score relevancia: {score_relevancia:.2f}")
            else:
                logger.warning(f"❌ Contexto no cumple estándares premium (score: {score_relevancia:.2f})")
                contexto = None
        else:
            logger.warning("❌ No se encontró contexto legal para modo premium")
        
        # ========== GENERACIÓN DE RESPUESTA PREMIUM ==========
        respuesta = generar_respuesta_legal_premium(historial_limitado, contexto)
        
        # ========== PREPARAR RESPUESTA ESTRUCTURADA ==========
        tiempo_procesamiento = time.time() - start_time
        fuente = extraer_fuente_legal(contexto)
        
        # Actualizar métricas del sistema
        codigo_identificado = "desconocido"
        for nombre_codigo, collection in MAPA_COLECCIONES.items():
            if collection == collection_name:
                codigo_identificado = nombre_codigo
                break
        
        articulo_encontrado = contexto.get("numero_articulo") if contexto else None
        actualizar_metricas(contexto_valido, tiempo_procesamiento, codigo_identificado, articulo_encontrado)
        
        response_data = ConsultaResponse(
            respuesta=respuesta,
            fuente=fuente,
            recomendaciones=None,  # Modo premium sin recomendaciones automáticas
            tiempo_procesamiento=round(tiempo_procesamiento, 2),
            es_respuesta_oficial=True
        )
        
        logger.info(f"✅ Consulta PREMIUM procesada exitosamente en {tiempo_procesamiento:.2f}s")
        logger.info(f"🎯 Contexto encontrado: {contexto_valido}")
        
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error procesando consulta premium: {e}")
        
        # Actualizar métricas de error
        tiempo_procesamiento = time.time() - start_time
        actualizar_metricas(False, tiempo_procesamiento, "error")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Error interno del sistema premium",
                "mensaje": "No fue posible procesar su consulta legal en este momento",
                "recomendacion": "Intente nuevamente en unos momentos",
                "codigo_error": str(e)[:100],
                "timestamp": datetime.now().isoformat()
            }
        )

# === MANEJO DE ERRORES ===
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detalle": exc.detail,
            "timestamp": datetime.now().isoformat(),
            "mensaje_usuario": "Ha ocurrido un error procesando su consulta legal",
            "version": "3.2.0-PREMIUM"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Error no controlado en modo premium: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "detalle": "Error interno del servidor premium",
            "timestamp": datetime.now().isoformat(),
            "mensaje_usuario": "El sistema premium está experimentando dificultades técnicas",
            "version": "3.2.0-PREMIUM"
        }
    )

# === PUNTO DE ENTRADA ===
if __name__ == "__main__":
    logger.info("🚀 Iniciando COLEPA PREMIUM - Sistema Legal Gubernamental v3.2.0")
    logger.info("🏛️ Optimizado para Demo Congreso Nacional de Paraguay")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,  # Deshabilitado en producción
        log_level="info"
    )
