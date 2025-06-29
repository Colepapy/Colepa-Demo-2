# Archivo: app/main.py (Versión con Personalidad Profesional y Conversacional)

import os
import re
from fastapi import FastAPI, HTTPException
# Importar la herramienta de CORS
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

from app.vector_search import buscar_articulo_relevante, buscar_articulo_por_numero
from app.prompt_builder import construir_prompt

# --- Configuración Inicial ---
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI(
    title="Colepa API - Asistente Legal Inteligente",
    description="API para realizar consultas legales sobre múltiples cuerpos normativos de Paraguay.",
    version="3.0.0" # ¡Versión final!
)

# --- Configuración de CORS ---
origins = [
    "https://www.colepa.com",
    "http://localhost",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelos de Datos ---
class ConsultaRequest(BaseModel):
    pregunta: str

# --- Enrutador de Colecciones ---
MAPA_COLECCIONES = {
    "Código Aduanero": "colepa_aduanero_final",
    "Código Civil": "colepa_codigo_civil_final",
    "Código de la Niñez y la Adolescencia": "colepa_ninez_final",
    "Código de Organización Judicial": "colepa_organizacion_judicial_final",
    "Código Procesal Civil": "colepa_procesal_civil_final",
    "Código Procesal Penal": "colepa_procesal_penal_final",
    "Código Laboral": "colepa_laboral_final",
    "Código Electoral": "colepa_electoral_final",
    # Aquí puedes seguir añadiendo los códigos que faltan
}

def clasificar_pregunta(pregunta: str) -> str:
    """Usa un LLM para determinar a qué cuerpo legal pertenece la pregunta."""
    nombres_leyes = list(MAPA_COLECCIONES.keys())
    
    prompt_clasificacion = f"Dada la siguiente pregunta de un usuario, determina a cuál de estas áreas legales de Paraguay se refiere con mayor probabilidad: {nombres_leyes}. Responde únicamente con el nombre exacto de la ley de la lista. Pregunta del usuario: '{pregunta}'"
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_clasificacion}],
            temperature=0,
            max_tokens=25
        )
        clasificacion = response.choices[0].message.content.strip().replace('"', '')
        
        for ley, coleccion in MAPA_COLECCIONES.items():
            if ley in clasificacion:
                return coleccion
        
        print(f"Advertencia: Clasificación no reconocida '{clasificacion}'. Se intentará una búsqueda general.")
        return next(iter(MAPA_COLECCIONES.values()))
    except Exception as e:
        print(f"Error en la clasificación, se usará la primera colección por defecto: {e}")
        return next(iter(MAPA_COLECCIONES.values()))

# --- Endpoint Principal de la API ---
@app.post("/consulta", summary="Procesa una consulta legal usando un enrutador inteligente")
def procesar_consulta(request: ConsultaRequest):
    try:
        print(f"Clasificando la pregunta: '{request.pregunta}'")
        collection_a_usar = clasificar_pregunta(request.pregunta)
        print(f"Decisión del enrutador: Usar la colección '{collection_a_usar}'")

        contexto_payload = None
        match_articulo = re.search(r'art[ií]culo\s+([\d\.]+)', request.pregunta, re.IGNORECASE)

        if match_articulo:
            numero_str = match_articulo.group(1).replace('.', '')
            contexto_payload = buscar_articulo_por_numero(numero=int(numero_str), collection_name=collection_a_usar)
        else:
            embedding = openai_client.embeddings.create(model="text-embedding-ada-002", input=request.pregunta).data[0].embedding
            contexto_payload = buscar_articulo_relevante(query_vector=embedding, collection_name=collection_a_usar)

        if not contexto_payload:
            raise HTTPException(status_code=404, detail="No se encontró un artículo relevante para su consulta en la ley seleccionada.")
        
        texto_contexto = contexto_payload.get("pageContent", "")
        prompt_final = construir_prompt(contexto_legal=texto_contexto, pregunta_usuario=request.pregunta)
        
        # --- ¡AQUÍ ESTÁ LA NUEVA PERSONALIDAD DE COLEPA! ---
        instruccion_de_sistema = """
Eres COLEPA, un asistente legal virtual especializado exclusivamente en la legislación de la República del Paraguay.

Tu misión es asistir a profesionales del derecho y ciudadanos, proporcionando respuestas precisas, claras y directas.

Tu personalidad y reglas de comportamiento son las siguientes:
1.  **Tono:** Eres profesional, calmado y servicial. Tu lenguaje es siempre respetuoso, amigable y empático, pero manteniendo la seriedad que el ámbito legal requiere.
2.  **Base de Conocimiento:** Tu única fuente de verdad es el "Contexto legal proporcionado" en cada consulta. NUNCA debes usar conocimiento externo que puedas tener de tu entrenamiento previo. Toda tu respuesta debe derivar estricta y únicamente del texto que se te proporciona.
3.  **Límites:** Si la pregunta del usuario es sobre leyes de otros países (que no sean tratados internacionales en los que Paraguay es parte) o sobre temas no legales (como opiniones, deportes, etc.), debes responder amablemente que tu especialización es exclusivamente sobre las leyes de Paraguay y que no puedes asistir con esa consulta.
4.  **Incertidumbre:** Si el contexto proporcionado no contiene la información suficiente para responder a la pregunta del usuario de manera completa y precisa, debes indicarlo claramente. Di algo como: "Basado en el artículo proporcionado, no tengo la información suficiente para responder a tu pregunta con total certeza." No inventes ni supongas información.
5.  **Conversación:** Puedes mantener una conversación natural. Si un usuario te saluda ("Hola", "Buenas tardes"), responde amablemente y luego vuelve a ofrecer tu ayuda con consultas legales. Por ejemplo: "¡Hola! Soy COLEPA, tu asistente legal. ¿En qué puedo ayudarte hoy?".
"""
        
        chat_completion = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": instruccion_de_sistema}, # <-- Usamos la nueva instrucción detallada
                {"role": "user", "content": prompt_final}
            ]
        )
        respuesta = chat_completion.choices[0].message.content

        return {
            "respuesta": respuesta,
            "fuente": {
                "ley": contexto_payload.get("nombre_ley"),
                "articulo_numero": contexto_payload.get("numero_articulo"),
                "texto_fuente": texto_contexto
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
