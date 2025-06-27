from server import app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
from fastapi import FastAPI
from pydantic import BaseModel
from utils.rag import obtener_respuesta  # <-- Este es el motor que ya tenés
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS para que Vercel pueda acceder a tu API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Podés restringir a tu dominio si querés más seguridad
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Consulta(BaseModel):
    pregunta: str

@app.post("/consultar")
def consultar(consulta: Consulta):
    respuesta = obtener_respuesta(consulta.pregunta)
    return {"respuesta": respuesta}
