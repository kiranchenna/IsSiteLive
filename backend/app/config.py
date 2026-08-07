from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./data/issitelive.db"
    encryption_key: str  # generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    screenshots_dir: str = "./data/screenshots"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "alerts@issitelive.local"
    smtp_use_tls: bool = False

    default_check_concurrency: int = 3
    default_step_timeout_ms: int = 15000


settings = Settings()
