# Archivo: scripts/poblar_aduanero_desde_json.py

import os
import json
from openai import OpenAI
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv
import uuid
import re

# --- CONFIGURACIÓN ---
load_dotenv()

# <-- CAMBIO: Apuntamos a la colección final para este código
COLECCION_ADUANERO = "colepa_aduanero_final"
# <-- CAMBIO: Apuntamos al archivo JSON que acabamos de crear
ARCHIVO_JSON_ENTRADA = os.path.join(os.path.dirname(__file__), '..', 'data', 'aduanero_data.json')

# --- INICIALIZACIÓN DE CLIENTES ---
try:
    print("Inicializando clientes...")
    qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"), timeout=120)
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=120.0)
    print("Clientes de Qdrant y OpenAI inicializados.")
except Exception as e:
    print(f"Error al inicializar los clientes: {e}")
    exit()

def crear_coleccion_con_indices():
    """Crea la colección y todos los índices para el payload si no existen."""
    try:
        collections_response = qdrant_client.get_collections()
        existing_collections = [collection.name for collection in collections_response.collections]
        if COLECCION_ADUANERO not in existing_collections:
            print(f"La colección '{COLECCION_ADUANERO}' no existe. Creándola ahora...")
            qdrant_client.create_collection(
                collection_name=COLECCION_ADUANERO,
                vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
            )
            qdrant_client.create_payload_index(collection_name=COLECCION_ADUANERO, field_name="numero_articulo", field_schema="integer")
            qdrant_client.create_payload_index(collection_name=COLECCION_ADUANERO, field_name="titulo", field_schema="text")
            qdrant_client.create_payload_index(collection_name=COLECCION_ADUANERO, field_name="capitulo", field_schema="text")
            print(f"Colección '{COLECCION_ADUANERO}' e índices de payload creados exitosamente.")
        else:
            print(f"La colección '{COLECCION_ADUANERO}' ya existe. No se realizarán cambios.")
            
    except Exception as e:
        print(f"Ocurrió un error al verificar/crear la colección: {e}")
        exit()

def poblar_desde_json():
    """Lee el JSON, crea embeddings y sube los datos estructurados a Qdrant."""
    print(f"Leyendo datos desde: {ARCHIVO_JSON_ENTRADA}")
    try:
        with open(ARCHIVO_JSON_ENTRADA, 'r', encoding='utf-8') as f:
            lista_articulos = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo '{ARCHIVO_JSON_ENTRADA}'. Por favor, ejecuta primero 'procesar_aduanero_a_json.py'.")
        return

    print(f"Se encontraron {len(lista_articulos)} artículos en el archivo JSON.")
    textos_para_embedding = [articulo['texto'] for articulo in lista_articulos]
    
    print("Enviando textos a OpenAI para crear embeddings (esto puede tardar)...")
    try:
        embedding_response = openai_client.embeddings.create(model="text-embedding-ada-002", input=textos_para_embedding)
        vectores = [item.embedding for item in embedding_response.data]
        print("Embeddings recibidos de OpenAI.")
    except Exception as e:
        print(f"ERROR al crear embeddings con OpenAI: {e}")
        return

    print("Preparando y subiendo puntos a Qdrant...")
    puntos_a_subir = []
    for i, articulo in enumerate(lista_articulos):
        numero_int = int(articulo['numero_str'])
        
        punto_qdrant = models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, articulo['numero_str'])),
            vector=vectores[i],
            payload={
                "pageContent": articulo['texto'],
                "numero_articulo": numero_int,
                "nombre_ley": "Código Aduanero",
                "titulo": articulo['titulo'],
                "capitulo": articulo['capitulo'],
                "seccion": articulo['seccion']
            }
        )
        puntos_a_subir.append(punto_qdrant)

    lote_size_qdrant = 100
    for i in range(0, len(puntos_a_subir), lote_size_qdrant):
        lote = puntos_a_subir[i:i + lote_size_qdrant]
        print(f"  - Subiendo lote {i//lote_size_qdrant + 1}...")
        qdrant_client.upsert(collection_name=COLECCION_ADUANERO, points=lote, wait=True)
            
    print("\n¡Proceso de carga para el Código Aduanero completado!")

# --- EJECUCIÓN ---
if __name__ == "__main__":
    crear_coleccion_con_indices()
    poblar_desde_json()