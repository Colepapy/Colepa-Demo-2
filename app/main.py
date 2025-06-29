# Archivo: app/main.py (Versión con Configuración de CORS)

import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # Importar CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

# Asumiendo que estos archivos existen y están correctos
from app.vector_search import buscar_articulo_relevante, buscar_articulo_por_numero
from app.prompt_builder import construir_prompt

# --- Configuración Inicial ---
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI(
    title="Colepa API - Asistente Legal Inteligente",
    description="API para realizar consultas legales sobre múltiples cuerpos normativos de Paraguay.",
    version="FINAL"
)

# --- AÑADIR ESTE BLOQUE PARA LA CONFIGURACIÓN DE CORS ---
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
# --- FIN DEL BLOQUE DE CORS ---


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
    prompt_clasificacion = f"Dada la siguiente pregunta, determina a cuál de estas áreas legales de Paraguay se refiere: {nombres_leyes}. Responde únicamente con el nombre exacto de la ley de la lista. Pregunta: '{pregunta}'"
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_clasificacion}],
            temperature=0, max_tokens=50
        )
        clasificacion = response.choices[0].message.content.strip().replace('"', '')
        
        for ley, coleccion in MAPA_COLECCIONES.items():
            if ley in clasificacion:
                return coleccion
        
        return next(iter(MAPA_COLECCIONES.values()))
    except Exception as e:
        print(f"Error en la clasificación: {e}")
        return next(iter(MAPA_COLECCIONES.values()))

instruccion_sistema = """
Eres COLEPA, un asistente legal virtual especializado en la legislación de Paraguay. Tu tono es profesional, calmado y empático. Basa tus respuestas únicamente en el contexto proporcionado. Si no sabes la respuesta, indícalo claramente. No respondas sobre leyes de otros países.
"""

@app.post("/consulta", summary="Procesa una consulta legal usando un enrutador inteligente")
def procesar_consulta(request: ConsultaRequest):
    historial_usuario = request.historial
    if not historial_usuario:
        raise HTTPException(status_code=400, detail="El historial no puede estar vacío.")

    pregunta_actual = historial_usuario[-1].content
    contexto_payload = None
    collection_a_usar = clasificar_pregunta(pregunta_actual)
    
    if collection_a_usar:
        print(f"Buscando en: {collection_a_usar}")
        match_articulo = re.search(r'art[ií]culo\s+([\d\.]+)', pregunta_actual, re.IGNORECASE)
        if match_articulo:
            numero_str = match_articulo.group(1).replace('.', '')
            contexto_payload = buscar_articulo_por_numero(numero=int(numero_str), collection_name=collection_a_usar)
        else:
            embedding = openai_client.embeddings.create(model="text-embedding-ada-002", input=pregunta_actual).data[0].embedding
            contexto_payload = buscar_articulo_relevante(query_vector=embedding, collection_name=collection_a_usar)

    mensajes_para_ia = [{"role": "system", "content": instruccion_sistema}] + [{"role": msg.role, "content": msg.content} for msg in historial_usuario]

    if contexto_payload:
        texto_contexto = contexto_payload.get("pageContent", "")
        prompt_con_contexto = construir_prompt(contexto_legal=texto_contexto, pregunta_usuario=pregunta_actual)
        mensajes_para_ia[-1]["content"] = prompt_con_contexto
    
    chat_completion = openai_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=mensajes_para_ia
    )
    respuesta = chat_completion.choices[0].message.content

    return {
        "respuesta": respuesta,
        "fuente": {
            "ley": contexto_payload.get("nombre_ley"),
            "articulo_numero": contexto_payload.get("numero_articulo")
        } if contexto_payload else None
    }
