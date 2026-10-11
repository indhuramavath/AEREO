from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AEREO Geospatial File Measurement API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    DEBUG: bool = False

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Storage and File Limits
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: List[str] = [".kml", ".zip"]

    # Security: ZIP extraction limits
    MAX_ZIP_EXTRACTED_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB max uncompressed
    MAX_ZIP_FILE_COUNT: int = 50

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'aereo_geospatial.db'}"

    # Geospatial Processing
    DEFAULT_FALLBACK_CRS: str = "EPSG:4326"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
