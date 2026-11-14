"""Adaptador SENAMHI. Spec: specs/01-adaptador-senamhi.md (Integrante 1).



Consulta datos meteorológicos históricos de SENAMHI.
No proporciona pronósticos.
"""

from datetime import date
import asyncio
import logging
import hashlib
import time
from io import BytesIO

import pandas as pd
import unicodedata

import httpx
from math import atan2, cos, radians, sin, sqrt

from jeils.cache import get_cache
from jeils.config import get_settings
from jeils.contracts import (
    ClimaHistorico,
    Estacion,
    FuenteNoDisponible,
    Locacion,
    ResultadoSenamhi,
)


def calcular_distancia_km(
    latitud_1: float,
    longitud_1: float,
    latitud_2: float,
    longitud_2: float,
) -> float:
    """Calcula la distancia entre dos coordenadas usando Haversine."""

    radio_tierra = 6371.0

    diferencia_latitud = radians(latitud_2 - latitud_1)
    diferencia_longitud = radians(longitud_2 - longitud_1)

    a = (
        sin(diferencia_latitud / 2) ** 2
        + cos(radians(latitud_1))
        * cos(radians(latitud_2))
        * sin(diferencia_longitud / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return radio_tierra * c



async def obtener_metadatos_senamhi() -> dict:
    """Consulta los metadatos del conjunto de datos SENAMHI."""

    configuracion = get_settings()
    intentos = configuracion.http_max_retries + 1

    async with httpx.AsyncClient(
        timeout=configuracion.http_timeout_seconds
    ) as cliente:
        for intento in range(intentos):
            try:
                respuesta = await cliente.get(
                    configuracion.senamhi_package_url
                )
                respuesta.raise_for_status()

                datos = respuesta.json()

                if not datos.get("success"):
                    raise ValueError(
                        "CKAN no devolvió una respuesta exitosa"
                    )

                resultado = datos["result"]

                # CKAN puede devolver un diccionario
                # o una lista de conjuntos de datos.
                if isinstance(resultado, list):
                    resultado = next(
                        (
                            elemento
                            for elemento in resultado
                            if isinstance(elemento, dict)
                            and "resources" in elemento
                        ),
                        None,
                    )

                if not isinstance(resultado, dict):
                    raise ValueError(
                        "CKAN no devolvió metadatos válidos"
                    )

                return resultado


            except (
                httpx.TimeoutException,
                httpx.RequestError,
                httpx.HTTPStatusError,
            ) as error:
                logging.warning(
                    "Error consultando SENAMHI, intento %s: %s",
                    intento + 1,
                    error,
                )

                if intento == intentos - 1:
                    raise FuenteNoDisponible(
                        "SENAMHI",
                        str(error),
                    ) from error

                await asyncio.sleep(0.5 * (2 ** intento))

    raise FuenteNoDisponible("SENAMHI")


def obtener_url_csv(metadatos: dict) -> str:
    """Identifica el recurso CSV de SENAMHI."""

    recursos = metadatos.get("resources", [])

    for recurso in recursos:
        formato = str(
            recurso.get("format", "")
        ).strip().lower()

        url = recurso.get("url", "")

        if formato == "csv" and url:
            return url

    raise ValueError(
        "No se encontró un recurso CSV en SENAMHI"
    )



async def descargar_csv_senamhi(url_csv: str) -> bytes:
    """Descarga el archivo CSV histórico de SENAMHI."""

    configuracion = get_settings()
    max_intentos = configuracion.http_max_retries + 1

    async with httpx.AsyncClient(
        timeout=configuracion.http_timeout_seconds,
        follow_redirects=True,
    ) as cliente:

        for intento in range(max_intentos):
            try:
                respuesta = await cliente.get(url_csv)
                respuesta.raise_for_status()

                # Se acepta CSV aunque el servidor lo entregue
                # como application/octet-stream.
                return respuesta.content

            except (
                httpx.TimeoutException,
                httpx.RequestError,
                httpx.HTTPStatusError,
            ) as error:

                logging.warning(
                    "Error descargando CSV SENAMHI. Intento %s/%s: %s",
                    intento + 1,
                    max_intentos,
                    error,
                )

                if intento == max_intentos - 1:
                    raise FuenteNoDisponible(
                        "SENAMHI",
                        str(error),
                    ) from error

                await asyncio.sleep(0.5 * (2 ** intento))

    raise FuenteNoDisponible("SENAMHI")


def procesar_csv_senamhi(contenido_csv: bytes) -> pd.DataFrame:
    """Convierte el CSV de SENAMHI en datos meteorológicos utilizables."""

    if not contenido_csv:
        raise ValueError("El CSV de SENAMHI está vacío")

    # Identificar si las columnas están separadas por ; o ,
    encabezado = contenido_csv[:4096].decode(
        "utf-8-sig", errors="replace"
    ).splitlines()[0]

    separador = (
        ";" if encabezado.count(";") > encabezado.count(",")
        else ","
    )

    # Leer el archivo sin importar si usa UTF-8 o Latin-1.
    try:
        datos = pd.read_csv(
            BytesIO(contenido_csv),
            sep=separador,
            encoding="utf-8-sig",
            dtype={"UBIGEO": "string"},
            low_memory=False,
        )
    except UnicodeDecodeError:
        datos = pd.read_csv(
            BytesIO(contenido_csv),
            sep=separador,
            encoding="latin-1",
            dtype={"UBIGEO": "string"},
            low_memory=False,
        )

    # Normalizar los nombres de las columnas.
    datos.columns = datos.columns.str.strip().str.upper()

    columnas_obligatorias = {
        "ESTACION", "FECHA", "LATITUD",
        "LONGITUD", "TEMP", "HR", "PP",
    }

    faltantes = columnas_obligatorias - set(datos.columns)

    if faltantes:
        raise ValueError(
            f"Faltan columnas en el CSV: {sorted(faltantes)}"
        )

    # Convertir fechas, descartando formatos inválidos.
    
    # Convertir las fechas a texto para evitar que pandas
    # interprete 20150101 como un número de nanosegundos.
    fechas = datos["FECHA"].astype("string").str.strip()

    # SENAMHI utiliza fechas como 20150101 (AAAAMMDD).
    formato_senamhi = fechas.str.fullmatch(
        r"\d{8}"
    ).fillna(False)

    fechas_senamhi = pd.to_datetime(
        fechas.where(formato_senamhi),
        format="%Y%m%d",
        errors="coerce",
    )

    # Mantener compatibilidad con fechas como 01/11/2024.
    fechas_otros_formatos = pd.to_datetime(
        fechas.where(~formato_senamhi),
        format="mixed",
        dayfirst=True,
        errors="coerce",
    )

    datos["FECHA"] = fechas_senamhi.combine_first(
        fechas_otros_formatos
    )


    # Convertir valores numéricos.
    columnas_numericas = [
        "LATITUD", "LONGITUD",
        "ALTITUD", "TEMP", "HR", "PP",
    ]

    for columna in columnas_numericas:
        if columna in datos.columns:
            valores = (
                datos[columna]
                .astype("string")
                .str.strip()
                .str.replace(",", ".", regex=False)
            )

            datos[columna] = pd.to_numeric(
                valores,
                errors="coerce",
            )

    # Eliminar registros sin fecha o ubicación válida.
    datos = datos.dropna(
        subset=["FECHA", "ESTACION", "LATITUD", "LONGITUD"]
    )

    # Eliminar registros sin ninguna medición meteorológica.
    datos = datos.dropna(
        subset=["TEMP", "HR", "PP"],
        how="all",
    )

    return datos



def calcular_promedios_historicos(
    datos: pd.DataFrame,
    fecha_evento: date,
) -> ClimaHistorico | None:
    """Calcula promedios del mismo mes de años anteriores.

    Los datos recibidos deben corresponder a una estación.
    """

    if datos.empty:
        return None

    # Seleccionar el mismo mes del evento en años anteriores.
    periodo = datos[
        (datos["FECHA"].dt.month == fecha_evento.month)
        & (datos["FECHA"].dt.year < fecha_evento.year)
    ]

    if periodo.empty:
        return None

    # Calcular promedios ignorando valores faltantes.
    def promedio(columna: str) -> float | None:
        valor = periodo[columna].mean()

        if pd.isna(valor):
            return None

        return round(float(valor), 2)

    meses = [
        "enero", "febrero", "marzo", "abril",
        "mayo", "junio", "julio", "agosto",
        "septiembre", "octubre", "noviembre", "diciembre",
    ]

    mes = meses[fecha_evento.month - 1]
    anio_inicio = int(periodo["FECHA"].dt.year.min())
    anio_fin = int(periodo["FECHA"].dt.year.max())

    periodo_referencia = (
        f"{mes}, {anio_inicio}-{anio_fin}"
    )

    return ClimaHistorico(
        temperatura_promedio_c=promedio("TEMP"),
        humedad_promedio_pct=promedio("HR"),
        precipitacion_promedio_mm=promedio("PP"),
        n_registros=len(periodo),
        periodo_referencia=periodo_referencia,
    )



def normalizar_texto(valor) -> str:
    """Normaliza textos para comparar localidades."""

    if pd.isna(valor):
        return ""

    texto = unicodedata.normalize(
        "NFKD", str(valor).strip().casefold()
    )

    return "".join(
        letra for letra in texto
        if not unicodedata.combining(letra)
    )


def seleccionar_estacion(
    datos: pd.DataFrame,
    locacion: Locacion,
) -> tuple[Estacion | None, pd.DataFrame]:
    """Selecciona una estación y sus registros históricos."""

    vacio = datos.iloc[0:0].copy()

    if datos.empty:
        return None, vacio

    claves = ["ESTACION", "LATITUD", "LONGITUD"]

    estaciones = datos.drop_duplicates(
        subset=claves
    ).copy()

    # Excluir coordenadas inválidas.
    estaciones = estaciones[
        estaciones["LATITUD"].between(-90, 90)
        & estaciones["LONGITUD"].between(-180, 180)
    ]

    if estaciones.empty:
        return None, vacio

    tiene_coordenadas = (
        locacion.latitud is not None
        and locacion.longitud is not None
    )

    distancia = None

    if tiene_coordenadas:
        # Seleccionar la estación con menor distancia.
        distancias = estaciones.apply(
            lambda fila: calcular_distancia_km(
                locacion.latitud,
                locacion.longitud,
                fila["LATITUD"],
                fila["LONGITUD"],
            ),
            axis=1,
        )

        indice = distancias.idxmin()
        elegida = estaciones.loc[indice]
        distancia = round(float(distancias.loc[indice]), 2)

    else:
        # Cuando no hay coordenadas, buscar por ubicación.
        if locacion.ubigeo:
            filtros = [("UBIGEO", locacion.ubigeo)]
        else:
            filtros = [
                ("DEPARTAMENTO", locacion.departamento),
                ("PROVINCIA", locacion.provincia),
                ("DISTRITO", locacion.distrito),
            ]

        for columna, valor in filtros:
            if valor is None:
                continue

            if columna not in estaciones.columns:
                return None, vacio

            estaciones = estaciones[
                estaciones[columna].map(normalizar_texto)
                == normalizar_texto(valor)
            ]

        if estaciones.empty:
            return None, vacio

        # Selección administrativa; sin distancia calculable.
        elegida = estaciones.iloc[0]

    # Obtener únicamente los registros de la estación.
    mascara = (
        (datos["ESTACION"] == elegida["ESTACION"])
        & (datos["LATITUD"] == elegida["LATITUD"])
        & (datos["LONGITUD"] == elegida["LONGITUD"])
    )

    registros = datos.loc[mascara].copy()

    altitud = elegida.get("ALTITUD")

    estacion = Estacion(
        nombre=str(elegida["ESTACION"]),
        latitud=float(elegida["LATITUD"]),
        longitud=float(elegida["LONGITUD"]),
        altitud=(
            float(altitud)
            if altitud is not None and pd.notna(altitud)
            else None
        ),
        distancia_km=distancia,
    )

    return estacion, registros



# Caché del CSV procesado durante la ejecución del servidor.
_datos_senamhi = None
_momento_datos_senamhi = 0.0
_candado_senamhi = asyncio.Lock()


async def cargar_datos_senamhi():
    """Carga el CSV evitando descargarlo en cada consulta."""
    global _datos_senamhi, _momento_datos_senamhi

    configuracion = get_settings()

    def datos_vigentes():
        return (
            _datos_senamhi is not None
            and time.monotonic() - _momento_datos_senamhi
            < configuracion.cache_ttl_seconds
        )

    if datos_vigentes():
        return _datos_senamhi, False

    async with _candado_senamhi:
        if datos_vigentes():
            return _datos_senamhi, False

        try:
            metadatos = await obtener_metadatos_senamhi()
            url_csv = obtener_url_csv(metadatos)
            contenido = await descargar_csv_senamhi(url_csv)

            datos = await asyncio.to_thread(
                procesar_csv_senamhi,
                contenido,
            )

        except (
            FuenteNoDisponible,
            ValueError,
            TypeError,
            KeyError,
            pd.errors.ParserError,
        ) as error:
            if _datos_senamhi is not None:
                logging.warning(
                    "Se usa una copia anterior de SENAMHI: %s",
                    error,
                )
                return _datos_senamhi, True

            if isinstance(error, FuenteNoDisponible):
                raise

            raise FuenteNoDisponible(
                "SENAMHI", str(error)
            ) from error

        _datos_senamhi = datos
        _momento_datos_senamhi = time.monotonic()

        return datos, False





async def consultar(
    locacion: Locacion,
    fecha_evento: date,
) -> ResultadoSenamhi:
    """Consulta el clima histórico de SENAMHI."""

    configuracion = get_settings()
    cache = get_cache()

    # Crear una clave única por ubicación y periodo.
    identificador = (
        locacion.model_dump_json(exclude_none=True)
        + f"|{fecha_evento.year}-{fecha_evento.month:02d}"
    )

    clave = (
        "senamhi:resultado:"
        + hashlib.sha256(
            identificador.encode("utf-8")
        ).hexdigest()
    )

    # RF-2: revisar primero la caché.
    guardado = await cache.get(clave)

    if guardado is not None:
        return ResultadoSenamhi.model_validate(guardado)

    try:
        # Obtener los datos históricos.
        datos, copia_anterior = await cargar_datos_senamhi()

    except FuenteNoDisponible:
        # RF-7: usar caché vencida si SENAMHI falla.
        respaldo = await cache.get_stale(clave)

        if respaldo is not None:
            resultado = ResultadoSenamhi.model_validate(
                respaldo
            )
            resultado.avisos.append(
                "SENAMHI no está disponible. "
                "Se utiliza información anterior."
            )
            return resultado

        raise

    # Seleccionar estación meteorológica.
    estacion, registros = seleccionar_estacion(
        datos, locacion
    )

    avisos = []

    if copia_anterior:
        avisos.append(
            "Se utilizan datos históricos de una "
            "copia anterior de SENAMHI."
        )

    if estacion is None:
        # RF-6: no hay estación disponible.
        clima = None
        avisos.append(
            "No se encontraron estaciones meteorológicas "
            "para la ubicación solicitada."
        )

    else:
        # RF-1 y RF-4: calcular promedios históricos.
        clima = calcular_promedios_historicos(
            registros,
            fecha_evento,
        )

        if clima is None:
            avisos.append(
                "No existen registros históricos del "
                "mismo mes de años anteriores."
            )

        # RF-5: comprobar la distancia.
        if (
            estacion.distancia_km is not None
            and estacion.distancia_km
            > configuracion.max_station_distance_km
        ):
            avisos.append(
                "Cobertura limitada: la estación "
                f"está a {estacion.distancia_km:.2f} km."
            )

        if estacion.distancia_km is None:
            avisos.append(
                "Estación elegida por coincidencia "
                "administrativa. Distancia no calculable."
            )

    resultado = ResultadoSenamhi(
        estacion=estacion,
        clima=clima,
        avisos=avisos,
    )

    # Guardar resultado en caché.
    await cache.set(
        clave,
        resultado.model_dump(mode="json"),
    )

    return resultado


    
