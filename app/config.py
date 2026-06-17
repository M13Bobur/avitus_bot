from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    bot_token: str
    database_url: str
    log_level: str = "INFO"
    max_upload_size_mb: int = 20
    low_stock_threshold: int = 20
    supplier_registration_password: str = "pharm2024"
    admin_registration_password: str = "admin2024"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()
