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

    model_config = {"env_file": ".env"}


settings = Settings()
