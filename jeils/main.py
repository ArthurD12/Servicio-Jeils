from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from jeils.contracts import EvaluacionRequest, EvaluacionResponse
from jeils.gateway import configurar_gateway
from jeils.orchestrator import evaluar_locacion

app = FastAPI(title="Jeils", version="0.1.0")
configurar_gateway(app)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/evaluacion", response_model=EvaluacionResponse)
async def evaluacion(req: EvaluacionRequest):
    return await evaluar_locacion(req)


_frontend = Path(__file__).resolve().parent.parent / "frontend"
if _frontend.is_dir():
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")
