# COLEPA - Asistente Legal Gubernamental
# Backend FastAPI Mejorado para Consultas Legales Oficiales

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

# === CONFIGURACIÓN DEL SISTEMA ===
MAPA_COLECCIONES = {
   "aduanero": "colepa_aduanero_maestro",
    "civil": "colepa_civil_maestro", 
    "electoral": "colepa_electoral_maestro",
    "laboral": "colepa_laboral_maestro",
    "ninezadolescencia": "colepa_ninezadolescencia_maestro",
    "organizacion_judicial": "colepa_organizacion_judicial_maestro",
    "penal": "colepa_penal_maestro",
    "procesal_civil": "colepa_procesal_civil_maestro",
    "procesal_penal": "colepa_procesal_penal_maestro",
    "sanitario": "colepa_sanitario_maestro"
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

# === PROMPT SIMPLIFICADO PARA TEXTO EXACTO ===
INSTRUCCION_SISTEMA_LEGAL = """
Eres COLEPA, el asistente legal oficial especializado en legislación paraguaya. 

INSTRUCCIONES CRÍTICAS:
1. **RESPUESTA DIRECTA INICIAL** (1-2 líneas)
   - Explica brevemente qué establece el artículo

2. **FUNDAMENTO LEGAL** (obligatorio)
   - Usa EXACTAMENTE el texto legal proporcionado
   - NO parafrasees, NO interpretes, USA EL TEXTO LITERAL
   - Cita claramente la ley y artículo

3. **NO AGREGUES:**
   - NO orientación práctica
   - NO recomendaciones  
   - NO pasos a seguir
   - NO "consulte con un abogado"

FORMATO:
[Explicación breve]

**Fundamento Legal:**
[TEXTO EXACTO DEL CONTEXTO]

FIN.

Usa ÚNICAMENTE el texto proporcionado en el contexto legal.
"""

# === CONFIGURACIÓN DE FASTAPI ===
app = FastAPI(
    title="COLEPA - Asistente Legal Oficial",
    description="Sistema de consultas legales basado en la legislación paraguaya",
    version="3.1.0",
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
    return MAPA_COLECCIONES["civil"]

def clasificar_consulta_con_ia_robusta(pregunta: str) -> str:
    """
    SÚPER ENRUTADOR: Clasificación robusta usando IA especializada
    FIX: Prompt ultra-corto y timeout para evitar error 500
    """
    if not OPENAI_AVAILABLE or not openai_client:
        logger.warning("⚠️ OpenAI no disponible, usando clasificación básica")
        return clasificar_consulta_inteligente(pregunta)
    
    try:
        # LOG SEGURO PARA DIAGNÓSTICO
        print(f"🧠 INICIO clasificar_consulta_con_ia_robusta")
        print(f"📝 Pregunta recibida: {pregunta[:100]}...")
        
        # PROMPT ULTRA-CORTO PARA EVITAR TIMEOUT
        prompt_ultra_corto = f"""
        Consulta: {pregunta[:150]}
        
        Responde solo con uno de estos códigos exactos:
        - Código Civil
        - Código Penal  
        - Código Laboral
        - Código Procesal Civil
        - Código Procesal Penal
        - Código Aduanero
        - Código Electoral
        - Código de la Niñez y la Adolescencia
        - Código de Organización Judicial
        - Código Sanitario
        
        Código:"""
        
        print("🔗 Llamando a OpenAI con prompt ultra-corto...")
        
        # LLAMADA CON TIMEOUT Y PARÁMETROS MÍNIMOS
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # Modelo más rápido
            messages=[{"role": "user", "content": prompt_ultra_corto}],
            temperature=0,  # Sin creatividad
            max_tokens=20,  # Máximo ultra-bajo
            timeout=15  # Timeout de 15 segundos
        )
        
        codigo_identificado = response.choices[0].message.content.strip()
        print(f"✅ OpenAI respondió: {codigo_identificado}")
        
        # Mapear respuesta a colección
        if codigo_identificado in MAPA_COLECCIONES:
            collection_name = MAPA_COLECCIONES[codigo_identificado]
            print(f"🎯 Mapeado exitosamente: {codigo_identificado} → {collection_name}")
            return collection_name
        else:
            # Fuzzy matching mejorado
            for codigo_oficial in MAPA_COLECCIONES.keys():
                if any(word in codigo_identificado.lower() for word in codigo_oficial.lower().split()):
                    collection_name = MAPA_COLECCIONES[codigo_oficial]
                    print(f"🎯 Mapeado fuzzy: {codigo_identificado} → {codigo_oficial}")
                    return collection_name
            
            # Fallback seguro
            print(f"⚠️ Código no reconocido: {codigo_identificado}, usando fallback")
            return clasificar_consulta_inteligente(pregunta)
            
    except Exception as e:
        print(f"🚨 ERROR en clasificar_consulta_con_ia_robusta: {type(e).__name__}: {str(e)}")
        print("🔄 Usando clasificación básica como fallback")
        return clasificar_consulta_inteligente(pregunta)

async def buscar_con_manejo_errores(numero_articulo, pregunta_actual, collection_name):
    """
    Función auxiliar para búsqueda con manejo robusto de errores Qdrant
    """
    contexto = None
    
    try:
        print(f"🔎 INICIO búsqueda - Artículo: {numero_articulo}, Colección: {collection_name}")
        
        if numero_articulo:
            # BÚSQUEDA POR NÚMERO EXACTO CON TIMEOUT
            print(f"🎯 Buscando artículo específico: {numero_articulo}")
            try:
                contexto = buscar_articulo_por_numero(numero_articulo, collection_name)
                print(f"✅ Búsqueda exacta completada: {type(contexto)}")
                
                if contexto and contexto.get("pageContent"):
                    print(f"✅ Artículo {numero_articulo} encontrado por búsqueda exacta")
                else:
                    print(f"❌ Artículo {numero_articulo} no encontrado, intentando búsqueda semántica")
                    contexto = None
                    
            except Exception as e:
                print(f"🚨 ERROR en buscar_articulo_por_numero: {str(e)}")
                contexto = None
        
        # BÚSQUEDA SEMÁNTICA CON MANEJO DE ERRORES
        if not contexto or not contexto.get("pageContent"):
            print("🔎 Iniciando búsqueda semántica...")
            
            if OPENAI_AVAILABLE:
                try:
                    # EMBEDDING CON TIMEOUT Y MANEJO DE ERRORES
                    print("🔢 Generando embedding...")
                    embedding_response = openai_client.embeddings.create(
                        model="text-embedding-ada-002",
                        input=pregunta_actual[:500],  # Limitar entrada
                        timeout=10  # Timeout de 10 segundos
                    )
                    query_vector = embedding_response.data[0].embedding
                    print(f"✅ Embedding generado: {len(query_vector)} dimensiones")
                    
                    # BÚSQUEDA VECTORIAL CON TIMEOUT
                    print("🗄️ Buscando en Qdrant...")
                    contexto = buscar_articulo_relevante(query_vector, collection_name)
                    print(f"✅ Búsqueda Qdrant completada: {type(contexto)}")
                    
                    if contexto and contexto.get("pageContent"):
                        print("✅ Contexto encontrado por búsqueda semántica")
                    else:
                        print("❌ No se encontró contexto en búsqueda semántica")
                        
                except Exception as e:
                    print(f"🚨 ERROR en búsqueda semántica: {str(e)}")
                    contexto = None
            else:
                print("⚠️ OpenAI no disponible para embeddings")
                
    except Exception as e:
        print(f"🚨 ERROR GENERAL en búsqueda: {type(e).__name__}: {str(e)}")
        contexto = None
    
    return contexto

def generar_respuesta_legal(historial: List[MensajeChat], contexto: Optional[Dict] = None) -> str:
    """
    FIX: Generación con límites estrictos para evitar error 422
    """
    if not OPENAI_AVAILABLE or not openai_client:
        return generar_respuesta_con_contexto(historial[-1].content, contexto)
    
    try:
        print("💭 INICIO generar_respuesta_legal")
        print(f"📊 Historial: {len(historial)} mensajes")
        print(f"📖 Contexto disponible: {bool(contexto and contexto.get('pageContent'))}")
        
        # LÍMITES ESTRICTOS PARA EVITAR ERROR 422
        mensajes = [{"role": "system", "content": INSTRUCCION_SISTEMA_LEGAL[:1000]}]  # Limitar instrucciones
        
        # MANEJO MEJORADO DEL CONTEXTO
        if contexto and contexto.get("pageContent"):
            contexto_limitado = contexto.get('pageContent', '')[:1500]  # Límite estricto
            prompt_limitado = construir_prompt(contexto_limitado, historial[-1].content[:300])
            
            # LIMITAR PROMPT TOTAL
            if len(prompt_limitado) > 2000:
                prompt_limitado = prompt_limitado[:2000] + "..."
            
            mensajes.append({"role": "user", "content": prompt_limitado})
            print(f"📖 Prompt construido: {len(prompt_limitado)} chars")
        else:
            # SIN CONTEXTO: Solo pregunta actual limitada
            pregunta_limitada = historial[-1].content[:300]
            mensajes.append({"role": "user", "content": pregunta_limitada})
            print(f"📝 Pregunta sin contexto: {len(pregunta_limitada)} chars")
        
        print("🔗 Llamando a OpenAI con límites estrictos...")
        
        # LLAMADA CON PARÁMETROS ULTRA-CONSERVADORES
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # Modelo más rápido y económico
            messages=mensajes,
            temperature=0.1,
            max_tokens=800,  # Límite reducido
            timeout=20,  # Timeout de 20 segundos
            presence_penalty=0,
            frequency_penalty=0
        )
        
        respuesta = response.choices[0].message.content
        print(f"✅ Respuesta generada: {len(respuesta)} chars")
        
        return respuesta
        
    except Exception as e:
        print(f"🚨 ERROR en generar_respuesta_legal: {type(e).__name__}: {str(e)}")
        print("🔄 Usando respuesta con contexto como fallback")
        return generar_respuesta_con_contexto(historial[-1].content, contexto)

def generar_respuesta_con_contexto(pregunta: str, contexto: Optional[Dict] = None) -> str:
    """
    Respuesta directa usando el contexto de Qdrant cuando OpenAI no está disponible
    """
    if contexto and contexto.get("pageContent"):
        # Usar el prompt_builder para consistencia
        contexto_legal_texto = contexto.get('pageContent', '')
        prompt_construido = construir_prompt(contexto_legal_texto, pregunta)
        
        # Respuesta básica usando el contexto
        ley = contexto.get('nombre_ley', 'Legislación paraguaya')
        articulo = contexto.get('numero_articulo', 'N/A')
        contenido = contexto.get('pageContent', '')
        
        response = f"""**{ley} - Artículo {articulo}**

{contenido}

---

**Aplicación a su consulta:**
Esta disposición legal responde a su pregunta sobre "{pregunta}".

**Nota importante:** Para asesoramiento específico sobre su situación particular, consulte con un abogado especializado.

*Fuente: {ley}, Artículo {articulo}*"""
        
        logger.info(f"✅ Respuesta generada con contexto: {ley} Art. {articulo}")
        return response
    else:
        return f"""**Consulta Legal**

No encontré esa disposición específica en mi base de datos legal para: "{pregunta}"

**Sugerencias:**
1. **Reformule su consulta** con términos más específicos
2. **Mencione el código o ley** específica si la conoce  
3. **Use números de artículo** si busca disposiciones particulares

**Consultas que puedo resolver:**
- Artículos específicos por número (ej: "artículo 95 del código aduanero")
- Temas generales (ej: "violencia doméstica", "derechos laborales")
- Procedimientos legales (ej: "cómo hacer una denuncia")

Para asesoramiento personalizado, consulte siempre con un abogado especializado.

*¿Puede reformular su consulta con más detalles específicos?*"""

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
        status="✅ Sistema COLEPA Operativo",
        timestamp=datetime.now(),
        version="3.1.0",
        servicios={
            "openai": "disponible" if OPENAI_AVAILABLE else "no disponible",
            "busqueda_vectorial": "disponible" if VECTOR_SEARCH_AVAILABLE else "modo_demo",
            "base_legal": "legislación paraguaya completa"
        },
        colecciones_disponibles=len(MAPA_COLECCIONES)
    )

@app.get("/api/health")
async def health_check():
    """Verificación de salud detallada"""
    health_status = {
        "sistema": "operativo",
        "timestamp": datetime.now().isoformat(),
        "version": "3.1.0",
        "servicios": {
            "openai": "❌ no disponible",
            "qdrant": "❌ no disponible" if not VECTOR_SEARCH_AVAILABLE else "✅ operativo",
            "base_legal": "✅ cargada"
        }
    }
    
    if OPENAI_AVAILABLE and openai_client:
        try:
            # Test mínimo de OpenAI
            openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            health_status["servicios"]["openai"] = "✅ operativo"
        except Exception as e:
            health_status["servicios"]["openai"] = f"❌ error: {str(e)[:50]}"
    
    return health_status

@app.get("/api/test-openai")
async def test_openai_connection():
    """
    Endpoint para probar conexión OpenAI específicamente
    """
    if not OPENAI_AVAILABLE:
        return {"status": "ERROR", "message": "OpenAI no configurado"}
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5,
            timeout=10
        )
        
        return {
            "status": "OK",
            "message": "OpenAI operativo",
            "model": "gpt-3.5-turbo",
            "response": response.choices[0].message.content
        }
        
    except Exception as e:
        return {
            "status": "ERROR", 
            "message": f"OpenAI error: {str(e)}",
            "error_type": type(e).__name__
        }

@app.get("/api/codigos")
async def listar_codigos_legales():
    """Lista todos los códigos legales disponibles"""
    return {
        "codigos_disponibles": list(MAPA_COLECCIONES.keys()),
        "total_codigos": len(MAPA_COLECCIONES),
        "descripcion": "Códigos legales completos de la República del Paraguay",
        "ultima_actualizacion": "2024",
        "cobertura": "Legislación nacional vigente"
    }

# ========== ENDPOINT PRINCIPAL MODIFICADO ==========
@app.post("/api/consulta", response_model=ConsultaResponse)
async def procesar_consulta_legal(
    request: ConsultaRequest, 
    background_tasks: BackgroundTasks
):
    """
    Endpoint principal - CON LOGGING DIAGNÓSTICO COMPLETO
    """
    start_time = time.time()
    
    try:
        print(f"🚀 INICIO ENDPOINT - Nueva consulta recibida")
        print(f"📊 Request: {len(request.historial)} mensajes en historial")
        
        historial = request.historial
        pregunta_actual = historial[-1].content
        print(f"📝 Pregunta actual: {pregunta_actual[:100]}...")
        
        # LÍMITE DE HISTORIAL PARA EVITAR ERROR 422
        MAX_HISTORIAL = 3  # MUY CONSERVADOR
        if len(historial) > MAX_HISTORIAL:
            historial_limitado = historial[-MAX_HISTORIAL:]
            print(f"⚠️ Historial limitado: {len(historial)} → {len(historial_limitado)} mensajes")
        else:
            historial_limitado = historial
        
        # CLASIFICACIÓN INTELIGENTE CON LOGGING
        if CLASIFICADOR_AVAILABLE:
            print("🧠 Iniciando clasificación inteligente...")
            try:
                clasificacion = clasificar_y_procesar(pregunta_actual)
                print(f"✅ Clasificación completada: {clasificacion.get('tipo_consulta', 'N/A')}")
                
                # MANEJO DE CONSULTAS CONVERSACIONALES
                if clasificacion['es_conversacional'] and clasificacion['respuesta_directa']:
                    print("💬 Generando respuesta conversacional...")
                    return ConsultaResponse(
                        respuesta=clasificacion['respuesta_directa'],
                        fuente=None,
                        recomendaciones=None,
                        tiempo_procesamiento=round(time.time() - start_time, 2),
                        es_respuesta_oficial=True
                    )
                
                if not clasificacion['requiere_busqueda']:
                    print("🚫 Consulta no legal, redirigiendo...")
                    return ConsultaResponse(
                        respuesta="Me especializo únicamente en consultas legales paraguayas. ¿Hay alguna pregunta legal específica en la que pueda ayudarte?",
                        fuente=None,
                        recomendaciones=None,
                        tiempo_procesamiento=round(time.time() - start_time, 2),
                        es_respuesta_oficial=True
                    )
                
                print("🔍 Consulta legal confirmada, procediendo...")
                
            except Exception as e:
                print(f"🚨 ERROR en clasificación: {str(e)}")
                print("🔄 Continuando sin clasificación...")
        
        # CLASIFICACIÓN DEL CÓDIGO LEGAL
        print("📚 Iniciando clasificación de código legal...")
        try:
            collection_name = clasificar_consulta_con_ia_robusta(pregunta_actual)
            print(f"✅ Código identificado: {collection_name}")
        except Exception as e:
            print(f"🚨 ERROR en clasificación de código: {str(e)}")
            collection_name = "colepa_civil_maestro"  # Fallback seguro
            print(f"🔄 Usando fallback: {collection_name}")
        
        # EXTRACCIÓN DE NÚMERO DE ARTÍCULO
        numero_articulo = extraer_numero_articulo_mejorado(pregunta_actual)
        print(f"🔢 Número de artículo extraído: {numero_articulo}")
        
        # BÚSQUEDA CON MANEJO DE ERRORES
        contexto = None
        if VECTOR_SEARCH_AVAILABLE:
            print("🔎 Iniciando búsqueda vectorial...")
            try:
                contexto = await buscar_con_manejo_errores(numero_articulo, pregunta_actual, collection_name)
                print(f"✅ Búsqueda completada: {bool(contexto and contexto.get('pageContent'))}")
            except Exception as e:
                print(f"🚨 ERROR en búsqueda: {str(e)}")
                contexto = None
        else:
            print("⚠️ Búsqueda vectorial no disponible")
        
        # GENERACIÓN DE RESPUESTA
        print("💭 Iniciando generación de respuesta...")
        try:
            respuesta = generar_respuesta_legal(historial_limitado, contexto)
            print(f"✅ Respuesta generada: {len(respuesta)} chars")
        except Exception as e:
            print(f"🚨 ERROR en generación: {str(e)}")
            respuesta = "Lo siento, no pude procesar tu consulta en este momento. Por favor, intenta reformular tu pregunta."
        
        # PREPARAR RESPUESTA FINAL
        tiempo_procesamiento = time.time() - start_time
        fuente = extraer_fuente_legal(contexto)
        
        response_data = ConsultaResponse(
            respuesta=respuesta,
            fuente=fuente,
            recomendaciones=None,
            tiempo_procesamiento=round(tiempo_procesamiento, 2),
            es_respuesta_oficial=True
        )
        
        print(f"🎉 Consulta procesada exitosamente en {tiempo_procesamiento:.2f}s")
        return response_data
        
    except Exception as e:
        print(f"🚨 ERROR CRÍTICO EN ENDPOINT: {type(e).__name__}: {str(e)}")
        print(f"🚨 Línea de error: {e.__traceback__.tb_lineno if e.__traceback__ else 'N/A'}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Error interno del sistema",
                "mensaje": "No fue posible procesar su consulta",
                "codigo_error": f"{type(e).__name__}: {str(e)[:100]}"
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
            "mensaje_usuario": "Ha ocurrido un error procesando su consulta"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Error no controlado: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "detalle": "Error interno del servidor",
            "timestamp": datetime.now().isoformat(),
            "mensaje_usuario": "El sistema está experimentando dificultades técnicas"
        }
    )

# === PUNTO DE ENTRADA ===
if __name__ == "__main__":
    logger.info("🚀 Iniciando COLEPA - Sistema Legal Gubernamental v3.1.0")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,  # Deshabilitado en producción
        log_level="info"
    )
