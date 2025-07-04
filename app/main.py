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

# === CONFIGURACIÓN DEL SISTEMA - EXPANDIDO PARA 10 CÓDIGOS ===
MAPA_COLECCIONES = {
    "Código Aduanero": "colepa_aduanero_maestro",  # ✅ YA ACTIVO
    "Código Civil": "colepa_codigo_civil_maestro", 
    "Código de la Niñez y la Adolescencia": "colepa_ninez_maestro",
    "Código de Organización Judicial": "colepa_organizacion_judicial_maestro",
    "Código Procesal Civil": "colepa_procesal_civil_maestro", 
    "Código Procesal Penal": "colepa_procesal_penal_maestro",
    "Código Laboral": "colepa_laboral_maestro",
    "Código Electoral": "colepa_electoral_maestro",
    "Código Penal": "colepa_penal_maestro",
    "Código Sanitario": "colepa_sanitario_maestro",
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

# === PROMPT MEJORADO PARA TEXTO EXACTO ===
INSTRUCCION_SISTEMA_LEGAL = """
Eres COLEPA, el asistente legal oficial especializado en legislación paraguaya. Tu función es proporcionar el texto exacto de las leyes sin añadir interpretaciones o recomendaciones adicionales.

REGLAS CRÍTICAS PARA RESPUESTAS:

1. **RESPUESTA DIRECTA INICIAL** (1-2 líneas)
   - Responde la pregunta de forma directa y concisa
   - Ve directo al grano sin preámbulos

2. **FUNDAMENTO LEGAL EXACTO** (obligatorio)
   - Proporciona el texto legal EXACTO como aparece en la ley
   - NO interpretes, NO parafrasees, USA EL TEXTO LITERAL
   - Cita claramente la ley y artículo

3. **SIN ORIENTACIÓN ADICIONAL** (crítico)
   - NO agregues pasos prácticos
   - NO agregues recomendaciones  
   - NO agregues "consulte con un abogado"
   - NO agregues orientación sobre dónde acudir

ESTRUCTURA DE RESPUESTA:
- Respuesta directa (1-2 líneas)
- Fundamento legal con texto exacto
- FIN (no agregar nada más)

EJEMPLO CORRECTO:
Usuario: "¿Qué dice el artículo 15 del código aduanero?"

Respuesta:
"El artículo 15 establece los casos de exención de tributos aduaneros.

**Fundamento Legal:**
Código Aduanero, Artículo 15: [TEXTO EXACTO DEL ARTÍCULO COMO APARECE EN LA LEY]"

EJEMPLO INCORRECTO (NO hacer esto):
"El artículo 15 establece... [interpretación]
**Pasos a seguir:** [NO agregar esto]
**Recomendaciones:** [NO agregar esto]"

Usa ÚNICAMENTE el texto proporcionado en el contexto legal. Si no tienes el texto exacto, di que no tienes acceso a esa disposición específica.
"""

# === CONFIGURACIÓN DE FASTAPI ===
app = FastAPI(
    title="COLEPA - Asistente Legal Oficial",
    description="Sistema de consultas legales basado en la legislación paraguaya",
    version="3.2.0",
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
    return MAPA_COLECCIONES["Código Civil"]

def clasificar_consulta_con_ia_robusta(pregunta: str) -> str:
    """
    SÚPER ENRUTADOR: Clasificación robusta usando IA especializada
    """
    if not OPENAI_AVAILABLE or not openai_client:
        logger.warning("⚠️ OpenAI no disponible, usando clasificación básica")
        return clasificar_consulta_inteligente(pregunta)
    
    # PROMPT ESPECIALIZADO PARA CLASIFICACIÓN
    prompt_clasificacion = f"""
Eres un experto clasificador de consultas legales paraguayas. Tu única tarea es identificar a qué CÓDIGO LEGAL pertenece la siguiente consulta.

CÓDIGOS DISPONIBLES:
1. Código Civil - matrimonio, divorcio, familia, propiedad, contratos, herencia, adopción, tutela, bienes
2. Código Penal - delitos, crímenes, violencia, agresión, robo, homicidio, maltrato, femicidio, drogas
3. Código Laboral - trabajo, empleo, salarios, despidos, vacaciones, derechos laborales, sindicatos
4. Código Procesal Civil - demandas civiles, juicios civiles, daños y perjuicios, procedimientos civiles
5. Código Procesal Penal - denuncias penales, procesos penales, investigaciones, fiscalía
6. Código Aduanero - aduana, importación, exportación, mercancías, aranceles, depósitos, contrabando
7. Código Electoral - elecciones, votos, candidatos, partidos políticos, procesos electorales
8. Código de la Niñez y la Adolescencia - menores, niños, adolescentes, tutela de menores, adopción
9. Código de Organización Judicial - tribunales, jueces, competencias judiciales, organización courts
10. Código Sanitario - salud, medicina, hospitales, medicamentos, control sanitario

CONSULTA A CLASIFICAR: "{pregunta}"

CÓDIGO IDENTIFICADO:"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_clasificacion}],
            temperature=0.1,
            max_tokens=50
        )
        
        codigo_identificado = response.choices[0].message.content.strip()
        
        # Mapear respuesta a colección
        if codigo_identificado in MAPA_COLECCIONES:
            collection_name = MAPA_COLECCIONES[codigo_identificado]
            logger.info(f"🎯 IA clasificó correctamente: {codigo_identificado} → {collection_name}")
            return collection_name
        else:
            # Fuzzy matching para nombres similares
            for codigo_oficial in MAPA_COLECCIONES.keys():
                if any(word in codigo_identificado.lower() for word in codigo_oficial.lower().split()):
                    collection_name = MAPA_COLECCIONES[codigo_oficial]
                    logger.info(f"🎯 IA clasificó (fuzzy match): {codigo_identificado} → {codigo_oficial}")
                    return collection_name
            
            # Fallback
            logger.warning(f"⚠️ IA devolvió código no reconocido: {codigo_identificado}")
            return clasificar_consulta_inteligente(pregunta)
            
    except Exception as e:
        logger.error(f"❌ Error en clasificación con IA: {e}")
        return clasificar_consulta_inteligente(pregunta)

def generar_respuesta_legal(historial: List[MensajeChat], contexto: Optional[Dict] = None) -> str:
    """
    Generación de respuesta legal mejorada - TEXTO EXACTO ÚNICAMENTE
    """
    if not OPENAI_AVAILABLE or not openai_client:
        return generar_respuesta_con_contexto(historial[-1].content, contexto)
    
    try:
        # Preparar mensajes para OpenAI
        mensajes = [{"role": "system", "content": INSTRUCCION_SISTEMA_LEGAL}]
        
        # Agregar contexto legal si existe - USANDO PROMPT_BUILDER
        if contexto and contexto.get("pageContent"):
            contexto_legal_texto = contexto.get('pageContent', '')
            prompt_construido = construir_prompt(contexto_legal_texto, historial[-1].content)
            
            mensajes.append({"role": "user", "content": prompt_construido})
            logger.info(f"📖 Usando prompt_builder.py para contexto: {contexto.get('nombre_ley')} Art. {contexto.get('numero_articulo')}")
        else:
            # Sin contexto específico
            for msg in historial[-2:]:
                role = "assistant" if msg.role == "assistant" else "user"
                mensajes.append({"role": role, "content": msg.content})
        
        # Llamada a OpenAI con parámetros optimizados para TEXTO EXACTO
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=mensajes,
            temperature=0.0,  # COMPLETAMENTE CONSERVADOR - SIN CREATIVIDAD
            max_tokens=1000,  # REDUCIDO - Solo texto exacto
            presence_penalty=0,
            frequency_penalty=0
        )
        
        respuesta = response.choices[0].message.content
        logger.info("✅ Respuesta generada con OpenAI - Modo texto exacto")
        
        return respuesta
        
    except Exception as e:
        logger.error(f"❌ Error con OpenAI: {e}")
        return generar_respuesta_con_contexto(historial[-1].content, contexto)

def generar_respuesta_con_contexto(pregunta: str, contexto: Optional[Dict] = None) -> str:
    """
    Respuesta directa usando ÚNICAMENTE el contexto de Qdrant - SIN ORIENTACIÓN ADICIONAL
    """
    if contexto and contexto.get("pageContent"):
        ley = contexto.get('nombre_ley', 'Legislación paraguaya')
        articulo = contexto.get('numero_articulo', 'N/A')
        contenido = contexto.get('pageContent', '')
        
        # RESPUESTA SIMPLE - SOLO TEXTO EXACTO
        response = f"""**{ley} - Artículo {articulo}**

{contenido}

*Fuente: {ley}, Artículo {articulo}*"""
        
        logger.info(f"✅ Respuesta generada con contexto exacto: {ley} Art. {articulo}")
        return response
    else:
        return f"""**Consulta Legal**

No encontré esa disposición específica en mi base de datos legal para: "{pregunta}"

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
        version="3.2.0",
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
        "version": "3.2.0",
        "servicios": {
            "openai": "❌ no disponible",
            "qdrant": "❌ no disponible" if not VECTOR_SEARCH_AVAILABLE else "✅ operativo",
            "base_legal": "✅ cargada"
        }
    }
    
    if OPENAI_AVAILABLE and openai_client:
        try:
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

# ========== ENDPOINT PRINCIPAL MODIFICADO PARA TEXTO EXACTO ==========
@app.post("/api/consulta", response_model=ConsultaResponse)
async def procesar_consulta_legal(
    request: ConsultaRequest, 
    background_tasks: BackgroundTasks
):
    """
    Endpoint principal para consultas legales oficiales - TEXTO EXACTO ÚNICAMENTE
    """
    start_time = time.time()
    
    try:
        historial = request.historial
        pregunta_actual = historial[-1].content
        
        # Límite de historial para evitar error 422
        MAX_HISTORIAL = 6
        if len(historial) > MAX_HISTORIAL:
            historial_limitado = historial[-MAX_HISTORIAL:]
            logger.info(f"⚠️ Historial limitado a {len(historial_limitado)} mensajes")
        else:
            historial_limitado = historial
        
        logger.info(f"🔍 Nueva consulta legal: {pregunta_actual[:100]}...")
        
        # Clasificación inteligente (si está disponible)
        if CLASIFICADOR_AVAILABLE:
            logger.info("🧠 Iniciando clasificación inteligente...")
            clasificacion = clasificar_y_procesar(pregunta_actual)
            
            # Manejo de consultas conversacionales
            if clasificacion['es_conversacional'] and clasificacion['respuesta_directa']:
                logger.info("💬 Generando respuesta conversacional directa...")
                tiempo_procesamiento = time.time() - start_time
                
                return ConsultaResponse(
                    respuesta=clasificacion['respuesta_directa'],
                    fuente=None,
                    recomendaciones=None,  # SIN RECOMENDACIONES AUTOMÁTICAS
                    tiempo_procesamiento=round(tiempo_procesamiento, 2),
                    es_respuesta_oficial=True
                )
            
            # Manejo de consultas no legales
            if not clasificacion['requiere_busqueda']:
                logger.info("🚫 Consulta no legal, redirigiendo...")
                tiempo_procesamiento = time.time() - start_time
                
                return ConsultaResponse(
                    respuesta=clasificacion['respuesta_directa'] or 
                             "Me especializo únicamente en consultas sobre las leyes de Paraguay. "
                             "¿Hay alguna pregunta legal en la que pueda asistirte?",
                    fuente=None,
                    recomendaciones=None,  # SIN RECOMENDACIONES AUTOMÁTICAS
                    tiempo_procesamiento=round(tiempo_procesamiento, 2),
                    es_respuesta_oficial=True
                )
        
        # Clasificar la consulta legal
        collection_name = clasificar_consulta_con_ia_robusta(pregunta_actual)
        logger.info(f"📚 Código legal identificado: {collection_name}")
        
        # Buscar información legal relevante
        contexto = None
        numero_articulo = extraer_numero_articulo_mejorado(pregunta_actual)
        
        if VECTOR_SEARCH_AVAILABLE:
            try:
                if numero_articulo:
                    # Búsqueda por número exacto
                    logger.info(f"🎯 Buscando artículo específico: {numero_articulo} en {collection_name}")
                    contexto = buscar_articulo_por_numero(numero_articulo, collection_name)
                    
                    if contexto and contexto.get("pageContent"):
                        logger.info(f"✅ Artículo {numero_articulo} encontrado por búsqueda exacta")
                    else:
                        logger.warning(f"❌ Artículo {numero_articulo} no encontrado por búsqueda exacta")
                        
                        # FALLBACK: Búsqueda semántica con número en el texto
                        if OPENAI_AVAILABLE:
                            logger.info(f"🔄 Intentando búsqueda semántica para artículo {numero_articulo}")
                            
                            consulta_semantica = f"artículo {numero_articulo} código penal civil procesal laboral"
                            
                            embedding_response = openai_client.embeddings.create(
                                model="text-embedding-ada-002",
                                input=consulta_semantica
                            )
                            query_vector = embedding_response.data[0].embedding
                            
                            contexto_semantico = buscar_articulo_relevante(query_vector, collection_name)
                            
                            if (contexto_semantico and 
                                contexto_semantico.get("pageContent") and 
                                str(numero_articulo) in contexto_semantico.get("pageContent", "")):
                                
                                contexto = contexto_semantico
                                logger.info(f"✅ Artículo {numero_articulo} encontrado por búsqueda semántica")
                            else:
                                logger.warning(f"❌ Búsqueda semántica no encontró artículo {numero_articulo}")
                                contexto = None
                
                # Búsqueda semántica general si no se buscó por número o no se encontró
                if not contexto or not contexto.get("pageContent"):
                    logger.info(f"🔎 Realizando búsqueda semántica general en {collection_name}")
                    
                    if OPENAI_AVAILABLE:
                        embedding_response = openai_client.embeddings.create(
                            model="text-embedding-ada-002",
                            input=pregunta_actual
                        )
                        query_vector = embedding_response.data[0].embedding
                        contexto = buscar_articulo_relevante(query_vector, collection_name)
                        
                        if contexto and contexto.get("pageContent"):
                            logger.info("✅ Contexto encontrado por búsqueda semántica general")
                        else:
                            logger.warning("❌ No se encontró contexto por búsqueda semántica")
                    else:
                        # Fallback sin OpenAI
                        contexto = buscar_articulo_relevante([], collection_name)
                        
            except Exception as e:
                logger.error(f"❌ Error en búsqueda vectorial: {e}")
                contexto = None

        # Validar contexto final
        if contexto and isinstance(contexto, dict) and contexto.get("pageContent"):
            logger.info(f"📖 Contexto legal final:")
            logger.info(f"   - Ley: {contexto.get('nombre_ley', 'N/A')}")
            logger.info(f"   - Artículo: {contexto.get('numero_articulo', 'N/A')}")
            logger.info(f"   - Contenido: {contexto.get('pageContent', '')[:200]}...")
        else:
            logger.warning("❌ No se encontró contexto legal relevante para la consulta")
            contexto = None
        
        # Generar respuesta legal - SOLO TEXTO EXACTO
        respuesta = generar_respuesta_legal(historial_limitado, contexto)
        
        # Preparar respuesta estructurada - SIN RECOMENDACIONES AUTOMÁTICAS
        tiempo_procesamiento = time.time() - start_time
        fuente = extraer_fuente_legal(contexto)
        
        # NO GENERAR RECOMENDACIONES AUTOMÁTICAS - ELIMINADO COMPLETAMENTE
        recomendaciones = None  # SIEMPRE None - Sin orientación automática
        
        response_data = ConsultaResponse(
            respuesta=respuesta,
            fuente=fuente,
            recomendaciones=recomendaciones,  # SIEMPRE None
            tiempo_procesamiento=round(tiempo_procesamiento, 2),
            es_respuesta_oficial=True
        )
        
        logger.info(f"✅ Consulta procesada exitosamente en {tiempo_procesamiento:.2f}s")
        if CLASIFICADOR_AVAILABLE and 'clasificacion' in locals():
            logger.info(f"🏷️ Tipo clasificado: {clasificacion.get('tipo_consulta', 'N/A')}")
        
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
    logger.info("🚀 Iniciando COLEPA - Sistema Legal Gubernamental v3.2.0")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
        log_level="info"
    )
