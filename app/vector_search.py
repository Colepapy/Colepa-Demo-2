# Archivo: app/vector_search.py - SIMPLIFICADO PARA COLEPA
import os
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)
load_dotenv()

# Cliente Qdrant simple
try:
    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
        timeout=30
    )
    logger.info("✅ Qdrant conectado")
except Exception as e:
    logger.error(f"❌ Error Qdrant: {e}")
    qdrant_client = None

def buscar_articulo_por_numero(numero: int, collection_name: str) -> Optional[Dict]:
    """
    Busca un artículo específico por número.
    Simple y directo.
    """
    if not qdrant_client:
        logger.error("❌ Qdrant no disponible")
        return None
    
    try:
        logger.info(f"🎯 Buscando artículo {numero} en {collection_name}")
        
        # Buscar por número exacto
        resultados = qdrant_client.query_points(
            collection_name=collection_name,
            query=[0.1] * 1536,  # Vector dummy, usamos filtros
            query_filter={
                "must": [
                    {
                        "key": "numero_articulo", 
                        "match": {"value": numero}
                    }
                ]
            },
            limit=1
        )
        
        if resultados.points:
            punto = resultados.points[0]
            contexto = {
                "pageContent": punto.payload.get("texto_completo", ""),
                "numero_articulo": punto.payload.get("numero_articulo"),
                "nombre_ley": punto.payload.get("nombre_ley", "Código Aduanero"),
                "titulo": punto.payload.get("titulo", "")
            }
            
            logger.info(f"✅ Artículo {numero} encontrado")
            return contexto
        else:
            logger.warning(f"❌ Artículo {numero} no encontrado")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error buscando artículo {numero}: {e}")
        return None

def buscar_articulo_relevante(query_vector: List[float], collection_name: str) -> Optional[Dict]:
    """
    Búsqueda semántica simple.
    """
    if not qdrant_client or not query_vector:
        logger.error("❌ Qdrant o vector no disponible")
        return None
    
    try:
        logger.info(f"🔍 Búsqueda semántica en {collection_name}")
        
        resultados = qdrant_client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=1,
            score_threshold=0.7
        )
        
        if resultados.points:
            punto = resultados.points[0]
            contexto = {
                "pageContent": punto.payload.get("texto_completo", ""),
                "numero_articulo": punto.payload.get("numero_articulo"),
                "nombre_ley": punto.payload.get("nombre_ley", "Código Aduanero"),
                "titulo": punto.payload.get("titulo", "")
            }
            
            logger.info(f"✅ Contexto encontrado")
            return contexto
        else:
            logger.warning("❌ No se encontró contexto relevante")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error en búsqueda semántica: {e}")
        return None
