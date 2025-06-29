# Archivo: app/main.py (Versión Final con Lógica Conversacional)

import os
import re
from fastapi import FastAPI, HTTPException
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
    version="4.0.0" # Versión Conversacional
)

# --- Configuración de CORS ---
origins = ["https://www.colepa.com", "http://localhost", "http://localhost:8000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- Modelos de Datos ---
class ConsultaRequest(BaseModel):
    pregunta: str

# --- Enrutador de Colecciones ---
MAPA_COLECCIONES = {
    # ... (tu mapa de colecciones completo aquí) ...
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

def clasificar_pregunta(pregunta: str) -> str | None:
    nombres_leyes = list(MAPA_COLECCIONES.keys())
    prompt_clasificacion = f"Dada la siguiente pregunta, determina si se refiere a una de estas áreas legales de Paraguay: {nombres_leyes}. Si la pregunta es un saludo, una despedida, una pregunta casual o no es de temática legal, responde 'N/A'. De lo contrario, responde únicamente con el nombre exacto de la ley de la lista. Pregunta: '{pregunta}'"
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_clasificacion}],
            temperature=0, max_tokens=50
        )
        clasificacion = response.choices[0].message.content.strip().replace('"', '')
        
        if clasificacion == 'N/A':
            return None # Es una pregunta casual/conversacional
        
        for ley, coleccion in MAPA_COLECCIONES.items():
            if ley in clasificacion:
                return coleccion
        
        return "fallback" # Si no está seguro, podemos buscar en todas
    except Exception as e:
        print(f"Error en la clasificación: {e}")
        return "fallback"

# --- INSTRUCCIÓN DE SISTEMA MEJORADA ---
instruccion_de_sistema = """
Eres COLEPA, un asistente legal virtual especializado exclusivamente en la legislación de la República del Paraguay. Tu misión es asistir a profesionales del derecho y ciudadanos, proporcionando respuestas precisas, claras y directas.

Tus reglas de comportamiento son:
1.  **Tono:** Profesional, calmado, servicial y empático.
2.  **Base de Conocimiento:** Si se te proporciona un "Contexto legal", tu única fuente de verdad es ese texto. Basa tu respuesta estricta y únicamente en él. No uses conocimiento externo.
3.  **Límites:** Tu especialización es exclusivamente sobre las leyes de Paraguay. Si la pregunta es sobre leyes de otros países o temas no legales, responde amablemente que no puedes asistir.
4.  **Incertidumbre:** Si el contexto no contiene la información para responder, indícalo claramente diciendo: "Basado en el artículo proporcionado, no tengo la información suficiente para responder a tu pregunta." No inventes información.
5.  **Conversación Casual:** Si no se te proporciona un contexto legal y la pregunta del usuario es un saludo o una charla casual, puedes responder de manera natural y amigable. Por ejemplo: "¡Hola! Soy COLEPA, tu asistente legal. ¿Cómo puedo ayudarte hoy con las leyes de Paraguay?".
"""

@app.post("/consulta", summary="Procesa una consulta legal o conversacional")
def procesar_consulta(request: ConsultaRequest):
    try:
        contexto_payload = None
        # --- PASO 0: CLASIFICAR PREGUNTA ---
        collection_a_usar = clasificar_pregunta(request.pregunta)
        
        if collection_a_usar is None:
            # Es una pregunta conversacional, no buscamos en Qdrant
            print("Pregunta conversacional detectada.")
        else:
            # Es una pregunta legal, procedemos con la búsqueda
            print(f"Decisión del enrutador: Usar la colección '{collection_a_usar}'")
            # --- BÚSQUEDA DUAL ---
            match_articulo = re.search(r'art[ií]culo\s+([\d\.]+)', request.pregunta, re.IGNORECASE)
            if match_articulo:
                numero_str = match_articulo.group(1).replace('.', '')
                contexto_payload = buscar_articulo_por_numero(numero=int(numero_str), collection_name=collection_a_usar)
            else:
                embedding = openai_client.embeddings.create(model="text-embedding-ada-002", input=request.pregunta).data[0].embedding
                contexto_payload = buscar_articulo_relevante(query_vector=embedding, collection_name=collection_a_usar)

        # --- CONSTRUCCIÓN DE RESPUESTA ---
        if contexto_payload:
            # Si encontramos un artículo, usamos el prompt estructurado
            texto_contexto = contexto_payload.get("pageContent", "")
            prompt_final = construir_prompt(contexto_legal=texto_contexto, pregunta_usuario=request.pregunta)
            messages = [
                {"role": "system", "content": instruccion_de_sistema},
                {"role": "user", "content": prompt_final}
            ]
        else:
            # Si no encontramos artículo (o es conversacional), enviamos la pregunta directamente
            messages = [
                {"role": "system", "content": instruccion_de_sistema},
                {"role": "user", "content": request.pregunta}
            ]

        chat_completion = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages
        )
        respuesta = chat_completion.choices[0].message.content

        # --- RESPUESTA CONDICIONAL ---
        if contexto_payload:
            return {
                "respuesta": respuesta,
                "fuente": {
                    "ley": contexto_payload.get("nombre_ley"),
                    "articulo_numero": contexto_payload.get("numero_articulo"),
                    "texto_fuente": texto_contexto
                }
            }
        else:
            return {"respuesta": respuesta, "fuente": None}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
