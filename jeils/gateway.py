"""API Gateway (CORS, rate limiting, JWT). Spec: specs/04 (Integrante 4)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jeils.config import get_settings


def configurar_gateway(app: FastAPI) -> None:
    s = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    # TODO(integrante 4): límite de peticiones por IP (429) y validación JWT (401).
