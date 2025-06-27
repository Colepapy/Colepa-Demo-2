# Archivo: scripts/poblar_aduanero.py
import os, json, re, uuid
from openai import OpenAI
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

load_dotenv()
# CONFIGURACIÓN
COLECCION = "colepa_aduanero_final"
RUTA_ARTICULOS = os.path.join(os.path.dirname(__file__), '..', 'data', 'articulos_aduanero_final')

# El resto del script es idéntico en lógica al que usaremos para el código civil...
# (El código completo se omite por brevedad, pero puedes copiar el de poblar_civil.py y solo cambiar las 2 líneas de arriba y el "nombre_ley" en el payload)
# Para evitar errores, te recomiendo usar el script completo que te daré para el Código Civil y solo adaptar esas 3 variables.
print(f"Este es un script de ejemplo. Por favor, use el de 'poblar_civil.py' como plantilla principal y adapte las variables COLECCION, RUTA_ARTICULOS y el 'nombre_ley' en el payload.")