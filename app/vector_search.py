# Archivo: app/vector_search.py (Versión Final Multi-Colección)

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

load_dotenv()

qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

def buscar_articulo_relevante(query_vector: list[float], collection_name: str) -> dict | None:
    """Búsqueda por SIMILITUD SEMÁNTICA en una colección específica."""
    try:
        search_result = qdrant_client.search(
            collection_name=collection_name, query_vector=query_vector, limit=1, with_payload=True
        )
        return search_result[0].payload if search_result else None
    except Exception as e:
        print(f"Error en búsqueda semántica en Qdrant (Colección: {collection_name}): {e}")
        return None

def buscar_articulo_por_numero(numero: int, collection_name: str) -> dict | None:
    """Búsqueda EXACTA por número de artículo en una colección específica."""
    try:
        puntos, _ = qdrant_client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(must=[models.FieldCondition(key="numero_articulo", match=models.MatchValue(value=numero))]),
            limit=1, with_payload=True
        )
        return puntos[0].payload if puntos else None
    except Exception as e:
        print(f"Error en búsqueda por número en Qdrant (Colección: {collection_name}): {e}")
        return None