# Archivo: app/vector_search.py (Versión Súper Optimizada)
import os
import logging
import time
from typing import List, Dict, Optional, Union
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from qdrant_client.http import models as rest

# Configurar logging específico para vector search
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Cliente Qdrant global con configuración optimizada
try:
    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
        timeout=30,  # Timeout más generoso
        prefer_grpc=False,  # Usar HTTP para mejor compatibilidad
    )
    logger.info("✅ Cliente Qdrant inicializado correctamente")
except Exception as e:
    logger.error(f"❌ Error inicializando cliente Qdrant: {e}")
    qdrant_client = None

def verificar_conexion_qdrant() -> bool:
    """
    Verifica que la conexión a Qdrant esté funcionando.
    
    Returns:
        True si la conexión es exitosa, False en caso contrario.
    """
    if not qdrant_client:
        logger.error("❌ Cliente Qdrant no está inicializado")
        return False
    
    try:
        # Test básico de conexión
        collections = qdrant_client.get_collections()
        logger.info(f"✅ Conexión Qdrant exitosa. Colecciones disponibles: {len(collections.collections)}")
        return True
    except Exception as e:
        logger.error(f"❌ Error verificando conexión Qdrant: {e}")
        return False

def buscar_articulo_relevante(
    query_vector: List[float], 
    collection_name: str, 
    limit: int = 3,
    score_threshold: float = 0.7
) -> Optional[Dict]:
    """
    Búsqueda por SIMILITUD SEMÁNTICA optimizada en una colección específica.
    
    Args:
        query_vector: Vector de embedding de la consulta
        collection_name: Nombre de la colección en Qdrant
        limit: Número máximo de resultados (default: 3)
        score_threshold: Umbral mínimo de similitud (default: 0.7)
    
    Returns:
        Payload del mejor resultado o None si no hay coincidencias
    """
    if not qdrant_client:
        logger.error("❌ Cliente Qdrant no disponible para búsqueda semántica")
        return None
    
    if not query_vector:
        logger.warning("⚠️ Vector de consulta vacío")
        return None
    
    start_time = time.time()
    
    try:
        logger.info(f"🔍 Búsqueda semántica en colección: {collection_name}")
        logger.info(f"📊 Parámetros: limit={limit}, threshold={score_threshold}")
        
        # Realizar búsqueda con parámetros optimizados
        search_result = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=True,
            with_vectors=False,  # No necesitamos los vectores de vuelta
            score_threshold=score_threshold
        )
        
        search_time = time.time() - start_time
        
        if search_result:
            mejor_resultado = search_result[0]
            score = mejor_resultado.score
            payload = mejor_resultado.payload
            
            logger.info(f"✅ Resultado encontrado en {search_time:.2f}s")
            logger.info(f"📈 Score de similitud: {score:.3f}")
            logger.info(f"📖 Ley: {payload.get('nombre_ley', 'N/A')}")
            logger.info(f"📄 Artículo: {payload.get('numero_articulo', 'N/A')}")
            logger.info(f"📝 Contenido: {payload.get('pageContent', '')[:100]}...")
            
            # Añadir metadatos de búsqueda al payload
            payload_enriquecido = dict(payload)
            payload_enriquecido['_search_metadata'] = {
                'score': score,
                'search_time': search_time,
                'results_count': len(search_result),
                'collection': collection_name
            }
            
            return payload_enriquecido
        else:
            logger.warning(f"❌ No se encontraron resultados en {search_time:.2f}s (threshold: {score_threshold})")
            return None
            
    except Exception as e:
        search_time = time.time() - start_time
        logger.error(f"❌ Error en búsqueda semántica en Qdrant: {e}")
        logger.error(f"   Colección: {collection_name}")
        logger.error(f"   Tiempo transcurrido: {search_time:.2f}s")
        logger.error(f"   Dimensión del vector: {len(query_vector) if query_vector else 'N/A'}")
        return None

def buscar_articulo_por_numero(
    numero: int, 
    collection_name: str,
    exacto: bool = True
) -> Optional[Dict]:
    """
    Búsqueda EXACTA optimizada por número de artículo en una colección específica.
    
    Args:
        numero: Número del artículo a buscar
        collection_name: Nombre de la colección en Qdrant
        exacto: Si True, busca coincidencia exacta. Si False, busca también similares
    
    Returns:
        Payload del artículo encontrado o None si no existe
    """
    if not qdrant_client:
        logger.error("❌ Cliente Qdrant no disponible para búsqueda por número")
        return None
    
    if not isinstance(numero, int) or numero <= 0:
        logger.warning(f"⚠️ Número de artículo inválido: {numero}")
        return None
    
    start_time = time.time()
    
    try:
        logger.info(f"🎯 Búsqueda por número de artículo: {numero}")
        logger.info(f"📚 Colección: {collection_name}")
        logger.info(f"🔒 Búsqueda exacta: {exacto}")
        
        # Crear filtro para búsqueda exacta
        search_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="numero_articulo",
                    match=models.MatchValue(value=str(numero))  # Buscar como string también
                )
            ]
        )
        
        # Si no es exacto, agregar filtro alternativo para enteros
        if not exacto:
            search_filter = models.Filter(
                should=[
                    models.FieldCondition(
                        key="numero_articulo",
                        match=models.MatchValue(value=str(numero))
                    ),
                    models.FieldCondition(
                        key="numero_articulo",
                        match=models.MatchValue(value=numero)
                    )
                ]
            )
        
        # Realizar búsqueda con scroll para mayor eficiencia
        puntos, next_page_offset = qdrant_client.scroll(
            collection_name=collection_name,
            scroll_filter=search_filter,
            limit=5,  # Buscar hasta 5 para tener opciones
            with_payload=True,
            with_vectors=False
        )
        
        search_time = time.time() - start_time
        
        if puntos:
            # Tomar el primer resultado (más relevante)
            mejor_punto = puntos[0]
            payload = mejor_punto.payload
            
            logger.info(f"✅ Artículo {numero} encontrado en {search_time:.2f}s")
            logger.info(f"📖 Ley: {payload.get('nombre_ley', 'N/A')}")
            logger.info(f"📄 Artículo encontrado: {payload.get('numero_articulo', 'N/A')}")
            logger.info(f"📝 Contenido: {payload.get('pageContent', '')[:100]}...")
            
            # Añadir metadatos de búsqueda
            payload_enriquecido = dict(payload)
            payload_enriquecido['_search_metadata'] = {
                'search_time': search_time,
                'results_count': len(puntos),
                'collection': collection_name,
                'search_type': 'exact_number'
            }
            
            return payload_enriquecido
        else:
            logger.warning(f"❌ Artículo {numero} no encontrado en {search_time:.2f}s")
            
            # Si búsqueda exacta falló, intentar búsqueda aproximada
            if exacto:
                logger.info("🔄 Intentando búsqueda aproximada...")
                return buscar_articulo_por_numero(numero, collection_name, exacto=False)
            
            return None
            
    except Exception as e:
        search_time = time.time() - start_time
        logger.error(f"❌ Error en búsqueda por número en Qdrant: {e}")
        logger.error(f"   Colección: {collection_name}")
        logger.error(f"   Número buscado: {numero}")
        logger.error(f"   Tiempo transcurrido: {search_time:.2f}s")
        return None

def buscar_articulos_multiples(
    query_vector: List[float],
    collection_names: List[str],
    limit_por_coleccion: int = 2
) -> List[Dict]:
    """
    Búsqueda semántica en múltiples colecciones simultáneamente.
    
    Args:
        query_vector: Vector de embedding de la consulta
        collection_names: Lista de nombres de colecciones
        limit_por_coleccion: Límite de resultados por colección
    
    Returns:
        Lista de payloads encontrados, ordenados por relevancia
    """
    if not qdrant_client:
        logger.error("❌ Cliente Qdrant no disponible para búsqueda múltiple")
        return []
    
    resultados = []
    start_time = time.time()
    
    logger.info(f"🔍 Búsqueda en múltiples colecciones: {len(collection_names)}")
    
    for collection_name in collection_names:
        try:
            resultado = buscar_articulo_relevante(
                query_vector, 
                collection_name, 
                limit=limit_por_coleccion
            )
            if resultado:
                resultados.append(resultado)
                
        except Exception as e:
            logger.warning(f"⚠️ Error en colección {collection_name}: {e}")
            continue
    
    search_time = time.time() - start_time
    logger.info(f"✅ Búsqueda múltiple completada en {search_time:.2f}s")
    logger.info(f"📊 Resultados encontrados: {len(resultados)}")
    
    # Ordenar por score de similitud
    resultados_ordenados = sorted(
        resultados,
        key=lambda x: x.get('_search_metadata', {}).get('score', 0),
        reverse=True
    )
    
    return resultados_ordenados

def obtener_estadisticas_coleccion(collection_name: str) -> Optional[Dict]:
    """
    Obtiene estadísticas detalladas de una colección.
    
    Args:
        collection_name: Nombre de la colección
    
    Returns:
        Diccionario con estadísticas o None si hay error
    """
    if not qdrant_client:
        logger.error("❌ Cliente Qdrant no disponible para estadísticas")
        return None
    
    try:
        # Información básica de la colección
        info = qdrant_client.get_collection(collection_name)
        
        # Contar puntos totales
        count_result = qdrant_client.count(collection_name)
        
        estadisticas = {
            'nombre': collection_name,
            'total_puntos': count_result.count,
            'vector_size': info.config.params.vectors.size,
            'distance_metric': info.config.params.vectors.distance.value,
            'status': info.status.value,
            'memoria_indexada': info.config.params.vectors.on_disk if hasattr(info.config.params.vectors, 'on_disk') else 'N/A'
        }
        
        logger.info(f"📊 Estadísticas de {collection_name}: {estadisticas['total_puntos']} artículos")
        return estadisticas
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas de {collection_name}: {e}")
        return None

def validar_coleccion_existe(collection_name: str) -> bool:
    """
    Valida que una colección específica existe en Qdrant.
    
    Args:
        collection_name: Nombre de la colección a validar
    
    Returns:
        True si existe, False en caso contrario
    """
    if not qdrant_client:
        return False
    
    try:
        qdrant_client.get_collection(collection_name)
        logger.info(f"✅ Colección {collection_name} existe y es accesible")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Colección {collection_name} no existe o no es accesible: {e}")
        return False

def buscar_con_filtros_avanzados(
    query_vector: List[float],
    collection_name: str,
    filtros: Dict[str, Union[str, int, List]] = None,
    limit: int = 5
) -> List[Dict]:
    """
    Búsqueda con filtros avanzados por metadatos.
    
    Args:
        query_vector: Vector de consulta
        collection_name: Nombre de la colección
        filtros: Diccionario de filtros a aplicar
        limit: Límite de resultados
    
    Returns:
        Lista de payloads que cumplen los filtros
    """
    if not qdrant_client or not query_vector:
        return []
    
    try:
        # Construir filtros de Qdrant
        conditions = []
        if filtros:
            for key, value in filtros.items():
                if isinstance(value, list):
                    # Filtro OR para múltiples valores
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchAny(any=value)
                        )
                    )
                else:
                    # Filtro exacto
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )
        
        search_filter = models.Filter(must=conditions) if conditions else None
        
        # Realizar búsqueda con filtros
        resultados = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        
        logger.info(f"🔍 Búsqueda con filtros: {len(resultados)} resultados")
        return [resultado.payload for resultado in resultados]
        
    except Exception as e:
        logger.error(f"❌ Error en búsqueda con filtros: {e}")
        return []

# Función de diagnóstico para debugging
def diagnosticar_qdrant() -> Dict[str, Union[bool, str, int]]:
    """
    Ejecuta diagnósticos completos del sistema Qdrant.
    
    Returns:
        Diccionario con resultados del diagnóstico
    """
    diagnostico = {
        'conexion_activa': False,
        'total_colecciones': 0,
        'colecciones_accesibles': 0,
        'errores': [],
        'tiempo_respuesta': 0
    }
    
    start_time = time.time()
    
    try:
        # Verificar conexión
        diagnostico['conexion_activa'] = verificar_conexion_qdrant()
        
        if diagnostico['conexion_activa']:
            # Listar colecciones
            collections = qdrant_client.get_collections()
            diagnostico['total_colecciones'] = len(collections.collections)
            
            # Verificar acceso a cada colección
            accesibles = 0
            for collection in collections.collections:
                if validar_coleccion_existe(collection.name):
                    accesibles += 1
            
            diagnostico['colecciones_accesibles'] = accesibles
        
    except Exception as e:
        diagnostico['errores'].append(str(e))
        logger.error(f"❌ Error en diagnóstico: {e}")
    
    diagnostico['tiempo_respuesta'] = time.time() - start_time
    
    logger.info(f"🩺 Diagnóstico Qdrant completado: {diagnostico}")
    return diagnostico
