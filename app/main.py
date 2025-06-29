# Archivo: app/main.py (Tu versión, actualizada con Memoria de Chat)

import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# --- CAMBIO #1: Importar herramientas de tipado ---
from pydantic import BaseModel, Field
from typing import List, Dict

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
    version="5.0.0" # Versión con Memoria
)

# --- Configuración de CORS ---
origins = ["https://www.colepa.com", "http://localhost", "http://localhost:8000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- CAMBIO #2: Modelos de Datos actualizados para recibir un historial ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ConsultaRequest(BaseModel):
    historial: List[ChatMessage]

# --- Enrutador de Colecciones (Sin cambios) ---
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

def clasificar_pregunta(pregunta: str) -> str | None:
    # (Esta función no cambia)
    nombres_leyes = list(MAPA_COLECCIONES.keys())
    prompt_clasificacion = f"Dada la siguiente pregunta, determina si se refiere a una de estas áreas legales de Paraguay: {nombres_leyes}. Si la pregunta es un saludo, una despedida, una pregunta casual o no es de temática legal, responde 'N/A'. De lo contrario, responde únicamente con el nombre exacto de la ley de la lista. Pregunta: '{pregunta}'"
    try:
        response = openai_client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_clasificacion}], temperature=0, max_tokens=50)
        clasificacion = response.choices[0].message.content.strip().replace('"', '')
        if clasificacion == 'N/A': return None
        for ley, coleccion in MAPA_COLECCIONES.items():
            if ley in clasificacion: return coleccion
        return "fallback"
    except Exception as e:
        print(f"Error en la clasificación: {e}")
        return "fallback"

# --- Instrucción de Sistema (Sin cambios) ---
instruccion_de_sistema = """
Eres COLEPA, un asistente legal virtual especializado exclusivamente en la legislación de la República del Paraguay...
""" # (Tu prompt de personalidad completo va aquí)

# --- Endpoint Principal de la API (Actualizado para usar historial) ---
@app.post("/consulta", summary="Procesa una conversación con memoria")
def procesar_consulta(request: ConsultaRequest):
    try:
        historial_completo = request.historial
        if not historial_completo:
            raise HTTPException(status_code=400, detail="El historial no puede estar vacío.")

        # La pregunta actual es el último mensaje del usuario
        pregunta_actual = historial_completo[-1].content
        
        contexto_payload = None
        collection_a_usar = clasificar_pregunta(pregunta_actual)
        
        if collection_a_usar and collection_a_usar != "fallback":
            print(f"Pregunta legal detectada. Buscando en: '{collection_a_usar}'")
            embedding = openai_client.embeddings.create(model="text-embedding-ada-002", input=pregunta_actual).data[0].embedding
            contexto_payload = buscar_articulo_relevante(query_vector=embedding, collection_name=collection_a_usar)

        # Preparamos los mensajes para la IA
        mensajes_para_ia = [{"role": "system", "content": instruccion_de_sistema}]
        
        # Añadimos el historial completo que nos envió el usuario
        for msg in historial_completo:
            mensajes_para_ia.append({"role": msg.role, "content": msg.content})

        if contexto_payload:
            # Si encontramos un artículo, inyectamos el contexto en el último mensaje del usuario
            texto_contexto = contexto_payload.get("pageContent", "")
            prompt_con_contexto = construir_prompt(contexto_legal=texto_contexto, pregunta_usuario=pregunta_actual)
            mensajes_para_ia[-1]["content"] = prompt_con_contexto

        chat_completion = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=mensajes_para_ia
        )
        respuesta = chat_completion.choices[0].message.content

        if contexto_payload:
            return {"respuesta": respuesta, "fuente": {"ley": contexto_payload.get("nombre_ley"), "articulo_numero": contexto_payload.get("numero_articulo")}}
        else:
            return {"respuesta": respuesta, "fuente": None}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
