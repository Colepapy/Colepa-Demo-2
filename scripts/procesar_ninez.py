# Archivo: scripts/procesar_ninez.py

import os
import re
import fitz  # PyMuPDF
import json

# --- CONFIGURACIÓN ---
NOMBRE_PDF_ENTRADA = "Código de la Niñez y la Adolescencia-Texto Consolidado.pdf"
DIRECTORIO_DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
ARCHIVO_JSON_SALIDA = os.path.join(DIRECTORIO_DATA, 'ninez_data.json')

# --- LÓGICA ---

def extraer_texto_pdf(ruta_pdf):
    print(f"Abriendo y leyendo: {ruta_pdf}")
    try:
        documento = fitz.open(ruta_pdf)
        texto_completo = ""
        # <-- CAMBIO: Empezamos desde la página 10 (índice 9) para este PDF
        for num_pagina in range(9, len(documento)):
            texto_completo += documento[num_pagina].get_text("text", sort=True) + "\n"
        return texto_completo
    except Exception as e:
        return f"Error al leer el PDF: {e}"

def limpiar_texto(texto):
    print("Limpiando texto extraído...")
    textos_a_eliminar = [
        r"Sesquicentenario de la Epop(e|o)ya Nacional\s*\d{4}-\d{4}",
        r"Texto consolidado de la Ley N° 1680/2001",
        r"Oficina: Primer Piso- Cámara de Senadores",
        r"Email: digesto@senado\.gov\.py", "Telefono: 021 4145112", r"\bJA\b"
    ]
    for patron in textos_a_eliminar:
        texto = re.sub(patron, "", texto, flags=re.IGNORECASE)
    texto = re.sub(r'^\s*\d+\s*$', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'(\n\s*){2,}', "\n", texto)
    print("Limpieza completada.")
    return texto.strip()

def guardar_articulo(numero, buffer, contexto, lista):
    """Función auxiliar para guardar un artículo en la lista."""
    if numero and buffer:
        texto_completo = "\n".join(buffer)
        lista.append({"numero_str": numero, "texto": texto_completo, **contexto})
        print(f"Estructurado: Artículo {numero}")

def procesar_y_estructurar(texto_limpio):
    contexto_actual = {'libro': 'N/A', 'titulo': 'N/A', 'capitulo': 'N/A'}
    buffer_articulo = []
    numero_articulo_actual = None
    lista_de_articulos = []
    lineas = texto_limpio.split('\n')

    for linea in lineas:
        linea_stripped = linea.strip()
        if not linea_stripped: continue

        match_libro = re.match(r'^LIBRO\s+(.+)', linea_stripped, re.IGNORECASE)
        match_titulo = re.match(r'^T[ÍI]TULO\s+(.+)', linea_stripped, re.IGNORECASE)
        match_capitulo = re.match(r'^CAP[ÍI]TULO\s+(.+)', linea_stripped, re.IGNORECASE)
        match_articulo = re.match(r'^Artículo\s*(\d+)[º°]?\.?-?.*', linea_stripped, re.IGNORECASE)
        
        es_marcador = match_libro or match_titulo or match_capitulo or match_articulo

        if es_marcador:
            guardar_articulo(numero_articulo_actual, buffer_articulo, contexto_actual, lista_de_articulos)
            buffer_articulo = []
            
            if match_articulo:
                numero_articulo_actual = match_articulo.group(1).strip()
                buffer_articulo.append(linea_stripped)
            else:
                numero_articulo_actual = None
                if match_libro:
                    contexto_actual['libro'] = match_libro.group(1).strip()
                    contexto_actual.update({'titulo': 'N/A', 'capitulo': 'N/A'})
                elif match_titulo:
                    contexto_actual['titulo'] = match_titulo.group(1).strip()
                    contexto_actual.update({'capitulo': 'N/A'})
                elif match_capitulo:
                    contexto_actual['capitulo'] = match_capitulo.group(1).strip()
        
        elif numero_articulo_actual:
            buffer_articulo.append(linea_stripped)

    guardar_articulo(numero_articulo_actual, buffer_articulo, contexto_actual, lista_de_articulos)

    print(f"\nProcesamiento finalizado. Se han estructurado {len(lista_de_articulos)} artículos.")
    
    if not os.path.exists(os.path.dirname(ARCHIVO_JSON_SALIDA)):
        os.makedirs(os.path.dirname(ARCHIVO_JSON_SALIDA))
    with open(ARCHIVO_JSON_SALIDA, 'w', encoding='utf-8') as f:
        json.dump(lista_de_articulos, f, ensure_ascii=False, indent=4)
    print(f"Datos estructurados guardados en: {ARCHIVO_JSON_SALIDA}")

if __name__ == "__main__":
    ruta_pdf = os.path.join(os.path.dirname(__file__), '..', NOMBRE_PDF_ENTRADA)
    texto_bruto = extraer_texto_pdf(ruta_pdf)
    if texto_bruto:
        texto_limpio = limpiar_texto(texto_bruto)
        procesar_y_estructurar(texto_limpio)