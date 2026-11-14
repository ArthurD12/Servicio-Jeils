
"""Pruebas del Adaptador SENAMHI."""
import pytest
from datetime import date
from jeils.contracts import Locacion
from jeils.adapters.senamhi import seleccionar_estacion
import jeils.adapters.senamhi as senamhi
from jeils.contracts import Locacion, FuenteNoDisponible
import httpx
from types import SimpleNamespace

from jeils.adapters.senamhi import (
    calcular_distancia_km,
    calcular_promedios_historicos,
    procesar_csv_senamhi,
)


def test_distancia_misma_ubicacion():
    distancia = calcular_distancia_km(
        -6.77, -79.84, -6.77, -79.84
    )

    assert distancia == 0


def test_procesar_csv():
    csv = (
        b"ESTACION;FECHA;LATITUD;LONGITUD;TEMP;HR;PP\n"
        b"Estacion A;01/11/2023;-6.77;-79.84;20;60;0\n"
        b"Estacion A;10/11/2024;-6.77;-79.84;24;80;2\n"
    )

    datos = procesar_csv_senamhi(csv)

    assert len(datos) == 2
    assert datos["TEMP"].mean() == 22


def test_promedios_historicos():
    csv = (
        b"ESTACION;FECHA;LATITUD;LONGITUD;TEMP;HR;PP\n"
        b"Estacion A;01/11/2023;-6.77;-79.84;20;60;0\n"
        b"Estacion A;10/11/2024;-6.77;-79.84;24;80;2\n"
        b"Estacion A;01/10/2024;-6.77;-79.84;30;90;5\n"
        b"Estacion A;01/11/2026;-6.77;-79.84;100;100;100\n"
    )

    datos = procesar_csv_senamhi(csv)

    resultado = calcular_promedios_historicos(
        datos, date(2026, 11, 20)
    )

    assert resultado is not None
    assert resultado.temperatura_promedio_c == 22
    assert resultado.humedad_promedio_pct == 70
    assert resultado.precipitacion_promedio_mm == 1
    assert resultado.n_registros == 2


def test_sin_registros_del_mes():
    csv = (
        b"ESTACION;FECHA;LATITUD;LONGITUD;TEMP;HR;PP\n"
        b"Estacion A;01/10/2024;-6.77;-79.84;25;70;1\n"
    )

    datos = procesar_csv_senamhi(csv)

    resultado = calcular_promedios_historicos(
        datos, date(2026, 11, 20)
    )

    assert resultado is None



def test_seleccionar_estacion_mas_cercana():
    csv = (
        b"ESTACION;FECHA;LATITUD;LONGITUD;TEMP;HR;PP;UBIGEO\n"
        b"Estacion A;01/11/2023;-6.77;-79.84;20;60;0;140101\n"
        b"Estacion A;01/11/2024;-6.77;-79.84;24;80;2;140101\n"
        b"Estacion B;01/11/2024;-12.05;-77.04;18;75;1;150101\n"
    )

    datos = procesar_csv_senamhi(csv)

    locacion = Locacion(
        latitud=-6.78,
        longitud=-79.85,
    )

    estacion, registros = seleccionar_estacion(
        datos, locacion
    )

    assert estacion is not None
    assert estacion.nombre == "Estacion A"
    assert estacion.distancia_km is not None
    assert estacion.distancia_km < 5
    assert len(registros) == 2


def test_seleccionar_estacion_por_ubigeo():
    csv = (
        b"ESTACION;FECHA;LATITUD;LONGITUD;TEMP;HR;PP;UBIGEO\n"
        b"Estacion A;01/11/2024;-6.77;-79.84;24;80;2;140101\n"
        b"Estacion B;01/11/2024;-12.05;-77.04;18;75;1;150101\n"
    )

    datos = procesar_csv_senamhi(csv)

    locacion = Locacion(ubigeo="140101")

    estacion, registros = seleccionar_estacion(
        datos, locacion
    )

    assert estacion is not None
    assert estacion.nombre == "Estacion A"
    assert estacion.distancia_km is None
    assert len(registros) == 1



@pytest.mark.asyncio
async def test_consultar_con_cache_vigente(monkeypatch):
    """Comprueba que no consulte SENAMHI si existe caché."""

    class CacheFalsa:
        async def get(self, clave):
            return {
                "estacion": None,
                "clima": None,
                "avisos": ["Información de caché"],
            }

    async def carga_prohibida():
        raise AssertionError(
            "No debía consultar SENAMHI"
        )

    monkeypatch.setattr(
        senamhi, "get_cache", lambda: CacheFalsa()
    )
    monkeypatch.setattr(
        senamhi, "cargar_datos_senamhi", carga_prohibida
    )

    resultado = await senamhi.consultar(
        Locacion(latitud=-6.77, longitud=-79.84),
        date(2026, 11, 20),
    )

    assert resultado.avisos == ["Información de caché"]


@pytest.mark.asyncio
async def test_consultar_calcula_y_guarda(monkeypatch):
    """Comprueba promedios y almacenamiento en caché."""

    csv = (
        b"ESTACION;FECHA;LATITUD;LONGITUD;TEMP;HR;PP\n"
        b"Estacion A;01/11/2023;-6.77;-79.84;20;60;0\n"
        b"Estacion A;01/11/2024;-6.77;-79.84;24;80;2\n"
    )

    datos = senamhi.procesar_csv_senamhi(csv)

    class CacheFalsa:
        def __init__(self):
            self.guardado = None

        async def get(self, clave):
            return None

        async def set(self, clave, valor, ttl=None):
            self.guardado = valor

    cache = CacheFalsa()

    async def carga_simulada():
        return datos, False

    monkeypatch.setattr(
        senamhi, "get_cache", lambda: cache
    )
    monkeypatch.setattr(
        senamhi, "cargar_datos_senamhi", carga_simulada
    )

    resultado = await senamhi.consultar(
        Locacion(latitud=-6.77, longitud=-79.84),
        date(2026, 11, 20),
    )

    assert resultado.estacion is not None
    assert resultado.estacion.nombre == "Estacion A"
    assert resultado.clima is not None
    assert resultado.clima.temperatura_promedio_c == 22
    assert resultado.clima.humedad_promedio_pct == 70
    assert resultado.clima.precipitacion_promedio_mm == 1
    assert cache.guardado is not None


@pytest.mark.asyncio
async def test_consultar_usa_cache_vencida(monkeypatch):
    """Comprueba recuperación ante caída de SENAMHI."""

    class CacheFalsa:
        async def get(self, clave):
            return None

        async def get_stale(self, clave):
            return {
                "estacion": None,
                "clima": None,
                "avisos": [],
            }

    async def carga_con_error():
        raise FuenteNoDisponible("SENAMHI")

    monkeypatch.setattr(
        senamhi, "get_cache", lambda: CacheFalsa()
    )
    monkeypatch.setattr(
        senamhi, "cargar_datos_senamhi", carga_con_error
    )

    resultado = await senamhi.consultar(
        Locacion(latitud=-6.77, longitud=-79.84),
        date(2026, 11, 20),
    )

    assert resultado.clima is None
    assert any(
        "información anterior" in aviso.lower()
        for aviso in resultado.avisos
    )


@pytest.mark.asyncio
async def test_consultar_falla_sin_respaldo(monkeypatch):
    """Comprueba que se informa el fallo sin caché."""

    class CacheFalsa:
        async def get(self, clave):
            return None

        async def get_stale(self, clave):
            return None

    async def carga_con_error():
        raise FuenteNoDisponible("SENAMHI")

    monkeypatch.setattr(
        senamhi, "get_cache", lambda: CacheFalsa()
    )
    monkeypatch.setattr(
        senamhi, "cargar_datos_senamhi", carga_con_error
    )

    with pytest.raises(FuenteNoDisponible):
        await senamhi.consultar(
            Locacion(latitud=-6.77, longitud=-79.84),
            date(2026, 11, 20),
        )



def test_identificar_recurso_csv():
    """RF-3: encuentra el recurso CSV en CKAN."""

    metadatos = {
        "resources": [
            {
                "format": "JSON",
                "url": "https://ejemplo.com/datos.json",
            },
            {
                "format": "CSV",
                "url": "https://ejemplo.com/datos.csv",
            },
        ]
    }

    url = senamhi.obtener_url_csv(metadatos)

    assert url == "https://ejemplo.com/datos.csv"


@pytest.mark.asyncio
async def test_descargar_csv_octet_stream(monkeypatch):
    """RF-8: acepta un CSV como application/octet-stream."""

    contenido = b"ESTACION;TEMP\nEstacion A;25\n"

    def responder(request):
        return httpx.Response(
            200,
            headers={
                "content-type": "application/octet-stream"
            },
            content=contenido,
        )

    transporte = httpx.MockTransport(responder)
    cliente_original = httpx.AsyncClient

    monkeypatch.setattr(
        senamhi.httpx,
        "AsyncClient",
        lambda **kwargs: cliente_original(
            transport=transporte,
            **kwargs,
        ),
    )

    resultado = await senamhi.descargar_csv_senamhi(
        "https://ejemplo.com/clima.csv"
    )

    assert resultado == contenido


@pytest.mark.asyncio
async def test_aviso_cobertura_limitada(monkeypatch):
    """RF-5: avisa si la estación está a más de 100 km."""

    csv = (
        b"ESTACION;FECHA;LATITUD;LONGITUD;TEMP;HR;PP\n"
        b"Estacion Lejana;01/11/2024;-12.05;-77.04;22;70;1\n"
    )

    datos = senamhi.procesar_csv_senamhi(csv)

    class CacheFalsa:
        async def get(self, clave):
            return None

        async def set(self, clave, valor, ttl=None):
            pass

    async def carga_simulada():
        return datos, False

    monkeypatch.setattr(
        senamhi, "get_cache", lambda: CacheFalsa()
    )

    monkeypatch.setattr(
        senamhi, "cargar_datos_senamhi", carga_simulada
    )

    monkeypatch.setattr(
        senamhi,
        "get_settings",
        lambda: SimpleNamespace(
            max_station_distance_km=100.0
        ),
    )

    resultado = await senamhi.consultar(
        Locacion(latitud=-6.77, longitud=-79.84),
        date(2026, 11, 20),
    )

    assert resultado.estacion is not None
    assert resultado.estacion.distancia_km > 100

    assert any(
        "Cobertura limitada" in aviso
        for aviso in resultado.avisos
    )



@pytest.mark.asyncio
async def test_ckan_obtiene_metadatos(monkeypatch):
    """RF-3: CKAN devuelve los metadatos del CSV."""

    def responder(request):
        return httpx.Response(
            200,
            json={
                "success": True,
                "result": {
                    "resources": [
                        {
                            "format": "CSV",
                            "url": "https://ejemplo.com/clima.csv",
                        }
                    ]
                },
            },
        )

    transporte = httpx.MockTransport(responder)
    cliente_original = httpx.AsyncClient

    monkeypatch.setattr(
        senamhi.httpx,
        "AsyncClient",
        lambda **kwargs: cliente_original(
            transport=transporte, **kwargs
        ),
    )

    resultado = await senamhi.obtener_metadatos_senamhi()

    assert "resources" in resultado
    assert senamhi.obtener_url_csv(
        resultado
    ) == "https://ejemplo.com/clima.csv"


@pytest.mark.asyncio
async def test_ckan_reintenta_ante_error_http(monkeypatch):
    """Comprueba los dos reintentos configurados."""

    contador = {"intentos": 0}

    def responder(request):
        contador["intentos"] += 1

        if contador["intentos"] < 3:
            return httpx.Response(503)

        return httpx.Response(
            200,
            json={
                "success": True,
                "result": {"resources": []},
            },
        )

    transporte = httpx.MockTransport(responder)
    cliente_original = httpx.AsyncClient

    monkeypatch.setattr(
        senamhi.httpx,
        "AsyncClient",
        lambda **kwargs: cliente_original(
            transport=transporte, **kwargs
        ),
    )

    async def pausa_simulada(segundos):
        pass

    monkeypatch.setattr(
        senamhi.asyncio,
        "sleep",
        pausa_simulada,
    )

    resultado = await senamhi.obtener_metadatos_senamhi()

    assert contador["intentos"] == 3
    assert resultado == {"resources": []}


@pytest.mark.asyncio
async def test_csv_no_se_descarga_dos_veces(monkeypatch):
    """Comprueba que se reutiliza el CSV procesado."""

    contador = {"descargas": 0}

    csv = (
        b"ESTACION;FECHA;LATITUD;LONGITUD;TEMP;HR;PP\n"
        b"Estacion A;01/11/2024;-6.77;-79.84;24;80;2\n"
    )

    async def metadatos_simulados():
        return {
            "resources": [
                {
                    "format": "CSV",
                    "url": "https://ejemplo.com/clima.csv",
                }
            ]
        }

    async def descarga_simulada(url):
        contador["descargas"] += 1
        return csv

    # Reiniciar únicamente la copia en memoria del test.
    monkeypatch.setattr(
        senamhi, "_datos_senamhi", None
    )
    monkeypatch.setattr(
        senamhi, "_momento_datos_senamhi", 0.0
    )

    monkeypatch.setattr(
        senamhi,
        "obtener_metadatos_senamhi",
        metadatos_simulados,
    )

    monkeypatch.setattr(
        senamhi,
        "descargar_csv_senamhi",
        descarga_simulada,
    )

    datos_1, _ = await senamhi.cargar_datos_senamhi()
    datos_2, _ = await senamhi.cargar_datos_senamhi()

    assert contador["descargas"] == 1
    assert len(datos_1) == 1
    assert len(datos_2) == 1




def test_fechas_reales_senamhi():
    """Comprueba fechas en formato AAAAMMDD."""

    csv = (
        b"ESTACION,FECHA,LATITUD,LONGITUD,TEMP,HR,PP\n"
        b"Estacion A,20151101,-6.77,-79.84,20,60,0\n"
        b"Estacion A,20231120,-6.77,-79.84,24,80,2\n"
    )

    datos = senamhi.procesar_csv_senamhi(csv)

    assert datos.iloc[0]["FECHA"].year == 2015
    assert datos.iloc[0]["FECHA"].month == 11
    assert datos.iloc[1]["FECHA"].year == 2023

    resultado = senamhi.calcular_promedios_historicos(
        datos,
        date(2026, 11, 20),
    )

    assert resultado is not None
    assert resultado.n_registros == 2
    assert resultado.temperatura_promedio_c == 22




@pytest.mark.asyncio
async def test_ckan_devuelve_lista(monkeypatch):
    """Verifica que CKAN pueda devolver recursos dentro de una lista."""

    def responder(request):
        return httpx.Response(
            200,
            json={
                "success": True,
                "result": [
                    {
                        "resources": [
                            {
                                "format": "CSV",
                                "url": "https://ejemplo.com/clima.csv",
                            }
                        ]
                    }
                ],
            },
        )

    transporte = httpx.MockTransport(responder)
    cliente_original = httpx.AsyncClient

    monkeypatch.setattr(
        senamhi.httpx,
        "AsyncClient",
        lambda **kwargs: cliente_original(
            transport=transporte,
            **kwargs,
        ),
    )

    datos = await senamhi.obtener_metadatos_senamhi()

    assert isinstance(datos, dict)
    assert senamhi.obtener_url_csv(datos) == (
        "https://ejemplo.com/clima.csv"
    )
