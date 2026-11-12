
"""API Gateway: CORS, límite de solicitudes y JWT.

Módulo del Integrante 4. Spec: 04-gateway-cache.
"""
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from jeils.config import get_settings

log = logging.getLogger(__name__)


def validar_jwt(token: str, secreto: str) -> bool:
    """Valida firma HS256 y fecha de expiración del token."""
    try:
        partes = token.split(".")
        if len(partes) != 3 or not secreto:
            return False

        encabezado, contenido, firma = partes

        def decodificar(valor):
            relleno = "=" * (-len(valor) % 4)
            return base64.urlsafe_b64decode(valor + relleno)

        header = json.loads(decodificar(encabezado))
        payload = json.loads(decodificar(contenido))

        if header.get("alg") != "HS256":
            return False

        mensaje = f"{encabezado}.{contenido}".encode()
        firma_esperada = hmac.new(
            secreto.encode(),
            mensaje,
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(
            firma_esperada, decodificar(firma)
        ):
            return False

        expiracion = payload.get("exp")

       
        return (
            not isinstance(expiracion, bool)
            and isinstance(expiracion, (int, float))
            and expiracion > time.time()
        )

    except (ValueError, TypeError, KeyError):
        return False


def configurar_gateway(app: FastAPI) -> None:

    """Configura la seguridad y el acceso a la API."""
    s = get_settings()
    if s.jwt_required and not s.jwt_secret:
        raise ValueError(
            "JWT_REQUIRED está activado, pero falta JWT_SECRET"
        )
    # Orígenes permitidos para solicitudes desde navegadores.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Registro de solicitudes por dirección IP.
    solicitudes = defaultdict(deque)
    bloqueo_solicitudes = asyncio.Lock()
    async def seguridad(request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        ip = request.client.host if request.client else "desconocida"

        async with bloqueo_solicitudes:
            ahora = time.monotonic()
            historial = solicitudes[ip]

            while (
                historial
                and ahora - historial[0] >= s.rate_limit_window_seconds
            ):
                historial.popleft()

            if len(historial) >= s.rate_limit_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Demasiadas solicitudes"},
                )

            historial.append(ahora)


        # JWT protege la evaluación cuando está habilitado.
        if (
            s.jwt_required
            and request.url.path == "/api/v1/evaluacion"
        ):
            autorizacion = request.headers.get(
                "Authorization", ""
            )

            esquema, separador, token = autorizacion.partition(" ")

            if (
                not separador
                or esquema.lower() != "bearer"
                or not validar_jwt(token.strip(), s.jwt_secret)
            ):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token inválido o ausente"},
                )

        return await call_next(request)

    app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=seguridad,
    )

    log.info("Gateway configurado correctamente")
