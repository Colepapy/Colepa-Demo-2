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
    from app.prompt_builder import construir_prompt_legal
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
    
    def construir_prompt_legal(contexto_legal, pregunta_usuario):
        return f"Contexto Legal: {contexto_legal}\n\nPregunta del Usuario: {pregunta_usuario}"

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

PALABRAS_CLAVE_EXPANDIDAS = {
    "Código Civil": [
        "civil", "matrimonio", "divorcio", "propiedad", "contratos", "familia", 
        "herencia", "sucesión", "sociedad conyugal", "bien ganancial", "patria potestad",
        "tutela", "curatela", "adopción", "filiación", "alimentos", "régimen patrimonial"
    ],
    "Código Penal": [
        "penal", "delito", "crimen", "pena", "prisión", "robo", "homicidio", "hurto",
        "estafa", "violación", "agresión", "lesiones", "amenaza", "extorsión", "secuestro",
        "narcotráfico", "corrupción", "fraude", "violencia doméstica", "femicidio"
    ],
    "Código Laboral": [
        "laboral", "trabajo", "empleado", "salario", "vacaciones", "despido", "contrato laboral",
        "indemnización", "aguinaldo", "licencia", "maternidad", "seguridad social", "sindicato",
        "huelga", "jornada laboral", "horas extras", "jubilación", "accidente laboral"
    ],
    "Código Procesal Civil": [
        "proceso civil", "demanda", "juicio civil", "sentencia", "apelación", "recurso",
        "prueba", "testigo", "peritaje", "embargo", "medida cautelar", "ejecución"
    ],
    "Código Procesal Penal": [
        "proceso penal", "acusación", "juicio penal", "fiscal", "defensor", "imputado",
        "querella", "investigación", "allanamiento", "detención", "prisión preventiva"
    ],
    "Código Aduanero": [
        "aduana", "importación", "exportación", "aranceles", "tributo aduanero", "mercancía",
        "declaración aduanera", "régimen aduanero", "zona franca", "contrabando"
    ],
    "Código Electoral": [
        "electoral", "elecciones", "voto", "candidato", "sufragio", "padrón electoral",
        "tribunal electoral", "campaña electoral", "partido político", "referendum"
    ],
    "Código de la Niñez y la Adolescencia": [
        "menor", "niño", "adolescente", "tutela", "adopción", "menor infractor",
        "protección integral", "derechos del niño", "consejería", "medida socioeducativa"
    ],
    "Código de Organización Judicial": [
        "judicial", "tribunal", "juez", "competencia", "jurisdicción", "corte suprema",
        "juzgado", "fuero", "instancia", "sala", "magistrado", "secretario judicial"
    ],
    "Código de Ejecución Penal": [
        "ejecución penal", "prisión", "penitenciario", "recluso", "libertad condicional",
        "régimen penitenciario", "trabajo penitenciario", "visita", "traslado", "redención"
    ]
}

# === PROMPTS DEL SISTEMA ===
INSTRUCCION_SISTEMA_LEGAL = """
Eres COLEPA, el asistente legal oficial especializado en la legislación paraguaya. 
Tu función es proporcionar información jurídica precisa basada EXCLUSIVAMENTE en las leyes de Paraguay.

PERSONALIDAD Y TONO:
- Profesional pero cercano y comprensible
- Empático ante situaciones delicadas
- Directo y claro en tus explicaciones
- Formal pero accesible para cualquier ciudadano

REGLAS ESTRICTAS:
1. SOLO utilizas información de los códigos legales paraguayos en tu base de datos
2. NUNCA inventes información legal
3. Si no tienes información específica, lo indicas claramente
4. Proporcionas el fundamento legal exacto (ley, artículo, inciso)
5. Para casos delicados (violencia, abusos), incluyes recomendaciones de acción inmediata
6. Recomiendas consultar un abogado para asesoramiento personalizado
7. No das consejos específicos, solo información general de la ley

FORMATO DE RESPUESTA:
- Explicación clara del marco legal aplicable
- Cita específica de artículos y leyes
- Consecuencias legales si aplica
- Recomendaciones generales
- Sugerencia de consulta profesional cuando sea necesario

CASOS ESPECIALES:
- Violencia doméstica: Prioriza información sobre protección y denuncia
- Casos penales: Explica tanto derechos del denunciante como del acusado
- Temas laborales: Incluye procedimientos ante el Ministerio de Trabajo
- Temas civiles: Explica procesos judiciales cuando sea relevante

Responde como un asesor legal institucional confiable del Estado paraguayo.
"""

# === CONFIGURACIÓN DE FASTAPI ===
app = FastAPI(
    title="COLEPA - Asistente Legal Oficial",
    description="Sistema de consultas legales basado en la legislación paraguaya",
    version="3.0.0",
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
def clasificar_consulta_inteligente(pregunta: str) -> str:
    """
    Clasificación inteligente mejorada de consultas legales
    """
    pregunta_lower = pregunta.lower()
    scores = {}
    
    # Búsqueda por palabras clave con peso
    for ley, palabras in PALABRAS_CLAVE_EXPANDIDAS.items():
        score = 0
        for palabra in palabras:
            if palabra in pregunta_lower:
                # Peso mayor para coincidencias exactas
                if f" {palabra} " in f" {pregunta_lower} ":
                    score += 3
                else:
                    score += 1
        
        if score > 0:
            scores[ley] = score
    
    # Búsqueda por menciones explícitas de códigos
    for ley in MAPA_COLECCIONES.keys():
        ley_variations = [
            ley.lower(),
            ley.lower().replace("código ", ""),
            ley.lower().replace(" ", "")
        ]
        
        for variation in ley_variations:
            if variation in pregunta_lower:
                scores[ley] = scores.get(ley, 0) + 15
    
    # Búsqueda por patrones específicos
    patrones_especiales = {
        r"violen(cia|to|tar)|agre(sión|dir)|golpe|maltrato": "Código Penal",
        r"matrimonio|divorcio|esposo|esposa|cónyuge": "Código Civil",
        r"trabajo|empleo|jefe|patrón|salario|sueldo": "Código Laboral",
        r"menor|niño|adolescente|hijo": "Código de la Niñez y la Adolescencia",
        r"elección|voto|candidato|político": "Código Electoral",
        r"juicio|demanda|tribunal|juez": "Código Procesal Civil",
        r"denuncia|fiscal|delito|acusado": "Código Procesal Penal"
    }
    
    for patron, ley in patrones_especiales.items():
        if re.search(patron, pregunta_lower):
            scores[ley] = scores.get(ley, 0) + 10
    
    # Determinar la mejor clasificación
    if scores:
        mejor_ley = max(scores.keys(), key=lambda k: scores[k])
        logger.info(f"Consulta clasificada como: {mejor_ley} (score: {scores[mejor_ley]})")
        return MAPA_COLECCIONES[mejor_ley]
    
    # Default: Código Civil (más general)
    logger.info("Consulta no clasificada específicamente, usando Código Civil por defecto")
    return MAPA_COLECCIONES["Código Civil"]

def extraer_numero_articulo_mejorado(texto: str) -> Optional[int]:
    """
    Extracción mejorada de números de artículo
    """
    patrones = [
        r'art[ií]culo\s*(?:n[úu]mero\s*)?(\d+)',
        r'art\.?\s*(\d+)',
        r'artículo\s*(\d+)',
        r'código\s*(\d+)',
        r'ley\s*(\d+)',
    ]
    
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            try:
                numero = int(match.group(1))
                logger.info(f"Número de artículo extraído: {numero}")
                return numero
            except ValueError:
                continue
    
    return None

def generar_respuesta_legal(historial: List[MensajeChat], contexto: Optional[Dict] = None) -> str:
    """
    Generación de respuesta legal con OpenAI
    """
    if not OPENAI_AVAILABLE or not openai_client:
        return generar_respuesta_mock_legal(historial[-1].content, contexto)
    
    try:
        # Preparar mensajes para OpenAI
        mensajes = [{"role": "system", "content": INSTRUCCION_SISTEMA_LEGAL}]
        
        # Agregar contexto legal si existe
        if contexto and contexto.get("pageContent"):
            contexto_msg = f"""
INFORMACIÓN LEGAL RELEVANTE:

Ley: {contexto.get('nombre_ley', 'No especificada')}
Artículo: {contexto.get('numero_articulo', 'No especificado')}

Contenido:
{contexto.get('pageContent', '')}

Utiliza ÚNICAMENTE esta información para responder la consulta del usuario.
"""
            mensajes.append({"role": "system", "content": contexto_msg})
        
        # Agregar historial (últimos 10 mensajes)
        for msg in historial[-10:]:
            role = "assistant" if msg.role == "assistant" else "user"
            mensajes.append({"role": role, "content": msg.content})
        
        # Llamada a OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=mensajes,
            temperature=0.1,  # Muy conservador para información legal
            max_tokens=1500,
            presence_penalty=0.1,
            frequency_penalty=0.1
        )
        
        respuesta = response.choices[0].message.content
        logger.info("✅ Respuesta generada con OpenAI")
        return respuesta
        
    except Exception as e:
        logger.error(f"❌ Error con OpenAI: {e}")
        return generar_respuesta_mock_legal(historial[-1].content, contexto)

def generar_respuesta_mock_legal(pregunta: str, contexto: Optional[Dict] = None) -> str:
    """
    Respuesta de respaldo cuando OpenAI no está disponible
    """
    if contexto:
        return f"""**Información Legal Encontrada**

Basándome en {contexto.get('nombre_ley', 'la legislación paraguaya')}, artículo {contexto.get('numero_articulo', 'N/A')}:

Para su consulta sobre "{pregunta}", el marco legal paraguayo establece disposiciones específicas que requieren análisis detallado.

**Recomendación importante:** Para obtener asesoramiento legal específico sobre su situación particular, le recomiendo consultar con un abogado especializado en la materia.

**Fuente legal:** {contexto.get('nombre_ley', 'Legislación paraguaya')}

*Esta es información general. Para casos específicos, consulte siempre con un profesional del derecho.*"""
    else:
        return f"""**Respuesta a su consulta**

Respecto a su pregunta: "{pregunta}"

Lamentablemente, no pude encontrar información específica en nuestra base de datos legal para brindarle una respuesta precisa sobre este tema.

**Le recomiendo:**
1. Reformular su consulta con términos más específicos
2. Mencionar el código o ley específica si la conoce  
3. Consultar directamente con un abogado para asesoramiento personalizado

**Importante:** COLEPA proporciona información legal general basada en la legislación paraguaya. Para casos específicos y asesoramiento personalizado, siempre es recomendable consultar con un profesional del derecho.

*¿Hay alguna forma específica en que pueda ayudarle a reformular su consulta?*"""

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
        version="3.0.0",
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
        "version": "3.0.0",
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

@app.post("/api/consulta", response_model=ConsultaResponse)
async def procesar_consulta_legal(
    request: ConsultaRequest, 
    background_tasks: BackgroundTasks
):
    """
    Endpoint principal para consultas legales oficiales
    """
    start_time = time.time()
    
    try:
        historial = request.historial
        pregunta_actual = historial[-1].content
        
        logger.info(f"🔍 Nueva consulta legal: {pregunta_actual[:100]}...")
        
        # Clasificar la consulta
        collection_name = clasificar_consulta_inteligente(pregunta_actual)
        logger.info(f"📚 Código legal identificado: {collection_name}")
        
        # Buscar información legal relevante
        contexto = None
        numero_articulo = extraer_numero_articulo_mejorado(pregunta_actual)
        
        if VECTOR_SEARCH_AVAILABLE:
            try:
                if numero_articulo:
                    # Búsqueda por número específico
                    logger.info(f"🔎 Buscando artículo específico: {numero_articulo}")
                    contexto = buscar_articulo_por_numero(numero_articulo, collection_name)
                else:
                    # Búsqueda semántica
                    if OPENAI_AVAILABLE:
                        embedding = openai_client.embeddings.create(
                            model="text-embedding-ada-002",
                            input=pregunta_actual
                        ).data[0].embedding
                        contexto = buscar_articulo_relevante(embedding, collection_name)
                    else:
                        contexto = buscar_articulo_relevante([], collection_name)
                
                if contexto:
                    logger.info(f"📖 Contexto legal encontrado: {contexto.get('nombre_ley')} - Art. {contexto.get('numero_articulo')}")
                    
            except Exception as e:
                logger.error(f"❌ Error en búsqueda vectorial: {e}")
                contexto = None
        
        # Generar respuesta legal
        respuesta = generar_respuesta_legal(historial, contexto)
        
        # Preparar respuesta estructurada
        tiempo_procesamiento = time.time() - start_time
        fuente = extraer_fuente_legal(contexto)
        
        # Generar recomendaciones generales
        recomendaciones = []
        if "violencia" in pregunta_actual.lower() or "maltrato" in pregunta_actual.lower():
            recomendaciones.extend([
                "En casos de violencia, comuníquese inmediatamente con la línea 137",
                "Puede acudir a cualquier comisaría para realizar la denuncia",
                "Solicite asesoramiento del Ministerio de la Mujer"
            ])
        elif "laboral" in pregunta_actual.lower():
            recomendaciones.append("Puede consultar en el Ministerio de Trabajo, Empleo y Seguridad Social")
        
        response_data = ConsultaResponse(
            respuesta=respuesta,
            fuente=fuente,
            recomendaciones=recomendaciones if recomendaciones else None,
            tiempo_procesamiento=round(tiempo_procesamiento, 2),
            es_respuesta_oficial=True
        )
        
        logger.info(f"✅ Consulta procesada exitosamente en {tiempo_procesamiento:.2f}s")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error procesando consulta: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Error interno del sistema",
                "mensaje": "No fue posible procesar su consulta en este momento",
                "recomendacion": "Intente nuevamente en unos momentos",
                "codigo_error": str(e)[:100]
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
    logger.info("🚀 Iniciando COLEPA - Sistema Legal Gubernamental")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,  # Deshabilitado en producción
        log_level="info"
    )
