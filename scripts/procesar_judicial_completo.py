# Archivo: scripts/procesar_judicial_completo.py (Versión con Limpieza de Caracteres de Control)

import os
import re
import fitz  # PyMuPDF
import json

# --- CONFIGURACIÓN ---
NOMBRE_PDF_ENTRADA = "Código de Organización Judicial-Texto Consolidado.pdf"
DIRECTORIO_TXT_SALIDA = os.path.join(os.path.dirname(__file__), '..', 'data', 'judicial_articulos_txt')
ARCHIVO_JSON_SALIDA = os.path.join(os.path.dirname(__file__), '..', 'data', 'judicial_data_completo.json')

# --- LÓGICA ---

def extraer_texto_pdf(ruta_pdf):
    # (Esta función no cambia)
    print(f"Abriendo y leyendo: {ruta_pdf}")
    try:
        documento = fitz.open(ruta_pdf)
        texto_completo = ""
        for num_pagina in range(9, len(documento)):
            texto_completo += documento[num_pagina].get_text("text", sort=True) + "\n"
        return texto_completo
    except Exception as e:
        return f"Error al leer el PDF: {e}"

def limpieza_quirurgica(texto):
    # (Esta función no cambia)
    print("Iniciando limpieza profunda del texto...")
    lineas_originales = texto.split('\n')
    lineas_limpias = []
    patrones_de_ruido = [
        r"Sesquicentenario de la Epopoya Nacional", "PODER LEGISLATIVO", 
        "Honorable Cámara de Senadores", "Digesto Legislativo", "Oficina: Primer Piso", 
        "Email: digesto@senado\.gov\.py", "Telefono: 021 4145112", 
        r"ICA DEL PAR", r"\bJA\b"
    ]
    for linea in lineas_originales:
        linea_stripped = linea.strip()
        if not linea_stripped or re.fullmatch(r'\d+', linea_stripped):
            continue
        if not any(re.search(patron, linea, re.IGNORECASE) for patron in patrones_de_ruido):
            lineas_limpias.append(linea)
    texto_procesado = "\n".join(lineas_limpias)
    texto_procesado = re.sub(r'(\n\s*){2,}', "\n\n", texto_procesado)
    print("Limpieza profunda completada.")
    return texto_procesado

def guardar_articulo_estructurado(numero_articulo, buffer, contexto, lista_json, dir_txt):
    """Guarda el artículo en formatos .txt y .json, con limpieza final."""
    if not numero_articulo or not buffer: return

    texto_completo = "\n".join(buffer).strip()
    
    # --- ¡NUEVA LIMPIEZA FINAL ANTES DE GUARDAR! ---
    # Reemplazamos los saltos de línea y otros caracteres de control por un espacio.
    texto_limpio_para_json = re.sub(r'[\n\r\t]', ' ', texto_completo)
    
    nota_estado = "Vigente"
    patron_nota = r'(Ampliado Por:|Modificado por|Derogado Por:)[\s\S]+'
    match_nota = re.search(patron_nota, texto_limpio_para_json, re.IGNORECASE)
    if match_nota:
        nota_estado = " ".join(match_nota.group(0).strip().split())
        texto_principal = re.split(patron_nota, texto_limpio_para_json, flags=re.IGNORECASE)[0].strip()
    else:
        texto_principal = texto_limpio_para_json

    # 1. Preparar el objeto para JSON con el texto limpio
    lista_json.append({
        "numero_str": numero_articulo, "texto": texto_principal, "estado": nota_estado,
        "contexto": contexto.copy()
    })

    # 2. Preparar el contenido para el .txt (mantenemos los saltos de línea para legibilidad)
    formato_txt = (
        f"CONTEXTO:\n"
        f"LIBRO: {contexto.get('libro', 'N/A')}\n"
        f"TITULO: {contexto.get('titulo', 'N/A')}\n"
        f"CAPITULO: {contexto.get('capitulo', 'N/A')}\n"
        f"SECCIÓN: {contexto.get('seccion', 'N/A')}\n"
        f"---\n"
        f"ESTADO: {nota_estado.replace('  ', ' ')}\n"
        f"---\n"
        f"TEXTO DEL ARTÍCULO:\n{texto_completo}\n" # Usamos el texto con saltos de línea para el .txt
    )

    nombre_archivo = f"articulo_{numero_articulo}.txt"
    with open(os.path.join(dir_txt, nombre_archivo), 'w', encoding='utf-8') as f:
        f.write(formato_txt)
    print(f"Guardado TXT: {nombre_archivo}")

def procesar_documento(texto_limpio):
    # (Esta función no cambia)
    if not os.path.exists(DIRECTORIO_TXT_SALIDA):
        os.makedirs(DIRECTORIO_TXT_SALIDA)
    contexto_actual = {'libro': 'N/A', 'titulo': 'N/A', 'capitulo': 'N/A', 'seccion': 'N/A'}
    buffer_articulo = []
    numero_articulo_actual = None
    lista_para_json = []
    lineas = texto_limpio.split('\n')
    for linea in lineas:
        linea_stripped = linea.strip()
        if not linea_stripped: continue
        match_libro = re.match(r'^LIBRO\s+(.+)', linea_stripped, re.IGNORECASE)
        match_titulo = re.match(r'^T[ÍI]TULO\s+(.+)', linea_stripped, re.IGNORECASE)
        match_capitulo = re.match(r'^CAP[ÍI]TULO\s+(.+)', linea_stripped, re.IGNORECASE)
        match_seccion = re.match(r'^SECCI[ÓO]N\s+(.+)', linea_stripped, re.IGNORECASE)
        match_articulo = re.match(r'^Artículo\s*(\d+)[º°]?\.?-?.*', linea_stripped, re.IGNORECASE)
        es_marcador = match_libro or match_titulo or match_capitulo or match_seccion or match_articulo
        if es_marcador:
            guardar_articulo_estructurado(numero_articulo_actual, buffer_articulo, contexto_actual, lista_para_json, DIRECTORIO_TXT_SALIDA)
            buffer_articulo = []
            if match_articulo:
                numero_articulo_actual = match_articulo.group(1).strip()
            else:
                numero_articulo_actual = None
                if match_libro:
                    contexto_actual['libro'] = match_libro.group(1).strip()
                    contexto_actual.update({'titulo': 'N/A', 'capitulo': 'N/A', 'seccion': 'N/A'})
                elif match_titulo:
                    contexto_actual['titulo'] = match_titulo.group(1).strip()
                    contexto_actual.update({'capitulo': 'N/A', 'seccion': 'N/A'})
                elif match_capitulo:
                    contexto_actual['capitulo'] = match_capitulo.group(1).strip()
                    contexto_actual.update({'seccion': 'N/A'})
                elif match_seccion:
                    contexto_actual['seccion'] = match_seccion.group(1).strip()
        if numero_articulo_actual is not None:
             buffer_articulo.append(linea_stripped)
    guardar_articulo_estructurado(numero_articulo_actual, buffer_articulo, contexto_actual, lista_para_json, DIRECTORIO_TXT_SALIDA)
    print(f"\nProcesamiento finalizado. Se han procesado y guardado {len(lista_para_json)} artículos.")
    
    with open(ARCHIVO_JSON_SALIDA, 'w', encoding='utf-8') as f:
        json.dump(lista_para_json, f, ensure_ascii=False, indent=4)
    print(f"Datos estructurados completos guardados en: {ARCHIVO_JSON_SALIDA}")

if __name__ == "__main__":
    ruta_pdf_completa = os.path.join(os.path.dirname(__file__), '..', NOMBRE_PDF_ENTRADA)
    texto_bruto = extraer_texto_pdf(ruta_pdf_completa)
    if texto_bruto:
        texto_limpio = limpieza_quirurgica(texto_bruto)
        procesar_documento(texto_limpio)