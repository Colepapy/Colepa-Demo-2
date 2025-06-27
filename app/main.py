# Archivo: app/main.py (Versión Final con Enrutador Inteligente Multi-Ley)

import os
import re
from fastapi import FastAPI, HTTPException
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

# --- Modelos de Datos ---
class ConsultaRequest(BaseModel):
    pregunta: str

# --- Enrutador de Colecciones ---
# El mapa que le da al gerente el conocimiento de toda la biblioteca
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
            model="gpt-3.5-turbo", # Usamos un modelo rápido y económico para esta tarea simple
            messages=[{"role": "user", "content": prompt_clasificacion}],
            temperature=0,
            max_tokens=25 # Una respuesta corta es suficiente
        )
        clasificacion = response.choices[0].message.content.strip().replace('"', '')
        
        for ley, coleccion in MAPA_COLECCIONES.items():
            if ley in clasificacion:
                return coleccion
        
        print(f"Advertencia: Clasificación no reconocida '{clasificacion}'. Se intentará una búsqueda general.")
        # Futura lógica: Si no se reconoce, se podría buscar en una colección general o devolver un error.
        # Por ahora, usamos la primera como defecto.
        return next(iter(MAPA_COLECCIONES.values()))
    except Exception as e:
        print(f"Error en la clasificación, se usará la primera colección por defecto: {e}")
        return next(iter(MAPA_COLECCIONES.values()))

# --- Endpoint Principal de la API ---
@app.post("/consulta", summary="Procesa una consulta legal usando un enrutador inteligente")
def procesar_consulta(request: ConsultaRequest):
    try:
        # --- PASO 0: CLASIFICAR Y ELEGIR COLECCIÓN ---
        print(f"Clasificando la pregunta: '{request.pregunta}'")
        collection_a_usar = clasificar_pregunta(request.pregunta)
        print(f"Decisión del enrutador: Usar la colección '{collection_a_usar}'")

        contexto_payload = None
        match_articulo = re.search(r'art[ií]culo\s+([\d\.]+)', request.pregunta, re.IGNORECASE)

        if match_articulo:
            # ESTRATEGIA 1: BÚSQUEDA EXACTA
            numero_str = match_articulo.group(1).replace('.', '')
            contexto_payload = buscar_articulo_por_numero(numero=int(numero_str), collection_name=collection_a_usar)
        else:
            # ESTRATEGIA 2: BÚSQUEDA SEMÁNTICA
            embedding = openai_client.embeddings.create(model="text-embedding-ada-002", input=request.pregunta).data[0].embedding
            contexto_payload = buscar_articulo_relevante(query_vector=embedding, collection_name=collection_a_usar)

        if not contexto_payload:
            raise HTTPException(status_code=404, detail="No se encontró un artículo relevante para su consulta en la ley seleccionada.")
        
        texto_contexto = contexto_payload.get("pageContent", "")
        prompt_final = construir_prompt(contexto_legal=texto_contexto, pregunta_usuario=request.pregunta)
        
        chat_completion = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt_final}]
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