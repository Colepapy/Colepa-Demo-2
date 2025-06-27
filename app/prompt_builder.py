# Archivo: app/prompt_builder.py

def construir_prompt(contexto_legal: str, pregunta_usuario: str) -> str:
    """
    Construye el prompt final para enviar al modelo de lenguaje.

    Args:
        contexto_legal: El texto del artículo de ley recuperado de Qdrant.
        pregunta_usuario: La pregunta original hecha por el usuario.

    Returns:
        Un string con el prompt completo y formateado.
    """

    # Usamos un "f-string" de Python para construir el texto fácilmente.
    # Los bloques con triples comillas ('''...''') nos permiten escribir texto en múltiples líneas.
    prompt = f'''
Contexto legal proporcionado:
---
{contexto_legal}
---

Pregunta del usuario:
{pregunta_usuario}

Instrucción para el asistente de IA:
Basándote únicamente en el "Contexto legal proporcionado", responde a la "Pregunta del usuario".
Tu respuesta debe ser clara y directa.
Si la información en el contexto no es suficiente para responder la pregunta, di explícitamente: "La información proporcionada en el contexto no es suficiente para responder a esa pregunta."
No inventes información ni añadas datos que no estén en el texto del artículo.
'''

    return prompt