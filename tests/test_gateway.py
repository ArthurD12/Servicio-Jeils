
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from jeils.config import Settings
from jeils.gateway import configurar_gateway, validar_jwt


def crear_app(monkeypatch, **configuracion):
    settings = Settings(
        _env_file=None,
        **configuracion,
    )

    monkeypatch.setattr(
        "jeils.gateway.get_settings",
        lambda: settings,
    )

    app = FastAPI()
    configurar_gateway(app)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/v1/evaluacion")
    def evaluacion():
        return {"resultado": "ok"}

    return app


def test_gateway_health(monkeypatch):
    app = crear_app(monkeypatch)

    with TestClient(app) as cliente:
        respuesta = cliente.get("/health")

    assert respuesta.status_code == 200


def test_gateway_rate_limit(monkeypatch):
    app = crear_app(
        monkeypatch,
        rate_limit_requests=2,
        rate_limit_window_seconds=60,
    )

    with TestClient(app) as cliente:
        assert cliente.get("/health").status_code == 200
        assert cliente.get("/health").status_code == 200

        respuesta = cliente.get("/health")

    assert respuesta.status_code == 429


def test_gateway_jwt_obligatorio(monkeypatch):
    app = crear_app(
        monkeypatch,
        jwt_required=True,
        jwt_secret="secreto-solo-para-pruebas",
    )

    with TestClient(app) as cliente:
        respuesta = cliente.post("/api/v1/evaluacion")

    assert respuesta.status_code == 401


def test_gateway_jwt_invalido():
    assert validar_jwt(
        "token.invalido.prueba",
        "secreto-solo-para-pruebas",
    ) is False


def test_gateway_cors(monkeypatch):
    app = crear_app(
        monkeypatch,
        cors_origins=["http://localhost:5500"],
    )

    with TestClient(app) as cliente:
        respuesta = cliente.options(
            "/api/v1/evaluacion",
            headers={
                "Origin": "http://localhost:5500",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert respuesta.status_code == 200
    assert (
        respuesta.headers.get("access-control-allow-origin")
        == "http://localhost:5500"
    )


def test_gateway_jwt_valido(monkeypatch):
    import base64
    import hashlib
    import hmac
    import json

    secreto = "secreto-solo-para-pruebas"

    def codificar(datos):
        contenido = json.dumps(datos).encode()
        return base64.urlsafe_b64encode(
            contenido
        ).rstrip(b"=").decode()

    encabezado = codificar({
        "alg": "HS256",
        "typ": "JWT",
    })

    contenido = codificar({
        "sub": "usuario-prueba",
        "exp": time.time() + 3600,
    })

    mensaje = f"{encabezado}.{contenido}"

    firma = hmac.new(
        secreto.encode(),
        mensaje.encode(),
        hashlib.sha256,
    ).digest()

    firma_codificada = base64.urlsafe_b64encode(
        firma
    ).rstrip(b"=").decode()

    token = f"{mensaje}.{firma_codificada}"

    app = crear_app(
        monkeypatch,
        jwt_required=True,
        jwt_secret=secreto,
    )

    with TestClient(app) as cliente:
        respuesta = cliente.post(
            "/api/v1/evaluacion",
            headers={
                "Authorization": f"Bearer {token}"
            },
        )

    assert respuesta.status_code == 200


def test_gateway_cors_origen_no_autorizado(monkeypatch):
    app = crear_app(
        monkeypatch,
        cors_origins=["http://localhost:5500"],
    )

    with TestClient(app) as cliente:
        respuesta = cliente.options(
            "/api/v1/evaluacion",
            headers={
                "Origin": "https://sitio-no-autorizado.com",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert (
        respuesta.headers.get("access-control-allow-origin")
        is None
    )
