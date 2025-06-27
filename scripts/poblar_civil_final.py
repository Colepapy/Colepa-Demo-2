# Archivo: scripts/poblar_civil_final.py (Versión con Filtro de Vacíos)

import os
import json
from openai import OpenAI
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv
import uuid
import re

# --- CONFIGURACIÓN ---
load_dotenv()
COLECCION = "colepa_codigo_civil_final"
RUTA_ARTICULOS = os.path.join(os.path.dirname(__file__), '..', 'data', 'articulos_codigo_civil_final')
NOMBRE_LEY_PAYLOAD = "Código Civil"

# --- INICIALIZACIÓN ---
try:
    print("Inicializando clientes...")
    qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"), timeout=120)
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=120.0)
    print("Clientes inicializados.")
except Exception as e:
    print(f"Error al inicializar los clientes: {e}")
    exit()

def crear_coleccion():
    print(f"Borrando y volviendo a crear la colección '{COLECCION}' para una carga limpia...")
    try:
        qdrant_client.recreate_collection(
            collection_name=COLECCION,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )
        qdrant_client.create_payload_index(collection_name=COLECCION, field_name="numero_articulo", field_schema="integer")
        print(f"Colección '{COLECCION}' lista y con índice creado.")
    except Exception as e:
        print(f"Error al crear la colección: {e}")
        exit()

def poblar_base_de_datos():
    print(f"Buscando artículos en: {RUTA_ARTICULOS}")
    archivos_txt = [f for f in os.listdir(RUTA_ARTICULOS) if f.endswith('.txt')]
    print(f"Se encontraron {len(archivos_txt)} archivos para procesar.")

    articulos_info = []
    for nombre_archivo in archivos_txt:
        ruta_completa = os.path.join(RUTA_ARTICULOS, nombre_archivo)
        with open(ruta_completa, 'r', encoding='utf-8') as file:
            contenido_texto = file.read().strip()
        if contenido_texto: # Solo procesamos archivos que no estén vacíos
            match_num = re.search(r'Art(?:ículo)?\.\s*([\d\.]+)', contenido_texto)
            if match_num:
                numero_int = int(match_num.group(1).replace('.', ''))
                articulos_info.append({'numero_int': numero_int, 'contenido': contenido_texto, 'nombre_archivo': nombre_archivo})
    
    # --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
    # Nos aseguramos de que la lista de textos a enviar no contenga elementos vacíos
    textos_para_embedding = [info['contenido'] for info in articulos_info]
    
    if not textos_para_embedding:
        print("No se encontró texto válido para procesar después de la limpieza.")
        return

    print(f"Creando embeddings para {len(textos_para_embedding)} artículos válidos (esto tardará)...")
    vectores = []
    lote_openai = 1000
    for i in range(0, len(textos_para_embedding), lote_openai):
        lote_texto = textos_para_embedding[i:i + lote_openai]
        print(f"  - Enviando lote {i//lote_openai + 1} a OpenAI...")
        try:
            embedding_response = openai_client.embeddings.create(model="text-embedding-ada-002", input=lote_texto)
            vectores.extend([item.embedding for item in embedding_response.data])
        except Exception as e:
            print(f"ERROR al crear embeddings con OpenAI: {e}")
            return
    print("Embeddings creados.")

    print("Subiendo puntos a Qdrant...")
    puntos_a_subir = []
    for i, info in enumerate(articulos_info):
        puntos_a_subir.append(models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, info['nombre_archivo'])),
            vector=vectores[i],
            payload={"pageContent": info['contenido'], "numero_articulo": info['numero_int'], "nombre_ley": NOMBRE_LEY_PAYLOAD}
        ))
    
    lote_qdrant = 100
    for i in range(0, len(puntos_a_subir), lote_qdrant):
        lote = puntos_a_subir[i:i + lote_qdrant]
        print(f"  - Subiendo lote {i//lote_qdrant + 1}...")
        qdrant_client.upsert(collection_name=COLECCION, points=lote, wait=True)
            
    print(f"\n¡Proceso de carga para '{COLECCION}' completado!")

if __name__ == "__main__":
    crear_coleccion()
    poblar_base_de_datos()