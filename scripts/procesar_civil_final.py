# Archivo: scripts/procesar_civil_final.py

import os
import re
import fitz  # PyMuPDF
import json

# --- CONFIGURACIÓN ---
NOMBRE_PDF_ENTRADA = "Código Civil-Texto Consolidado.pdf"
DIRECTORIO_DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
ARCHIVO_JSON_SALIDA = os.path.join(DIRECTORIO_DATA, 'civil_data.json')

# --- LÓGICA ---

def extraer_texto_pdf(ruta_pdf):
    print(f"Abriendo y leyendo: {ruta_pdf}")
    try:
        documento = fitz.open(ruta_pdf)
        texto_completo = ""
        # Rango de páginas para el Código Civil (empieza en la pág. 23)
        for num_pagina in range(22, len(documento)):
            texto_completo += documento[num_pagina].get_text("text", sort=True) + "\n"
        return texto_completo
    except Exception as e:
        return f"Error al leer el PDF: {e}"

def procesar_y_estructurar(texto_bruto):
    if not os.path.exists(DIRECTORIO_DATA):
        os.makedirs(DIRECTORIO_DATA)

    # Limpieza
    textos_a_eliminar = [
        r"Sesquicentenario de la Epop(e|o)ya Nacional\s*\d{4}-\d{4}",
        r"Texto consolidado de la Ley N° 1183/1985",
        r"Oficina: Primer Piso- Cámara de Senadores",
        r"Email: digesto@senado\.gov\.py",
        r"Telefono: 021 4145112",
        r"\bER/JA\b"
    ]
    texto_limpio = texto_bruto
    for patron in textos_a_eliminar:
        texto_limpio = re.sub(patron, "", texto_limpio, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'^\s*\d+\s*$', '', texto_limpio, flags=re.MULTILINE)
    texto_limpio = re.sub(r'(\n\s*){2,}', "\n", texto_limpio)
    print("Limpieza de texto completada.")

    # Lógica de extracción línea por línea
    contexto_actual = {'libro': 'N/A', 'titulo': 'N/A', 'capitulo': 'N/A', 'seccion': 'N/A'}
    buffer_articulo = []
    numero_articulo_actual = None
    lista_de_articulos = []
    lineas = texto_limpio.split('\n')

    for linea in lineas:
        linea_stripped = linea.strip()
        if not linea_stripped: continue

        # Patrones para la estructura del Código Civil
        match_libro = re.match(r'^LIBRO\s+(.+)', linea_stripped, re.IGNORECASE)
        match_titulo = re.match(r'^T[ÍI]TULO\s+(.+)', linea_stripped, re.IGNORECASE)
        match_capitulo = re.match(r'^CAP[ÍI]TULO\s+(.+)', linea_stripped, re.IGNORECASE)
        match_seccion = re.match(r'^SECCI[ÓO]N\s+(.+)', linea_stripped, re.IGNORECASE)
        match_articulo = re.match(r'^Art\.\s*([\d\.]+)\.?-?.*', linea_stripped, re.IGNORECASE)
        es_marcador = match_libro or match_titulo or match_capitulo or match_seccion or match_articulo

        if es_marcador:
            if numero_articulo_actual and buffer_articulo:
                lista_de_articulos.append({
                    "numero_str": numero_articulo_actual,
                    "texto": "\n".join(buffer_articulo),
                    **contexto_actual
                })
            
            buffer_articulo = []
            
            if match_articulo:
                numero_articulo_actual = match_articulo.group(1).strip()
                buffer_articulo.append(linea_stripped)
            else:
                numero_articulo_actual = None
                if match_libro: contexto_actual['libro'] = match_libro.group(1).strip()
                if match_titulo: contexto_actual['titulo'] = match_titulo.group(1).strip()
                if match_capitulo: contexto_actual['capitulo'] = match_capitulo.group(1).strip()
                if match_seccion: contexto_actual['seccion'] = match_seccion.group(1).strip()
        
        elif numero_articulo_actual:
            buffer_articulo.append(linea_stripped)

    # Guardar el último artículo
    if numero_articulo_actual and buffer_articulo:
        lista_de_articulos.append({
            "numero_str": numero_articulo_actual,
            "texto": "\n".join(buffer_articulo),
            **contexto_actual
        })

    print(f"Procesamiento finalizado. Se han estructurado {len(lista_de_articulos)} artículos.")
    
    with open(ARCHIVO_JSON_SALIDA, 'w', encoding='utf-8') as f:
        json.dump(lista_de_articulos, f, ensure_ascii=False, indent=4)
        
    print(f"Datos estructurados guardados en: {ARCHIVO_JSON_SALIDA}")

if __name__ == "__main__":
    ruta = os.path.join(os.path.dirname(__file__), '..', NOMBRE_PDF_ENTRADA)
    texto = extraer_texto_pdf(ruta)
    if texto and not texto.startswith("Error"):
        procesar_y_estructurar(texto)