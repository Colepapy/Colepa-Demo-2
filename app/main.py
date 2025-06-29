# COLEPA - Backend FastAPI Mejorado
# Archivo: app/main.py

import os
import re
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from openai import OpenAI
from dotenv import load_dotenv

# Importaciones locales (asumiendo que estos módulos existen)
try:
    from app.vector_search import buscar_articulo_relevante, buscar_articulo_por_numero
    from app.prompt_builder import construir_prompt
except ImportError:
    # Fallback para desarrollo
    print("Módulos de búsqueda no encontrados, usando funciones mock")
    def buscar_articulo_relevante(query_vector, collection_name):
        return {"pageContent": "Contenido de ejemplo", "nombre_ley": "Código Civil", "numero_articulo": "123"}
    def buscar_articulo_por_numero(numero, collection_name):
        return {"pageContent": "Contenido de ejemplo", "nombre_ley": "Código Civil", "numero_articulo": str(numero)}
    def construir_prompt(contexto_legal, pregunta_usuario):
        return f"Contexto: {contexto_legal}\n\nPregunta: {pregunta_usuario}"

# === CONFIGURACIÓN INICIAL ===
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cliente OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === MODELOS PYDANTIC ===
class ChatMessage(BaseModel):
    role: str = Field(..., regex="^(user|bot|system)$")
    content: str = Field(..., min_length=1, max_length=2000)
    timestamp: Optional[datetime] = None
    fuente: Optional[Dict[str, Any]] = None

    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        return v or datetime.now()

class ConsultaRequest(BaseModel):
    historial: List[ChatMessage] = Field(..., min_items=1, max_items=50)
    metadata: Optional[Dict[str, Any]] = None

    @validator('historial')
    def validate_historial(cls, v):
        if not v:
            raise ValueError('El historial no puede estar vacío')
        
        # Verificar que el último mensaje sea del usuario
        if v[-1].role != 'user':
            raise ValueError('El último mensaje debe ser del usuario')
        
        return v

class ConsultaResponse(BaseModel):
    respuesta: str
    fuente: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None
    tiempo_procesamiento: Optional[float] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    api_status: str

class BusquedaRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    coleccion: Optional[str] = None
    limite: Optional[int] = Field(default=5, ge=1, le=20)

class EstadisticasResponse(BaseModel):
    total_consultas: int
    tiempo_promedio: float
    colecciones_mas_usadas: Dict[str, int]
    tasa_exito: float

# === CONFIGURACIÓN DE MAPEO DE COLECCIONES ===
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

# Palabras clave para clasificación mejorada
PALABRAS_CLAVE_CLASIFICACION = {
    "Código Civil": ["civil", "matrimonio", "divorcio", "propiedad", "contratos", "familia", "herencia", "bienes"],
    "Código Penal": ["penal", "delito", "crimen", "pena", "prisión", "robo", "homicidio", "lesiones"],
    "Código Laboral": ["laboral", "trabajo", "empleado", "salario", "vacaciones", "despido", "sindicato"],
    "Código Procesal Civil": ["proceso civil", "demanda", "juicio civil", "procedimiento civil"],
    "Código Procesal Penal": ["proceso penal", "acusación", "juicio penal", "procedimiento penal"],
    "Código Aduanero": ["aduana", "importación", "exportación", "aranceles", "comercio exterior"],
    "Código Electoral": ["electoral", "elecciones", "voto", "candidato", "partido político"],
    "Código de la Niñez y la Adolescencia": ["menor", "niño", "adolescente", "tutela", "adopción"],
    "Código de Organización Judicial": ["judicial", "tribunal", "juez", "competencia", "jurisdicción"],
    "Código de Ejecución Penal": ["ejecución penal", "prisión", "penitenciario", "régimen penitenciario"]
}

# === INSTRUCCIONES DEL SISTEMA ===
INSTRUCCION_SISTEMA = """
Eres COLEPA, un asistente legal virtual especializado en la legislación de Paraguay. 

CARACTERÍSTICAS DE TU PERSONALIDAD:
- Profesional pero accesible
- Empático y paciente 
- Preciso y confiable
- Didáctico en tus explicaciones

REGLAS FUNDAMENTALES:
1. Basa ÚNICAMENTE tus respuestas en el contexto legal proporcionado
2. Si no tienes información suficiente, indícalo claramente
3. No inventes información legal
4. No proporciones asesoramiento legal específico, solo información general
5. Siempre recomienda consultar con un abogado para casos específicos
6. No respondas sobre leyes de otros países
7. Usa un lenguaje claro y comprensible
8. Estructura tus respuestas de manera organizada
9. Cita siempre las fuentes legales cuando sea posible

FORMATO DE RESPUESTA:
- Respuesta clara y directa
- Explicación del contexto legal relevante
- Referencia a artículos específicos cuando aplique
- Advertencia sobre la necesidad de asesoramiento profesional si es necesario
"""

# === VARIABLES GLOBALES PARA ESTADÍSTICAS ===
estadisticas_consultas = {
    "total_consultas": 0,
    "tiempo_total": 0.0,
    "colecciones_usadas": {},
    "consultas_exitosas": 0
}

# === FUNCIÓN DE CONTEXTO DE APLICACIÓN ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Iniciando COLEPA API")
    
    # Verificar conexión con OpenAI
    try:
        test_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )
        logger.info("Conexión con OpenAI verificada")
    except Exception as e:
        logger.error(f"Error conectando con OpenAI: {e}")
    
    yield
    
    # Shutdown
    logger.info("Cerrando COLEPA API")

# === CONFIGURACIÓN DE FASTAPI ===
app = FastAPI(
    title="COLEPA API - Asistente Legal Inteligente",
    description="API avanzada para realizar consultas legales sobre múltiples cuerpos normativos de Paraguay",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# === CONFIGURACIÓN DE MIDDLEWARE ===

# CORS
origins = [
    "https://www.colepa.com",
    "https://colepa.com",
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted Host
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # En producción, especificar hosts exactos
)

# === FUNCIONES AUXILIARES ===

def clasificar_pregunta_avanzada(pregunta: str) -> str:
    """
    Clasificación mejorada de preguntas usando múltiples estrategias
    """
    pregunta_lower = pregunta.lower()
    scores = {}
    
    # 1. Búsqueda por palabras clave
    for ley, palabras in PALABRAS_CLAVE_CLASIFICACION.items():
        score = sum(1 for palabra in palabras if palabra in pregunta_lower)
        if score > 0:
            scores[ley] = scores.get(ley, 0) + score * 2
    
    # 2. Búsqueda por menciones explícitas de códigos
    for ley in MAPA_COLECCIONES.keys():
        if ley.lower() in pregunta_lower:
            scores[ley] = scores.get(ley, 0) + 10
    
    # 3. Clasificación con OpenAI como respaldo
    if not scores:
        try:
            nombres_leyes = list(MAPA_COLECCIONES.keys())
            prompt_clasificacion = f"""
            Clasifica la siguiente pregunta legal según corresponda a una de estas áreas del derecho paraguayo:
            {nombres_leyes}
            
            Pregunta: "{pregunta}"
            
            Responde únicamente con el nombre exacto de la ley más relevante de la lista.
            """
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt_clasificacion}],
                temperature=0,
                max_tokens=50
            )
            
            clasificacion = response.choices[0].message.content.strip().replace('"', '')
            
            # Verificar que la respuesta esté en nuestro mapeo
            for ley in MAPA_COLECCIONES.keys():
                if ley in clasificacion:
                    return MAPA_COLECCIONES[ley]
                    
        except Exception as e:
            logger.error(f"Error en clasificación con OpenAI: {e}")
    
    # Devolver la ley con mayor puntaje o default
    if scores:
        mejor_ley = max(scores.keys(), key=lambda k: scores[k])
        return MAPA_COLECCIONES[mejor_ley]
    
    # Default: Código Civil (más general)
    return MAPA_COLECCIONES["Código Civil"]

def extraer_numero_articulo(texto: str) -> Optional[int]:
    """
    Extrae número de artículo de un texto con múltiples patrones
    """
    patrones = [
        r'art[ií]culo\s*n?[úu]?m?e?r?o?\s*([\d\.]+)',
        r'art\.?\s*([\d\.]+)',
        r'artículo\s*([\d\.]+)',
        r'articulo\s*([\d\.]+)',
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

def optimizar_consulta_embedding(pregunta: str) -> str:
    """
    Optimiza la pregunta para búsqueda por embedding
    """
    # Remover palabras de parada específicas del contexto legal
    palabras_parada = ['qué', 'cómo', 'cuándo', 'dónde', 'por qué', 'para qué']
    
    palabras = pregunta.split()
    palabras_filtradas = [p for p in palabras if p.lower() not in palabras_parada]
    
    return ' '.join(palabras_filtradas) if palabras_filtradas else pregunta

def generar_respuesta_con_contexto(historial: List[ChatMessage], contexto_payload: Optional[Dict]) -> str:
    """
    Genera respuesta usando el contexto legal y el historial de conversación
    """
    # Preparar mensajes para la IA
    mensajes_para_ia = [{"role": "system", "content": INSTRUCCION_SISTEMA}]
    
    # Agregar historial (limitado a los últimos 10 mensajes para eficiencia)
    historial_reciente = historial[-10:] if len(historial) > 10 else historial
    
    for msg in historial_reciente[:-1]:  # Todos excepto el último
        mensajes_para_ia.append({
            "role": "assistant" if msg.role == "bot" else msg.role,
            "content": msg.content
        })
    
    # Procesar la pregunta actual
    pregunta_actual = historial[-1].content
    
    if contexto_payload:
        texto_contexto = contexto_payload.get("pageContent", "")
        prompt_con_contexto = construir_prompt(
            contexto_legal=texto_contexto, 
            pregunta_usuario=pregunta_actual
        )
        mensajes_para_ia.append({"role": "user", "content": prompt_con_contexto})
    else:
        mensajes_para_ia.append({"role": "user", "content": pregunta_actual})
    
    # Generar respuesta
    try:
        chat_completion = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=mensajes_para_ia,
            temperature=0.3,  # Ligeramente creativo pero preciso
            max_tokens=1000,
            presence_penalty=0.1,
            frequency_penalty=0.1
        )
        
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error generando respuesta: {e}")
        return "Lo siento, ha ocurrido un error interno. Por favor, intenta reformular tu pregunta."

def validar_api_key():
    """
    Valida que la API key de OpenAI esté configurada
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY no está configurada en las variables de entorno")
    return True

# === MIDDLEWARE PERSONALIZADO ===
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log de request
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Log de response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.2f}s")
    
    return response

# === ENDPOINTS ===

@app.get("/", response_model=HealthResponse)
async def root():
    """Endpoint de salud de la API"""
    return HealthResponse(
        status="active",
        timestamp=datetime.now(),
        version="2.0.0",
        api_status="operational"
    )

@app.get("/health", response_model=HealthResponse) 
async def health_check():
    """Verificación de salud detallada"""
    try:
        # Verificar conexión OpenAI
        validar_api_key()
        test_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )
        api_status = "healthy"
    except Exception as e:
        api_status = f"unhealthy: {str(e)}"
        logger.error(f"Health check failed: {e}")
    
    return HealthResponse(
        status="active",
        timestamp=datetime.now(),
        version="2.0.0",
        api_status=api_status
    )

@app.get("/colecciones")
async def listar_colecciones():
    """Lista todas las colecciones disponibles"""
    return {
        "colecciones": list(MAPA_COLECCIONES.keys()),
        "total": len(MAPA_COLECCIONES),
        "mapa_interno": MAPA_COLECCIONES
    }

@app.get("/estadisticas", response_model=EstadisticasResponse)
async def obtener_estadisticas():
    """Obtiene estadísticas de uso de la API"""
    total_consultas = estadisticas_consultas["total_consultas"]
    tiempo_promedio = (
        estadisticas_consultas["tiempo_total"] / total_consultas 
        if total_consultas > 0 else 0.0
    )
    tasa_exito = (
        estadisticas_consultas["consultas_exitosas"] / total_consultas 
        if total_consultas > 0 else 1.0
    )
    
    return EstadisticasResponse(
        total_consultas=total_consultas,
        tiempo_promedio=tiempo_promedio,
        colecciones_mas_usadas=estadisticas_consultas["colecciones_usadas"],
        tasa_exito=tasa_exito
    )

@app.post("/busqueda")
async def busqueda_directa(request: BusquedaRequest):
    """
    Endpoint para búsqueda directa en las colecciones sin procesamiento de IA
    """
    try:
        # Determinar colección
        if request.coleccion and request.coleccion in MAPA_COLECCIONES.values():
            collection_name = request.coleccion
        else:
            collection_name = clasificar_pregunta_avanzada(request.query)
        
        # Generar embedding para búsqueda
        embedding = openai_client.embeddings.create(
            model="text-embedding-ada-002", 
            input=request.query
        ).data[0].embedding
        
        # Buscar artículos relevantes
        resultados = []
        for i in range(request.limite):
            resultado = buscar_articulo_relevante(
                query_vector=embedding,
                collection_name=collection_name
            )
            if resultado:
                resultados.append(resultado)
        
        return {
            "query": request.query,
            "coleccion_utilizada": collection_name,
            "total_resultados": len(resultados),
            "resultados": resultados
        }
        
    except Exception as e:
        logger.error(f"Error en búsqueda directa: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error realizando la búsqueda"
        )

@app.post("/consulta", response_model=ConsultaResponse)
async def procesar_consulta(
    request: ConsultaRequest, 
    background_tasks: BackgroundTasks
):
    """
    Endpoint principal para procesar consultas legales
    """
    start_time = time.time()
    
    try:
        historial_usuario = request.historial
        pregunta_actual = historial_usuario[-1].content
        
        logger.info(f"Procesando consulta: {pregunta_actual[:100]}...")
        
        # Clasificar la pregunta
        collection_a_usar = clasificar_pregunta_avanzada(pregunta_actual)
        logger.info(f"Colección seleccionada: {collection_a_usar}")
        
        contexto_payload = None
        
        # Buscar contexto relevante
        numero_articulo = extraer_numero_articulo(pregunta_actual)
        
        if numero_articulo:
            # Búsqueda por número de artículo específico
            logger.info(f"Buscando artículo específico: {numero_articulo}")
            contexto_payload = buscar_articulo_por_numero(
                numero=numero_articulo, 
                collection_name=collection_a_usar
            )
        else:
            # Búsqueda por similaridad semántica
            consulta_optimizada = optimizar_consulta_embedding(pregunta_actual)
            
            try:
                embedding = openai_client.embeddings.create(
                    model="text-embedding-ada-002", 
                    input=consulta_optimizada
                ).data[0].embedding
                
                contexto_payload = buscar_articulo_relevante(
                    query_vector=embedding, 
                    collection_name=collection_a_usar
                )
            except Exception as e:
                logger.error(f"Error generando embedding: {e}")
        
        # Generar respuesta
        respuesta = generar_respuesta_con_contexto(historial_usuario, contexto_payload)
        
        # Preparar metadata
        tiempo_procesamiento = time.time() - start_time
        
        # Preparar fuente
        fuente = None
        if contexto_payload:
            fuente = {
                "ley": contexto_payload.get("nombre_ley", "Desconocida"),
                "articulo_numero": str(contexto_payload.get("numero_articulo", "N/A"))
            }
        
        # Log para analytics (en background)
        background_tasks.add_task(
            log_consulta_analytics,
            pregunta_actual,
            collection_a_usar,
            tiempo_procesamiento,
            bool(contexto_payload)
        )
        
        return ConsultaResponse(
            respuesta=respuesta,
            fuente=fuente,
            tiempo_procesamiento=tiempo_procesamiento,
            metadata={
                "coleccion_utilizada": collection_a_usar,
                "contexto_encontrado": bool(contexto_payload),
                "articulo_especifico": numero_articulo is not None
            }
        )
        
    except Exception as e:
        logger.error(f"Error procesando consulta: {e}")
        
        # Actualizar estadísticas de error
        estadisticas_consultas["total_consultas"] += 1
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Error interno del servidor",
                "message": "Ha ocurrido un error procesando tu consulta. Por favor, intenta nuevamente.",
                "tipo": "error_procesamiento"
            }
        )

@app.post("/validar-prompt")
async def validar_prompt(request: Dict[str, str]):
    """
    Endpoint para validar y probar prompts antes de usar en producción
    """
    try:
        prompt_test = request.get("prompt", "")
        
        if not prompt_test:
            raise HTTPException(status_code=400, detail="Prompt no puede estar vacío")
        
        # Probar el prompt con OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_test}],
            max_tokens=100,
            temperature=0
        )
        
        return {
            "prompt_valido": True,
            "respuesta_prueba": response.choices[0].message.content,
            "tokens_utilizados": response.usage.total_tokens if response.usage else 0
        }
        
    except Exception as e:
        return {
            "prompt_valido": False,
            "error": str(e)
        }

# === FUNCIONES DE BACKGROUND TASKS ===
async def log_consulta_analytics(
    pregunta: str, 
    coleccion: str, 
    tiempo: float, 
    contexto_encontrado: bool
):
    """
    Log de analytics para métricas y mejoras futuras
    """
    analytics_data = {
        "timestamp": datetime.now().isoformat(),
        "pregunta_length": len(pregunta),
        "coleccion": coleccion,
        "tiempo_procesamiento": tiempo,
        "contexto_encontrado": contexto_encontrado,
    }
    
    # Actualizar estadísticas globales
    estadisticas_consultas["total_consultas"] += 1
    estadisticas_consultas["tiempo_total"] += tiempo
    
    if contexto_encontrado:
        estadisticas_consultas["consultas_exitosas"] += 1
    
    # Actualizar contador de colecciones usadas
    if coleccion in estadisticas_consultas["colecciones_usadas"]:
        estadisticas_consultas["colecciones_usadas"][coleccion] += 1
    else:
        estadisticas_consultas["colecciones_usadas"][coleccion] = 1
    
    # En producción, aquí se podría enviar a un sistema de analytics
    # como Google Analytics, Mixpanel, o guardar en base de datos
    logger.info(f"Analytics registrado: {analytics_data}")

# === MANEJO DE ERRORES GLOBALES ===
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Manejo personalizado de excepciones HTTP
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Manejo de excepciones generales no controladas
    """
    logger.error(f"Error no controlado: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "detail": "Error interno del servidor",
            "message": "Ha ocurrido un error inesperado",
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        }
    )

# === PUNTO DE ENTRADA ===
if __name__ == "__main__":
    import uvicorn
    
    # Configuración para desarrollo
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
