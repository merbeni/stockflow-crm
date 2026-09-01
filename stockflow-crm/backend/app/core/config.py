from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    GOOGLE_API_KEY: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # SendGrid — optional; emails are silently skipped if not set
    SENDGRID_API_KEY: str = ""
    SMTP_FROM_EMAIL: str = ""

    # Orígenes permitidos por CORS, separados por coma.
    # Usar "*" solo en desarrollo: es incompatible con allow_credentials.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # URL pública del frontend, usada para armar el enlace de verificación de correo.
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = {"env_file": ".env"}


settings = Settings()
