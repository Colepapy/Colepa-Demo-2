# COLEPA - Backend FastAPI
# Archivo: main.py

import os
import re
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Verificar y configurar OpenAI
try:
    from openai import OpenAI
    from dotenv import load_dotenv
    
    load_dotenv()
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_AVAILABLE = True
    logger.info("OpenAI configurado correctamente")
except ImportError as e:
    logger.warning(f"OpenAI no disponible: {e}")
    OPENAI_AVAILABLE = False
    openai_client = None

# Importaciones locales con fallback
try:
    from app.vector_search import buscar_articulo_relevante, buscar_articulo_por_numero
    from app.prompt_builder import construir_prompt
    VECTOR_SEARCH_AVAILABLE = True
    logger.info("Módulos de búsqueda vectorial cargados")
except ImportError:
    logger.warning("Módulos de búsqueda no encontrados, usando funciones mock")
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

# === MODELOS PYDANTIC ===
class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|bot|system)$")
    content: str = Field(..., min_length=1, max_length=2000)
    timestamp: Optional[datetime] = None
    fuente: Optional[Dict[str, Any]] = None

class ConsultaRequest(BaseModel):
    historial: List[ChatMessage] = Field(..., min_items=1, max_items=50)
    metadata: Optional[Dict[str, Any]] = None

class ConsultaResponse(BaseModel):
    respuesta: str
    fuente: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None
    tiempo_procesamiento: Optional[float] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    openai_status: str
    vector_search_status: str

# === CONFIGURACIÓN ===
MAPA_COLECCIONES = {
    "Código Aduanero": "colepa_aduanero_final",
    "Código Civil": "colepa_codigo_civil_final",
    "Código de la Niñez y la Adolescencia": "colepa_ninez_final",
    "Código de Organización Judicial": "colepa_organizacion_judicial_final",
    "Código Procesal Civil": "colepa_procesal_civil_final",
    "Código Procesal Penal": "colepa_procesal_penal_final",
    "Código Laboral": "colepa_laboral_final",
    "Código Electoral": "colepa_electoral_final",
    "Código Penal": "colepa_penal_final",
    "Código de Ejecución Penal": "colepa_ejecucion_penal_final",
}

PALABRAS_CLAVE = {
    "Código Civil": ["civil", "matrimonio", "divorcio", "propiedad", "contratos", "familia", "herencia"],
    "Código Penal": ["penal", "delito", "crimen", "pena", "prisión", "robo", "homicidio"],
    "Código Laboral": ["laboral", "trabajo", "empleado", "salario", "vacaciones", "despido"],
    "Código Procesal Civil": ["proceso civil", "demanda", "juicio civil"],
    "Código Procesal Penal": ["proceso penal", "acusación", "juicio penal"],
    "Código Aduanero": ["aduana", "importación", "exportación", "aranceles"],
    "Código Electoral": ["electoral", "elecciones", "voto", "candidato"],
    "Código de la Niñez y la Adolescencia": ["menor", "niño", "adolescente", "tutela"],
    "Código de Organización Judicial": ["judicial", "tribunal", "juez", "competencia"],
    "Código de Ejecución Penal": ["ejecución penal", "prisión", "penitenciario"]
}

INSTRUCCION_SISTEMA = """
Eres COLEPA, un asistente legal virtual especializado en la legislación de Paraguay.

REGLAS:
1. Basa tus respuestas únicamente en el contexto legal proporcionado
2. Si no tienes información suficiente, indícalo claramente
3. No inventes información legal
4. Proporciona información general, no asesoramiento legal específico
5. Recomienda consultar con un abogado para casos específicos
6. Usa un lenguaje claro y comprensible
7. Cita las fuentes legales cuando sea posible

Responde de manera profesional, precisa y didáctica.
"""

# === CONFIGURACIÓN DE FASTAPI ===
app = FastAPI(
    title="COLEPA API - Asistente Legal",
    description="API para consultas legales sobre legislación paraguaya",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# === FUNCIONES AUXILIARES ===
def clasificar_pregunta(pregunta: str) -> str:
    """Clasifica la pregunta según las palabras clave"""
    pregunta_lower = pregunta.lower()
    scores = {}
    
    for ley, palabras in PALABRAS_CLAVE.items():
        score = sum(1 for palabra in palabras if palabra in pregunta_lower)
        if score > 0:
            scores[ley] = score
    
    # Buscar menciones explícitas
    for ley in MAPA_COLECCIONES.keys():
        if ley.lower() in pregunta_lower:
            scores[ley] = scores.get(ley, 0) + 10
    
    if scores:
        mejor_ley = max(scores.keys(), key=lambda k: scores[k])
        return MAPA_COLECCIONES[mejor_ley]
    
    return MAPA_COLECCIONES["Código Civil"]  # Default

def extraer_numero_articulo(texto: str) -> Optional[int]:
    """Extrae número de artículo del texto"""
    patrones = [
        r'art[ií]culo\s*n?[úu]?m?e?r?o?\s*([\d\.]+)',
        r'art\.?\s*([\d\.]+)',
        r'artículo\s*([\d\.]+)',
    ]
    
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            numero_str = match.group(1).replace('.', '')
            try:
                return int(numero_str)
            except ValueError:
                continue
    return None

def generar_respuesta_mock(pregunta: str, contexto: Optional[Dict] = None) -> str:
    """Genera una respuesta mock cuando OpenAI no está disponible"""
    if contexto:
        return f"""Basándome en el contexto legal proporcionado sobre {contexto.get('nombre_ley', 'la legislación')}, artículo {contexto.get('numero_articulo', 'N/A')}:

Para tu consulta sobre "{pregunta}", te puedo indicar que según la legislación paraguaya, es importante considerar los aspectos legales relevantes.

**Importante**: Esta es una respuesta de ejemplo. Para obtener asesoramiento legal específico sobre tu caso, te recomiendo consultar con un abogado especializado.

*Fuente: {contexto.get('nombre_ley', 'Legislación paraguaya')}*"""
    else:
        return f"""Respecto a tu consulta: "{pregunta}"

Lo siento, no pude encontrar información específica en la base de datos legal para responder tu pregunta de manera precisa.

Te recomiendo:
1. Reformular tu pregunta con términos más específicos
2. Mencionar el código o ley específica si la conoces
3. Consultar con un abogado para asesoramiento personalizado

**Importante**: Para casos específicos, siempre es recomendable consultar con un profesional del derecho."""

def generar_respuesta_con_openai(historial: List[ChatMessage], contexto: Optional[Dict] = None) -> str:
    """Genera respuesta usando OpenAI"""
    if not OPENAI_AVAILABLE or not openai_client:
        return generar_respuesta_mock(historial[-1].content, contexto)
    
    try:
        mensajes = [{"role": "system", "content": INSTRUCCION_SISTEMA}]
        
        # Agregar historial reciente
        for msg in historial[-5:]:  # Últimos 5 mensajes
            if msg.role != "system":
                role = "assistant" if msg.role == "bot" else msg.role
                mensajes.append({"role": role, "content": msg.content})
        
        # Si hay contexto, construir prompt especial
        if contexto:
            pregunta_actual = historial[-1].content
            prompt_con_contexto = construir_prompt(
                contexto_legal=contexto.get("pageContent", ""),
                pregunta_usuario=pregunta_actual
            )
            mensajes[-1] = {"role": "user", "content": prompt_con_contexto}
        
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=mensajes,
            temperature=0.3,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error con OpenAI: {e}")
        return generar_respuesta_mock(historial[-1].content, contexto)

# === MIDDLEWARE ===
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.2f}s")
    
    return response

# === ENDPOINTS ===
@app.get("/", response_model=HealthResponse)
async def root():
    """Endpoint raíz con información de salud"""
    return HealthResponse(
        status="active",
        timestamp=datetime.now(),
        version="2.0.0",
        openai_status="available" if OPENAI_AVAILABLE else "unavailable",
        vector_search_status="available" if VECTOR_SEARCH_AVAILABLE else "mock"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verificación de salud detallada"""
    openai_status = "unavailable"
    
    if OPENAI_AVAILABLE and openai_client:
        try:
            # Test simple
            openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            openai_status = "healthy"
        except Exception as e:
            openai_status = f"error: {str(e)[:50]}"
    
    return HealthResponse(
        status="active",
        timestamp=datetime.now(),
        version="2.0.0",
        openai_status=openai_status,
        vector_search_status="available" if VECTOR_SEARCH_AVAILABLE else "mock"
    )

@app.get("/colecciones")
async def listar_colecciones():
    """Lista todas las colecciones disponibles"""
    return {
        "colecciones": list(MAPA_COLECCIONES.keys()),
        "total": len(MAPA_COLECCIONES),
        "status": {
            "openai": OPENAI_AVAILABLE,
            "vector_search": VECTOR_SEARCH_AVAILABLE
        }
    }

@app.post("/consulta", response_model=ConsultaResponse)
async def procesar_consulta(request: ConsultaRequest, background_tasks: BackgroundTasks):
    """Endpoint principal para consultas legales"""
    start_time = time.time()
    
    try:
        historial = request.historial
        pregunta_actual = historial[-1].content
        
        logger.info(f"Procesando: {pregunta_actual[:100]}...")
        
        # Clasificar pregunta
        collection_name = clasificar_pregunta(pregunta_actual)
        logger.info(f"Colección: {collection_name}")
        
        # Buscar contexto
        contexto = None
        numero_articulo = extraer_numero_articulo(pregunta_actual)
        
        if VECTOR_SEARCH_AVAILABLE:
            if numero_articulo:
                contexto = buscar_articulo_por_numero(numero_articulo, collection_name)
            else:
                # Para búsqueda semántica necesitamos embedding
                if OPENAI_AVAILABLE:
                    try:
                        embedding = openai_client.embeddings.create(
                            model="text-embedding-ada-002",
                            input=pregunta_actual
                        ).data[0].embedding
                        contexto = buscar_articulo_relevante(embedding, collection_name)
                    except Exception as e:
                        logger.error(f"Error embedding: {e}")
                        contexto = buscar_articulo_relevante([], collection_name)
                else:
                    contexto = buscar_articulo_relevante([], collection_name)
        
        # Generar respuesta
        respuesta = generar_respuesta_con_openai(historial, contexto)
        
        # Preparar respuesta
        tiempo_procesamiento = time.time() - start_time
        
        fuente = None
        if contexto:
            fuente = {
                "ley": contexto.get("nombre_ley", "Desconocida"),
                "articulo_numero": str(contexto.get("numero_articulo", "N/A"))
            }
        
        return ConsultaResponse(
            respuesta=respuesta,
            fuente=fuente,
            tiempo_procesamiento=tiempo_procesamiento,
            metadata={
                "coleccion_utilizada": collection_name,
                "contexto_encontrado": bool(contexto),
                "modo": "openai" if OPENAI_AVAILABLE else "mock"
            }
        )
        
    except Exception as e:
        logger.error(f"Error procesando consulta: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando consulta: {str(e)}"
        )

# === MANEJO DE ERRORES ===
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error no controlado: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "detail": "Error interno del servidor",
            "timestamp": datetime.now().isoformat()
        }
    )

# === PUNTO DE ENTRADA ===
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
