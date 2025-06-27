# Archivo: scripts/poblar_laboral_final.py (Versión Corregida)

import os, json, re, uuid
from openai import OpenAI
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

load_dotenv()
# --- CONFIGURACIÓN ---
COLECCION = "colepa_laboral_final"
ARCHIVO_JSON_ENTRADA = os.path.join(os.path.dirname(__file__), '..', 'data', 'laboral_data.json')
NOMBRE_LEY_PAYLOAD = "Código Laboral"

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
    print(f"Borrando y volviendo a crear la colección '{COLECCION}'...")
    try:
        qdrant_client.recreate_collection(
            collection_name=COLECCION,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )
        qdrant_client.create_payload_index(collection_name=COLECCION, field_name="numero_articulo", field_schema="integer")
        qdrant_client.create_payload_index(collection_name=COLECCION, field_name="nombre_ley", field_schema="keyword")
        print(f"Colección '{COLECCION}' lista.")
    except Exception as e:
        print(f"Error al crear la colección: {e}")
        exit()

def poblar_base_de_datos():
    try:
        with open(ARCHIVO_JSON_ENTRADA, 'r', encoding='utf-8') as f:
            lista_articulos = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: No se encontró '{ARCHIVO_JSON_ENTRADA}'. Ejecuta el script de extracción primero.")
        return

    textos = [art.get('texto', '') for art in lista_articulos]
    articulos_validos = [art for art in lista_articulos if art.get('texto', '').strip()]
    textos_validos = [art['texto'] for art in articulos_validos]

    print(f"Creando embeddings para {len(textos_validos)} artículos...")
    
    try:
        embedding_response = openai_client.embeddings.create(model="text-embedding-ada-002", input=textos_validos)
        vectores = [item.embedding for item in embedding_response.data]
        print("Embeddings creados.")
    except Exception as e:
        print(f"ERROR al crear embeddings: {e}")
        return

    print("Subiendo puntos a Qdrant...")
    puntos = []
    for i, articulo in enumerate(articulos_validos):
        numero_int = int(articulo['numero_str'])
        
        # --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
        # Ahora leemos los datos directamente de 'articulo' usando .get()
        puntos.append(models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, articulo['numero_str'] + NOMBRE_LEY_PAYLOAD)),
            vector=vectores[i],
            payload={
                "pageContent": articulo.get('texto', ''),
                "numero_articulo": numero_int,
                "nombre_ley": NOMBRE_LEY_PAYLOAD,
                "libro": articulo.get('libro', 'N/A'),
                "titulo": articulo.get('titulo', 'N/A'),
                "capitulo": articulo.get('capitulo', 'N/A')
            }
        ))
    
    lote_qdrant = 100
    for i in range(0, len(puntos), lote_qdrant):
        lote = puntos[i:i + lote_qdrant]
        print(f"  - Subiendo lote {i//lote_qdrant + 1}...")
        qdrant_client.upsert(collection_name=COLECCION, points=lote, wait=True)
            
    print(f"\n¡Proceso de carga para '{COLECCION}' completado!")

if __name__ == "__main__":
    crear_coleccion()
    poblar_base_de_datos()