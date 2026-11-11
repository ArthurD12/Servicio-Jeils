"""Contratos de datos compartidos entre módulos (DTOs).

IMPORTANTE: no cambiar sin acuerdo del equipo (Pull Request revisado por todos).
"""
from datetime import date, datetime, timezone

from pydantic import BaseModel, Field, model_validator


class FuenteNoDisponible(Exception):
    """Una fuente externa no respondió y no hay copia en caché."""

    def __init__(self, fuente: str, detalle: str = ""):
        self.fuente = fuente
        super().__init__(f"{fuente} no disponible. {detalle}".strip())


# ---------- Entrada ----------
class Locacion(BaseModel):
    ubigeo: str | None = None
    departamento: str | None = None
    provincia: str | None = None
    distrito: str | None = None
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def _requiere_alguna_referencia(self):
        tiene_coords = self.latitud is not None and self.longitud is not None
        if not (self.ubigeo or self.departamento or tiene_coords):
            raise ValueError("Indique ubigeo, departamento/provincia/distrito o coordenadas")
        return self


class EvaluacionRequest(BaseModel):
    locacion: Locacion
    fecha_evento: date


# ---------- SENAMHI ----------
class Estacion(BaseModel):
    nombre: str
    latitud: float
    longitud: float
    altitud: float | None = None
    distancia_km: float | None = None


class ClimaHistorico(BaseModel):
    temperatura_promedio_c: float | None = None
    humedad_promedio_pct: float | None = None
    precipitacion_promedio_mm: float | None = None
    n_registros: int = 0
    periodo_referencia: str | None = None  # ej. "noviembre, 2019-2025"


class ResultadoSenamhi(BaseModel):
    estacion: Estacion | None = None
    clima: ClimaHistorico | None = None
    avisos: list[str] = []


# ---------- SENACE ----------
class ProyectoAmbiental(BaseModel):
    id: int
    titular: str | None = None
    ruc: str | None = None
    titulo_proyecto: str | None = None
    unidad_proyecto: str | None = None
    tipo: str | None = None
    actividad: str | None = None
    fecha_inicio: date | None = None
    estado: str | None = None


class ResultadoSenace(BaseModel):
    proyectos: list[ProyectoAmbiental] = []
    total: int = 0
    avisos: list[str] = []


# ---------- Salida unificada ----------
class EvaluacionResponse(BaseModel):
    senamhi: ResultadoSenamhi | None = None
    senace: ResultadoSenace | None = None
    advertencias: list[str] = []
    es_pronostico: bool = False  # siempre False: son datos históricos
    generado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
