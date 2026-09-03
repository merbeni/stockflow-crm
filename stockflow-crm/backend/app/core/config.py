from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    GOOGLE_API_KEY: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # SMTP — sirve cualquier proveedor (Brevo, Gmail, Mailjet…). Si no está
    # configurado, los correos se omiten en silencio (útil en desarrollo).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "StockFlow CRM"

    # Orígenes permitidos por CORS, separados por coma.
    # Usar "*" solo en desarrollo: es incompatible con allow_credentials.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # URL pública del frontend, usada para armar el enlace de verificación de correo.
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def email_enabled(self) -> bool:
        """El envío de correos requiere host, usuario y contraseña SMTP."""
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD)

    model_config = {"env_file": ".env"}


settings = Settings()
