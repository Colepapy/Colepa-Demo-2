# Mock Search Engine - Búsqueda local en JSON
import json
import os
import re
from pathlib import Path
from typing import Optional, Dict, List

# Cargar base de datos
CURRENT_DIR = Path(__file__).parent
DB_PATH = CURRENT_DIR / "legal_database.json"

with open(DB_PATH, 'r', encoding='utf-8') as f:
    LEGAL_DB = json.load(f)

ARTICULOS = LEGAL_DB['articulos']

def buscar_articulo_por_numero(numero: int) -> Optional[Dict]:
    """Busca artículo por número exacto"""
    numero_str = str(numero)
    
    for art in ARTICULOS:
        if str(art['numero_articulo']) == numero_str:
            return {
                "pageContent": art['texto_completo'],
                "numero_articulo": art['numero_articulo'],
                "nombre_ley": art['nombre_ley'],
                "titulo": art.get('titulo', '')
            }
    return None

def buscar_por_palabras_clave(query: str) -> Optional[Dict]:
    """Búsqueda semántica simple por palabras clave"""
    query_lower = query.lower()
    
    # Extraer palabras importantes de la query
    palabras_query = set(re.findall(r'\b\w{4,}\b', query_lower))  # Palabras de 4+ letras
    
    # Scoring de artículos
    scores = []
    for art in ARTICULOS:
        score = 0
        
        # Score por palabras clave
        for palabra in art.get('palabras_clave', []):
            if palabra.lower() in query_lower:
                score += 5
        
        # Score por palabras en texto
        texto_lower = art['texto_completo'].lower()
        for palabra in palabras_query:
            if palabra in texto_lower:
                score += 2
        
        # Score por nombre de ley
        if art['nombre_ley'].lower() in query_lower:
            score += 10
        
        if score > 0:
            scores.append((score, art))
    
    # Retornar el mejor match
    if scores:
        scores.sort(reverse=True, key=lambda x: x[0])
        best_art = scores[0][1]
        
        return {
            "pageContent": best_art['texto_completo'],
            "numero_articulo": best_art['numero_articulo'],
            "nombre_ley": best_art['nombre_ley'],
            "titulo": best_art.get('titulo', '')
        }
    
    return None

def buscar_articulo_relevante(query: str) -> Optional[Dict]:
    """Función principal de búsqueda (compatible con la interfaz original)"""
    
    # Intentar extraer número de artículo
    match = re.search(r'art[íi]culo\s*(\d+)|art\.?\s*(\d+)', query.lower())
    if match:
        numero = match.group(1) or match.group(2)
        resultado = buscar_articulo_por_numero(int(numero))
        if resultado:
            return resultado
    
    # Búsqueda semántica
    return buscar_por_palabras_clave(query)
