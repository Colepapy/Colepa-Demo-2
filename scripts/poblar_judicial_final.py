# Archivo: scripts/poblar_judicial_final.py

import os
import json
from openai import OpenAI
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv
import uuid
import re

# --- CONFIGURACIÓN ---
load_dotenv()
COLECCION = "colepa_organizacion_judicial_final"
ARCHIVO_JSON_ENTRADA = os.path.join(os.path.dirname(__file__), '..', 'data', 'judicial_data_completo.json')
NOMBRE_LEY_PAYLOAD = "Código de Organización Judicial"

# --- INICIALIZACIÓN DE CLIENTES ---
try:
    print("Inicializando clientes...")
    qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"), timeout=120)
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=120.0)
    print("Clientes inicializados.")
except Exception as e:
    print(f"Error al inicializar los clientes: {e}")
    exit()

def crear_coleccion():
    """Crea la colección y sus índices si no existen."""
    print(f"Borrando y volviendo a crear la colección '{COLECCION}' para una carga limpia...")
    try:
        qdrant_client.recreate_collection(
            collection_name=COLECCION,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )
        qdrant_client.create_payload_index(collection_name=COLECCION, field_name="numero_articulo", field_schema="integer")
        qdrant_client.create_payload_index(collection_name=COLECCION, field_name="nombre_ley", field_schema="keyword")
        print(f"Colección '{COLECCION}' lista y con índice creado.")
    except Exception as e:
        print(f"Error al crear la colección: {e}")
        exit()

def poblar_base_de_datos():
    """Lee el JSON, crea embeddings y sube los datos estructurados a Qdrant."""
    try:
        with open(ARCHIVO_JSON_ENTRADA, 'r', encoding='utf-8') as f:
            lista_articulos = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: No se encontró '{ARCHIVO_JSON_ENTRADA}'. Ejecuta el script de extracción primero.")
        return

    textos = [articulo['texto'] for articulo in lista_articulos]
    print(f"Creando embeddings para {len(textos)} artículos (esto puede tardar)...")
    
    try:
        # Vectorizar en lotes para mayor eficiencia
        vectores = []
        lote_openai = 1000
        for i in range(0, len(textos), lote_openai):
            lote_texto = textos[i:i + lote_openai]
            print(f"  - Enviando lote {i//lote_openai + 1} a OpenAI...")
            embedding_response = openai_client.embeddings.create(model="text-embedding-ada-002", input=lote_texto)
            vectores.extend([item.embedding for item in embedding_response.data])
        print("Embeddings creados.")
    except Exception as e:
        print(f"ERROR al crear embeddings con OpenAI: {e}")
        return

    print("Subiendo puntos a Qdrant...")
    puntos_a_subir = []
    for i, articulo in enumerate(lista_articulos):
        numero_int = int(articulo['numero_str'])
        puntos_a_subir.append(models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, articulo['numero_str'] + NOMBRE_LEY_PAYLOAD)), # ID único
            vector=vectores[i],
            payload={
                "pageContent": articulo['texto'],
                "numero_articulo": numero_int,
                "nombre_ley": NOMBRE_LEY_PAYLOAD,
                "estado": articulo['estado'],
                "libro": articulo['contexto']['libro'],
                "titulo": articulo['contexto']['titulo'],
                "capitulo": articulo['contexto']['capitulo'],
                "seccion": articulo['contexto']['seccion']
            }
        ))
    
    lote_qdrant = 100
    for i in range(0, len(puntos_a_subir), lote_qdrant):
        lote = puntos_a_subir[i:i + lote_qdrant]
        print(f"  - Subiendo lote {i//lote_qdrant + 1} a Qdrant...")
        qdrant_client.upsert(collection_name=COLECCION, points=lote, wait=True)
            
    print(f"\n¡Proceso de carga para '{COLECCION}' completado!")

if __name__ == "__main__":
    crear_coleccion()
    poblar_base_de_datos()