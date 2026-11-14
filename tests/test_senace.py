"""Cubre spec 02 (RF-1 a RF-8). Sin internet: la API de SENACE y la caché se simulan."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from jeils.adapters import senace
from jeils.cache import MemoryCache
from jeils.contracts import FuenteNoDisponible, Locacion, ResultadoSenace

AJUSTES = SimpleNamespace(
    senace_api_key="CLAVE_DE_PRUEBA",
    senace_url="https://ejemplo.test/CarteraProyectos",
    http_timeout_seconds=3.5,
    http_max_retries=2,
    cache_ttl_seconds=3600,
)

REGISTROS = [
    {
        "ID": 7,
        "TITULAR": "AUTOPISTA DEL NORTE S.A.C.",
        "RUC": "20520929658",
        "TITULO_PROYECTO": "REHABILITACIÓN DE LA CALZADA: TRAMO VIAL PATIVILCA-SANTA",
        "UNIDAD_PROYECTO": "EVAP PROYECTO TRAMO PATIVILCA - SANTA",
        "TIPO": "Clasificación",
        "ACTIVIDAD": "Transportes",
        "FECHA_INICIO": "29/03/2019",
        "ESTADO": "Aprobado",
    },
    {
        "ID": 8,
        "TITULAR": "MINERA X",
        "RUC": "20100000001",
        "TITULO_PROYECTO": "Ampliación de planta en Limache",
        "UNIDAD_PROYECTO": "Unidad Limache",
        "TIPO": "Clasificación",
        "ACTIVIDAD": "Minería",
        "FECHA_INICIO": "fecha-rota",
        "ESTADO": "En evaluación",
    },
]


class FalsaRespuesta:
    def __init__(self, status=200, datos=None, json_roto=False):
        self.status_code = status
        self._datos = datos
        self._json_roto = json_roto

    def json(self):
        if self._json_roto:
            raise ValueError("JSON mal formado")
        return self._datos


def falso_cliente(respuestas, llamadas):
    """Crea un reemplazo de httpx.AsyncClient que devuelve `respuestas` en orden."""

    class FalsoCliente:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None):
            llamadas.append({"url": url, "params": params})
            return respuestas[min(len(llamadas) - 1, len(respuestas) - 1)]

    return FalsoCliente


@pytest.fixture
def entorno():
    """Caché nueva, ajustes de prueba y sin esperas reales entre reintentos."""
    cache = MemoryCache()
    with patch.object(senace, "get_cache", return_value=cache), \
         patch.object(senace, "get_settings", return_value=AJUSTES), \
         patch.object(senace.asyncio, "sleep", new=AsyncMock()):
        yield cache


def con_respuestas(respuestas):
    llamadas = []
    return llamadas, patch.object(senace.httpx, "AsyncClient", falso_cliente(respuestas, llamadas))



async def test_rf1_devuelve_resultado_con_proyectos_coincidentes(entorno):
    llamadas, parche = con_respuestas([FalsaRespuesta(200, REGISTROS)])
    with parche:
        r = await senace.consultar(Locacion(departamento="Lima", distrito="Pativilca"))
    assert isinstance(r, ResultadoSenace)
    assert r.total == 1 and [p.id for p in r.proyectos] == [7]
    assert r.proyectos[0].titular == "AUTOPISTA DEL NORTE S.A.C."


async def test_rf2_envia_api_key_en_auth_key_desde_configuracion(entorno):
    llamadas, parche = con_respuestas([FalsaRespuesta(200, REGISTROS)])
    with parche:
        await senace.consultar(Locacion(departamento="Áncash", distrito="Pativilca"))
    assert llamadas[0]["params"] == {"auth_key": "CLAVE_DE_PRUEBA"}
    assert "CLAVE_DE_PRUEBA" not in open(senace.__file__, encoding="utf-8").read()


async def test_rf3_con_cache_vigente_no_llama_a_senace(entorno):
    await entorno.set(senace.CLAVE_CACHE, REGISTROS)
    llamadas, parche = con_respuestas([FalsaRespuesta(500)])
    with parche:
        r = await senace.consultar(Locacion(departamento="Áncash", distrito="Pativilca"))
    assert llamadas == []
    assert r.total == 1


async def test_rf3_guarda_en_cache_tras_consultar(entorno):
    _, parche = con_respuestas([FalsaRespuesta(200, REGISTROS)])
    with parche:
        await senace.consultar(Locacion(departamento="Áncash", distrito="Pativilca"))
    assert await entorno.get(senace.CLAVE_CACHE) == REGISTROS


async def test_rf4_respuesta_que_no_es_lista_se_trata_como_fallo(entorno):
    _, parche = con_respuestas([FalsaRespuesta(200, {"error": "x"})])
    with parche, pytest.raises(FuenteNoDisponible):
        await senace.consultar(Locacion(departamento="Áncash", distrito="Pativilca"))


async def test_rf4_estado_distinto_de_200_se_trata_como_fallo(entorno):
    _, parche = con_respuestas([FalsaRespuesta(500)])
    with parche, pytest.raises(FuenteNoDisponible):
        await senace.consultar(Locacion(departamento="Áncash", distrito="Pativilca"))


async def test_rf4_json_mal_formado_se_trata_como_fallo(entorno):
    _, parche = con_respuestas([FalsaRespuesta(200, json_roto=True)])
    with parche, pytest.raises(FuenteNoDisponible):
        await senace.consultar(Locacion(departamento="Áncash", distrito="Pativilca"))


async def test_rf5_ignora_mayusculas_tildes_y_no_confunde_palabras_parecidas(entorno):
    _, parche = con_respuestas([FalsaRespuesta(200, REGISTROS)])
    with parche:
        r = await senace.consultar(Locacion(departamento="Áncash", distrito="PÁTIVILCA"))
        assert [p.id for p in r.proyectos] == [7]
        r2 = await senace.consultar(Locacion(departamento="Lima"))
    # "Lima" NO debe coincidir con "Limache"
    assert r2.proyectos == []


async def test_rf6_sin_coincidencias_devuelve_lista_vacia_con_aviso(entorno):
    _, parche = con_respuestas([FalsaRespuesta(200, REGISTROS)])
    with parche:
        r = await senace.consultar(Locacion(departamento="Áncash", distrito="Tumbes"))
    assert r.proyectos == [] and r.total == 0
    assert any("texto" in a and "incompleta" in a for a in r.avisos)


async def test_rf6_locacion_solo_con_coordenadas_devuelve_vacio_con_aviso(entorno):
    _, parche = con_respuestas([FalsaRespuesta(200, REGISTROS)])
    with parche:
        r = await senace.consultar(Locacion(latitud=-10.6, longitud=-77.7))
    assert r.proyectos == [] and r.avisos


async def test_rf7_api_key_invalida_sin_cache_lanza_fuente_no_disponible(entorno):
    llamadas, parche = con_respuestas([FalsaRespuesta(401)])
    with parche, pytest.raises(FuenteNoDisponible):
        await senace.consultar(Locacion(departamento="Áncash", distrito="Pativilca"))
    assert len(llamadas) == 1  # con 401/403 no se reintenta


async def test_rf7_si_senace_cae_usa_la_copia_de_cache(entorno):
    # Copia ya vencida (ttl=0): get() no la ve, get_stale() sí.
    await entorno.set(senace.CLAVE_CACHE, REGISTROS, ttl=0)
    _, parche = con_respuestas([FalsaRespuesta(403)])
    with parche:
        r = await senace.consultar(Locacion(departamento="Áncash", distrito="Pativilca"))
    assert r.total == 1
    assert any("anteriormente" in a for a in r.avisos)


async def test_rf7_reintenta_y_se_recupera(entorno):
    llamadas, parche = con_respuestas([FalsaRespuesta(500), FalsaRespuesta(200, REGISTROS)])
    with parche:
        r = await senace.consultar(Locacion(departamento="Áncash", distrito="Pativilca"))
    assert len(llamadas) == 2 and r.total == 1


async def test_rf7_sin_api_key_configurada_lanza_error_sin_llamar(entorno):
    sin_clave = SimpleNamespace(**{**AJUSTES.__dict__, "senace_api_key": ""})
    llamadas, parche = con_respuestas([FalsaRespuesta(200, REGISTROS)])
    with parche, patch.object(senace, "get_settings", return_value=sin_clave), \
         pytest.raises(FuenteNoDisponible):
        await senace.consultar(Locacion(departamento="Áncash", distrito="Pativilca"))
    assert llamadas == []


async def test_rf8_convierte_fecha_ddmmaaaa_a_date_y_tolera_fechas_rotas(entorno):
    registros = [dict(REGISTROS[0]), {**REGISTROS[1], "TITULO_PROYECTO": "Obra en Pativilca"}]
    _, parche = con_respuestas([FalsaRespuesta(200, registros)])
    with parche:
        r = await senace.consultar(Locacion(departamento="Áncash", distrito="Pativilca"))
    por_id = {p.id: p for p in r.proyectos}
    assert por_id[7].fecha_inicio == date(2019, 3, 29)
    assert por_id[8].fecha_inicio is None
