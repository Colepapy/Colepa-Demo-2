# COLEPA - Sistema Legal Inteligente de Paraguay
# Versión: 4.0.0 NASDAQ Edition
# Arquitectura: FastAPI + Mock Database + GPT-4 + Cache System

import os
import re
import sys
import time
import json
import logging
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# ========== CONFIGURACIÓN DE PATHS ==========
current_dir = Path(__file__).parent
root_dir = current_dir.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(current_dir))

# ========== LOGGING PROFESIONAL ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== IMPORTAR OpenAI ==========
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

# ========== IMPORTAR MOCK SEARCH ==========
try:
    from app.mock_search import buscar_articulo_relevante, buscar_articulo_por_numero
    VECTOR_SEARCH_AVAILABLE = True
    logger.info("✅ Mock Search Engine cargado - 25 artículos disponibles")
except ImportError as e:
    logger.warning(f"⚠️ Mock search no disponible: {e}")
    VECTOR_SEARCH_AVAILABLE = False
    
    def buscar_articulo_relevante(query):
        return None
    
    def buscar_articulo_por_numero(numero):
        return None

# ========== CLASIFICADOR INTELIGENTE ==========
try:
    from app.clasificador_inteligente import clasificar_y_procesar
    CLASIFICADOR_AVAILABLE = True
    logger.info("✅ Clasificador inteligente cargado")
except ImportError as e:
    logger.warning(f"⚠️ Clasificador fallback: {e}")
    CLASIFICADOR_AVAILABLE = False
    
    def clasificar_y_procesar(texto):
        texto_lower = texto.lower().strip()
        
        saludos = ['hola', 'buenos días', 'buenas tardes', 'hey']
        if any(s in texto_lower for s in saludos):
            return {
                'tipo_consulta': 'saludo',
                'respuesta_directa': "¡Hola! Soy COLEPA, tu asistente legal paraguayo. ¿En qué puedo ayudarte?",
                'requiere_busqueda': False,
                'es_conversacional': True
            }
        
        despedidas = ['adiós', 'chau', 'hasta luego', 'gracias']
        if any(d in texto_lower for d in despedidas):
            return {
                'tipo_consulta': 'despedida',
                'respuesta_directa': "¡Hasta luego! Que tengas un excelente día.",
                'requiere_busqueda': False,
                'es_conversacional': True
            }
        
        return {
            'tipo_consulta': 'consulta_legal',
            'respuesta_directa': None,
            'requiere_busqueda': True,
            'es_conversacional': False
        }

# ========== CACHE SYSTEM NASDAQ ==========
class CacheManager:
    """Sistema de cache de 3 niveles para optimización máxima"""
    
    def __init__(self, max_memory_mb: int = 100):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        self.cache_clasificaciones = {}
        self.ttl_clasificaciones = 3600
        
        self.cache_contextos = {}
        self.ttl_contextos = 86400
        
        self.cache_respuestas = {}
        self.ttl_respuestas = 21600
        
        self.hits_clasificaciones = 0
        self.hits_contextos = 0
        self.hits_respuestas = 0
        self.misses_total = 0
        
        self.cleanup_lock = threading.RLock()
        self.start_cleanup_thread()
        
        logger.info(f"🚀 CacheManager inicializado - Límite: {max_memory_mb}MB")
    
    def _normalize_query(self, text: str) -> str:
        if not text:
            return ""
        normalized = text.lower().strip()
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()
    
    def _generate_hash(self, *args) -> str:
        content = "|".join(str(arg) for arg in args if arg is not None)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_expired(self, timestamp: float, ttl: int) -> bool:
        return time.time() - timestamp > ttl
    
    def _cleanup_expired(self):
        with self.cleanup_lock:
            current_time = time.time()
            
            for cache, ttl in [
                (self.cache_clasificaciones, self.ttl_clasificaciones),
                (self.cache_contextos, self.ttl_contextos),
                (self.cache_respuestas, self.ttl_respuestas)
            ]:
                expired = [k for k, (_, ts) in cache.items() if current_time - ts > ttl]
                for key in expired:
                    del cache[key]
    
    def start_cleanup_thread(self):
        def cleanup_worker():
            while True:
                try:
                    time.sleep(300)
                    self._cleanup_expired()
                except Exception as e:
                    logger.error(f"❌ Error en cleanup: {e}")
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()
    
    def get_respuesta(self, historial: List, contexto: Optional[Dict]) -> Optional[str]:
        historial_text = " ".join([msg.content for msg in historial[-3:]])
        normalized = self._normalize_query(historial_text)
        
        contexto_hash = ""
        if contexto:
            contexto_hash = self._generate_hash(
                contexto.get('nombre_ley', ''),
                contexto.get('numero_articulo', '')
            )
        
        cache_key = self._generate_hash(normalized, contexto_hash)
        
        if cache_key in self.cache_respuestas:
            respuesta, timestamp = self.cache_respuestas[cache_key]
            if not self._is_expired(timestamp, self.ttl_respuestas):
                self.hits_respuestas += 1
                logger.info(f"🎯 CACHE HIT - Respuesta")
                return respuesta
            else:
                del self.cache_respuestas[cache_key]
        
        self.misses_total += 1
        return None
    
    def set_respuesta(self, historial: List, contexto: Optional[Dict], respuesta: str):
        historial_text = " ".join([msg.content for msg in historial[-3:]])
        normalized = self._normalize_query(historial_text)
        
        contexto_hash = ""
        if contexto:
            contexto_hash = self._generate_hash(
                contexto.get('nombre_ley', ''),
                contexto.get('numero_articulo', '')
            )
        
        cache_key = self._generate_hash(normalized, contexto_hash)
        self.cache_respuestas[cache_key] = (respuesta, time.time())
    
    def get_stats(self) -> Dict:
        total_hits = self.hits_clasificaciones + self.hits_contextos + self.hits_respuestas
        total_requests = total_hits + self.misses_total
        hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hit_rate_percentage": round(hit_rate, 1),
            "total_hits": total_hits,
            "total_misses": self.misses_total,
            "entradas_cache": {
                "clasificaciones": len(self.cache_clasificaciones),
                "contextos": len(self.cache_contextos),
                "respuestas": len(self.cache_respuestas)
            }
        }

cache_manager = CacheManager(max_memory_mb=100)

# ========== MODELOS PYDANTIC ==========
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
    articulos_disponibles: int

# ========== CONFIGURACIÓN ==========
MAX_TOKENS_RESPUESTA = 400
MAX_TOKENS_CONTEXTO = 600

INSTRUCCION_SISTEMA_NASDAQ = """Eres COLEPA, asistente jurídico especializado en legislación paraguaya.

INSTRUCCIONES:
- Responde de forma clara, profesional pero accesible
- Cita artículos específicos cuando estén disponibles
- Máximo 300 palabras
- Usa formato conversacional, no telegráfico

ESTRUCTURA:
1. Respuesta directa a la consulta
2. Artículo aplicable (si existe)
3. Explicación práctica

Terminología jurídica precisa pero comprensible."""

# ========== MÉTRICAS ==========
metricas_sistema = {
    "consultas_procesadas": 0,
    "contextos_encontrados": 0,
    "tiempo_promedio": 0.0,
    "ultima_actualizacion": datetime.now()
}

# ========== FUNCIONES AUXILIARES ==========
def extraer_numero_articulo_mejorado(texto: str) -> Optional[int]:
    """Extracción optimizada de números de artículo"""
    texto_lower = texto.lower().strip()
    
    patrones = [
        r'art[íi]culo\s*(?:n[úu]mero\s*)?(\d+)',
        r'art\.?\s*(\d+)',
        r'artículo\s*(\d+)',
        r'articulo\s*(\d+)',
        r'(?:^|\s)(\d+)(?:\s+del\s+c[óo]digo)',
    ]
    
    for patron in patrones:
        matches = re.finditer(patron, texto_lower)
        for match in matches:
            try:
                numero = int(match.group(1))
                if 1 <= numero <= 9999:
                    logger.info(f"✅ Artículo extraído: {numero}")
                    return numero
            except (ValueError, IndexError):
                continue
    
    return None

def validar_calidad_contexto(contexto: Optional[Dict], pregunta: str) -> tuple[bool, float]:
    """Validación de relevancia del contexto"""
    if not contexto or not contexto.get("pageContent"):
        return False, 0.0
    
    try:
        texto_contexto = contexto.get("pageContent", "").lower()
        pregunta_lower = pregunta.lower()
        
        # Validación por número de artículo
        numero_pregunta = extraer_numero_articulo_mejorado(pregunta)
        numero_contexto = contexto.get("numero_articulo")
        
        if numero_pregunta and numero_contexto:
            if str(numero_contexto) == str(numero_pregunta):
                logger.info(f"✅ Match exacto - Art. {numero_pregunta}")
                return True, 1.0
        
        # Validación semántica
        palabras_pregunta = set(re.findall(r'\b\w{4,}\b', pregunta_lower))
        palabras_contexto = set(re.findall(r'\b\w{4,}\b', texto_contexto))
        
        if len(palabras_pregunta) == 0:
            return False, 0.0
        
        interseccion = palabras_pregunta & palabras_contexto
        score_basico = len(interseccion) / len(palabras_pregunta)
        
        # Bonus por longitud
        if len(texto_contexto) > 100:
            score_basico += 0.1
        
        es_valido = score_basico >= 0.2
        
        logger.info(f"🎯 Validación: Score {score_basico:.2f} - Válido: {es_valido}")
        return es_valido, score_basico
        
    except Exception as e:
        logger.error(f"❌ Error validando contexto: {e}")
        return False, 0.0

def buscar_con_manejo_errores(pregunta: str) -> Optional[Dict]:
    """Búsqueda robusta con mock database"""
    logger.info(f"🔍 Búsqueda: '{pregunta[:100]}...'")
    
    contexto_final = None
    
    # Método 1: Por número de artículo
    numero_articulo = extraer_numero_articulo_mejorado(pregunta)
    if numero_articulo and VECTOR_SEARCH_AVAILABLE:
        try:
            contexto = buscar_articulo_por_numero(numero_articulo)
            if contexto:
                es_valido, score = validar_calidad_contexto(contexto, pregunta)
                if es_valido:
                    contexto_final = contexto
                    logger.info(f"✅ Encontrado por número - Art. {numero_articulo}")
        except Exception as e:
            logger.error(f"❌ Error búsqueda por número: {e}")
    
    # Método 2: Búsqueda semántica
    if not contexto_final and VECTOR_SEARCH_AVAILABLE:
        try:
            contexto = buscar_articulo_relevante(pregunta)
            if contexto:
                es_valido, score = validar_calidad_contexto(contexto, pregunta)
                if es_valido:
                    contexto_final = contexto
                    logger.info(f"✅ Encontrado por semántica - Score: {score:.2f}")
        except Exception as e:
            logger.error(f"❌ Error búsqueda semántica: {e}")
    
    return contexto_final

def generar_respuesta_legal_nasdaq(historial: List[MensajeChat], contexto: Optional[Dict] = None) -> str:
    """Generación de respuesta premium con GPT-4"""
    
    # Cache check
    respuesta_cached = cache_manager.get_respuesta(historial, contexto)
    if respuesta_cached:
        return respuesta_cached
    
    if not OPENAI_AVAILABLE or not openai_client:
        return generar_respuesta_fallback(historial[-1].content, contexto)
    
    try:
        pregunta_actual = historial[-1].content
        
        mensajes = [{"role": "system", "content": INSTRUCCION_SISTEMA_NASDAQ}]
        
        if contexto and contexto.get("pageContent"):
            ley = contexto.get('nombre_ley', 'Legislación paraguaya')
            articulo = contexto.get('numero_articulo', 'N/A')
            contenido = contexto.get('pageContent', '')
            
            prompt = f"""**Consulta:** {pregunta_actual}

**Artículo encontrado:**
{ley}, Artículo {articulo}

**Texto legal:**
{contenido}

Responde de forma profesional y accesible."""
            
            mensajes.append({"role": "user", "content": prompt})
        else:
            mensajes.append({"role": "user", "content": f"Consulta legal: {pregunta_actual}\n\nNo se encontró artículo específico. Responde con información general legal paraguaya."})
        
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=mensajes,
            temperature=0.3,
            max_tokens=MAX_TOKENS_RESPUESTA,
            timeout=25
        )
        
        respuesta = response.choices[0].message.content
        
        if hasattr(response, 'usage'):
            logger.info(f"💰 Tokens: Input {response.usage.prompt_tokens}, Output {response.usage.completion_tokens}")
        
        # Cache save
        cache_manager.set_respuesta(historial, contexto, respuesta)
        
        return respuesta
        
    except Exception as e:
        logger.error(f"❌ Error GPT-4: {e}")
        return generar_respuesta_fallback(historial[-1].content, contexto)

def generar_respuesta_fallback(pregunta: str, contexto: Optional[Dict] = None) -> str:
    """Fallback cuando no hay OpenAI"""
    if contexto and contexto.get("pageContent"):
        ley = contexto.get('nombre_ley', 'Código')
        articulo = contexto.get('numero_articulo', 'N/A')
        contenido = contexto.get('pageContent', '')
        
        return f"""**Consulta legal:** {pregunta}

**Artículo aplicable:**
{ley}, Artículo {articulo}

**Texto legal:**
{contenido}

**Nota:** Esta es la disposición legal relevante encontrada en nuestra base de datos. Para asesoramiento específico sobre tu caso, consulta con un abogado."""
    
    return f"""**Consulta:** {pregunta}

No se encontró un artículo específico para esta consulta en nuestra base de datos actual.

**Recomendación:**
1. Reformula la consulta con más detalles
2. Especifica el código legal de interés
3. Menciona número de artículo si lo conoces

Para consultas específicas, es recomendable contactar con un profesional del derecho."""

def extraer_fuente_legal(contexto: Optional[Dict]) -> Optional[FuenteLegal]:
    if not contexto:
        return None
    
    return FuenteLegal(
        ley=contexto.get("nombre_ley", "No especificada"),
        articulo_numero=str(contexto.get("numero_articulo", "N/A")),
        libro=contexto.get("libro"),
        titulo=contexto.get("titulo")
    )

def actualizar_metricas(tiene_contexto: bool, tiempo: float):
    global metricas_sistema
    
    metricas_sistema["consultas_procesadas"] += 1
    if tiene_contexto:
        metricas_sistema["contextos_encontrados"] += 1
    
    total = metricas_sistema["consultas_procesadas"]
    anterior = metricas_sistema["tiempo_promedio"]
    metricas_sistema["tiempo_promedio"] = ((anterior * (total - 1)) + tiempo) / total
    metricas_sistema["ultima_actualizacion"] = datetime.now()

# ========== FASTAPI APP ==========
app = FastAPI(
    title="COLEPA - Asistente Legal NASDAQ Edition",
    description="Sistema profesional de consultas legales paraguayas",
    version="4.0.0-NASDAQ",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS
@app.middleware("http")
async def cors_handler(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== ENDPOINTS ==========
@app.get("/", response_model=StatusResponse)
async def sistema_status():
    return StatusResponse(
        status="✅ COLEPA NASDAQ Edition Operativo",
        timestamp=datetime.now(),
        version="4.0.0-NASDAQ",
        servicios={
            "openai": "disponible" if OPENAI_AVAILABLE else "no disponible",
            "database": "mock_local_25_articulos",
            "cache": "activo_3_niveles",
            "modo": "PRODUCTION_READY"
        },
        articulos_disponibles=25
    )

@app.get("/api/health")
async def health_check():
    return {
        "sistema": "operativo",
        "timestamp": datetime.now().isoformat(),
        "version": "4.0.0-NASDAQ",
        "servicios": {
            "openai": "✅" if OPENAI_AVAILABLE else "❌",
            "database": "✅ Mock Local (25 artículos)",
            "cache": "✅ Operativo",
            "clasificador": "✅" if CLASIFICADOR_AVAILABLE else "⚠️ Fallback"
        },
        "cache_stats": cache_manager.get_stats()
    }

@app.get("/api/metricas")
async def obtener_metricas():
    global metricas_sistema
    
    total = metricas_sistema["consultas_procesadas"]
    encontrados = metricas_sistema["contextos_encontrados"]
    exito = (encontrados / total * 100) if total > 0 else 0
    
    return {
        "estado": "✅ NASDAQ Edition",
        "version": "4.0.0",
        "timestamp": datetime.now().isoformat(),
        "metricas": {
            "total_consultas": total,
            "contextos_encontrados": encontrados,
            "porcentaje_exito": round(exito, 1),
            "tiempo_promedio_ms": round(metricas_sistema["tiempo_promedio"] * 1000, 2)
        },
        "cache": cache_manager.get_stats()
    }

@app.post("/api/consulta", response_model=ConsultaResponse)
async def procesar_consulta_legal_nasdaq(request: ConsultaRequest):
    start_time = time.time()
    
    try:
        historial = request.historial
        pregunta_actual = historial[-1].content
        
        # Limitar historial
        MAX_HISTORIAL = 3
        if len(historial) > MAX_HISTORIAL:
            historial_limitado = historial[-MAX_HISTORIAL:]
        else:
            historial_limitado = historial
        
        logger.info(f"📥 Nueva consulta: {pregunta_actual[:100]}...")
        
        # Clasificación
        if CLASIFICADOR_AVAILABLE:
            clasificacion = clasificar_y_procesar(pregunta_actual)
            
            if clasificacion['es_conversacional'] and clasificacion['respuesta_directa']:
                tiempo = time.time() - start_time
                actualizar_metricas(False, tiempo)
                
                return ConsultaResponse(
                    respuesta=clasificacion['respuesta_directa'],
                    fuente=None,
                    recomendaciones=None,
                    tiempo_procesamiento=round(tiempo, 2),
                    es_respuesta_oficial=True
                )
        
        # Búsqueda
        contexto = None
        if VECTOR_SEARCH_AVAILABLE:
            contexto = buscar_con_manejo_errores(pregunta_actual)
        
        # Generar respuesta
        respuesta = generar_respuesta_legal_nasdaq(historial_limitado, contexto)
        
        # Preparar response
        tiempo = time.time() - start_time
        fuente = extraer_fuente_legal(contexto)
        
        actualizar_metricas(contexto is not None, tiempo)
        
        logger.info(f"✅ Consulta procesada en {tiempo:.2f}s")
        
        return ConsultaResponse(
            respuesta=respuesta,
            fuente=fuente,
            recomendaciones=None,
            tiempo_procesamiento=round(tiempo, 2),
            es_respuesta_oficial=True
        )
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        tiempo = time.time() - start_time
        actualizar_metricas(False, tiempo)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Error procesando consulta",
                "timestamp": datetime.now().isoformat()
            }
        )

# ========== ERROR HANDLERS ==========
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detalle": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Error no controlado: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "detalle": "Error interno del servidor",
            "timestamp": datetime.now().isoformat()
        }
    )

# ========== ENTRY POINT ==========
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 COLEPA NASDAQ Edition v4.0.0 iniciando en puerto {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        access_log=True
    )
