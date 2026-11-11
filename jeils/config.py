from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    senace_api_key: str = ""
    senace_url: str = "https://datosabiertos.senace.gob.pe/Api/datastreams/CarteraProyectos"
    senamhi_package_url: str = (
        "https://www.datosabiertos.gob.pe/api/3/action/package_show"
        "?id=b884a001-f444-4c87-91b2-bee1891e6eb7"
    )
    redis_url: str = ""
    http_timeout_seconds: float = 3.5
    http_max_retries: int = 2
    cache_ttl_seconds: int = 3600
    max_station_distance_km: float = 100.0
    cors_origins: list[str] = ["*"]  # TODO(equipo): restringir en producción


@lru_cache
def get_settings() -> Settings:
    return Settings()
