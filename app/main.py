# Archivo: app/main.py (Versión Final con Memoria y Enrutador Robusto)

import os, re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

from app.vector_search import buscar_articulo_relevante, buscar_articulo_por_numero
from app.prompt_builder import construir_prompt

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI(title="Colepa API", version="FINAL")

origins = ["https://www.colepa.com", "http://localhost", "http://localhost:8000", "null"]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ConsultaRequest(BaseModel):
    historial: List[ChatMessage]

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
    nombres_leyes = list(MAPA_COLECCIONES.keys())
    prompt = f"Analiza la siguiente pregunta. Si se refiere a una de las siguientes áreas legales de Paraguay, responde únicamente con el nombre exacto de la ley de la lista: {nombres_leyes}. Si es un saludo, despedida o charla casual, responde 'N/A'. Pregunta: '{pregunta}'"
    try:
        response = openai_client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=50)
        clasificacion = response.choices[0].message.content.strip().replace('"', '')
        return MAPA_COLECCIONES.get(clasificacion)
    except Exception as e:
        print(f"Error en clasificación: {e}")
        return None

instruccion_sistema = """
Eres COLEPA, un asistente legal virtual de Paraguay. Tu tono es profesional, calmado y empático.
- Si la conversación es casual, responde amablemente.
- Si la pregunta es legal, y recibes un "Contexto legal", basa tu respuesta estricta y únicamente en ese texto.
- Si no encuentras una respuesta en el contexto, indícalo claramente.
- Si la pregunta es legal pero no recibes contexto, usa tu conocimiento para guiar al usuario, pero aclara que no estás citando un artículo específico.
- Nunca respondas sobre leyes de otros países.
"""

@app.post("/consulta")
def procesar_consulta(request: ConsultaRequest):
    historial_usuario = request.historial
    if not historial_usuario:
        raise HTTPException(status_code=400, detail="El historial no puede estar vacío.")

    pregunta_actual = historial_usuario[-1].content
    contexto_payload = None
    collection_a_usar = clasificar_pregunta(pregunta_actual)
    
    if collection_a_usar:
        print(f"Buscando en: {collection_a_usar}")
        embedding = openai_client.embeddings.create(model="text-embedding-ada-002", input=pregunta_actual).data[0].embedding
        contexto_payload = buscar_articulo_relevante(query_vector=embedding, collection_name=collection_a_usar)

    mensajes_para_ia = [{"role": "system", "content": instruccion_sistema}]
    mensajes_para_ia.extend([{"role": msg.role, "content": msg.content} for msg in historial_usuario])

    if contexto_payload:
        texto_contexto = contexto_payload.get("pageContent", "")
        prompt_con_contexto = construir_prompt(contexto_legal=texto_contexto, pregunta_usuario=pregunta_actual)
        mensajes_para_ia[-1]["content"] = prompt_con_contexto
    
    chat_completion = openai_client.chat.completions.create(model="gpt-4-turbo", messages=mensajes_para_ia)
    respuesta = chat_completion.choices[0].message.content

    return {
        "respuesta": respuesta,
        "fuente": {
            "ley": contexto_payload.get("nombre_ley"),
            "articulo_numero": contexto_payload.get("numero_articulo")
        } if contexto_payload else None
    }
