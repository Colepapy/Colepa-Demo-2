# Archivo: app/vector_search.py - CORREGIDO PARA QDRANT API
import os
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models

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
    CORREGIDO: Usa search() en lugar de query_points()
    """
    if not qdrant_client:
        logger.error("❌ Qdrant no disponible")
        return None
    
    try:
        logger.info(f"🎯 Buscando artículo {numero} en {collection_name}")
        
        # CORREGIDO: Usar search() con filter
        resultados = qdrant_client.search(
            collection_name=collection_name,
            query_vector=[0.1] * 1536,  # Vector dummy, usamos filtros
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="numero_articulo", 
                        match=models.MatchValue(value=numero)
                    )
                ]
            ),
            limit=1
        )
        
        if resultados:
            punto = resultados[0]
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
    CORREGIDO: Usa search() en lugar de query_points()
    """
    if not qdrant_client or not query_vector:
        logger.error("❌ Qdrant o vector no disponible")
        return None
    
    try:
        logger.info(f"🔍 Búsqueda semántica en {collection_name}")
        
        # CORREGIDO: Usar search() directamente
        resultados = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=1,
            score_threshold=0.7
        )
        
        if resultados:
            punto = resultados[0]
            contexto = {
                "pageContent": punto.payload.get("texto_completo", ""),
                "numero_articulo": punto.payload.get("numero_articulo"),
                "nombre_ley": punto.payload.get("nombre_ley", "Código Aduanero"),
                "titulo": punto.payload.get("titulo", "")
            }
            
            logger.info(f"✅ Contexto encontrado con score: {punto.score}")
            return contexto
        else:
            logger.warning("❌ No se encontró contexto relevante")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error en búsqueda semántica: {e}")
        return None
