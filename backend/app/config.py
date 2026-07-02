from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://medextract:medextract@localhost:5433/medextract"
    cors_origins: str = "http://localhost:3000,http://localhost:3100"
    ml_dir: str = ""  # path to the repo's ml/ directory; empty = auto-detect

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
