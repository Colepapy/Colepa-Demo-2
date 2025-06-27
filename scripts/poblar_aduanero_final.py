# Archivo: scripts/poblar_aduanero_final.py

import os, re, uuid
from openai import OpenAI
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

load_dotenv()
# --- CONFIGURACIÓN ---
COLECCION = "colepa_aduanero_final"
RUTA_ARTICULOS = os.path.join(os.path.dirname(__file__), '..', 'data', 'articulos_aduanero_final')
NOMBRE_LEY_PAYLOAD = "Código Aduanero"

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
    print(f"Verificando/Creando la colección '{COLECCION}'...")
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
    print(f"Se encontraron {len(archivos_txt)} artículos para procesar.")

    textos_para_embedding = []
    articulos_info = []
    for nombre_archivo in archivos_txt:
        ruta_completa = os.path.join(RUTA_ARTICULOS, nombre_archivo)
        with open(ruta_completa, 'r', encoding='utf-8') as file:
            contenido_texto = file.read()
        if contenido_texto.strip():
            match_num = re.search(r'Art(?:ículo)?\s*([\d\.]+)', contenido_texto)
            if match_num:
                numero_int = int(match_num.group(1).replace('.', ''))
                textos_para_embedding.append(contenido_texto)
                articulos_info.append({'numero_int': numero_int, 'contenido': contenido_texto, 'nombre_archivo': nombre_archivo})

    print(f"Creando embeddings para {len(textos_para_embedding)} artículos...")
    vectores = []
    lote_openai = 1000
    for i in range(0, len(textos_para_embedding), lote_openai):
        lote_texto = textos_para_embedding[i:i + lote_openai]
        print(f"  - Enviando lote {i//lote_openai + 1} a OpenAI...")
        embedding_response = openai_client.embeddings.create(model="text-embedding-ada-002", input=lote_texto)
        vectores.extend([item.embedding for item in embedding_response.data])
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