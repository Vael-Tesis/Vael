"""Configuración de la aplicación cargada desde variables de entorno (.env)."""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno de VAEL, validadas por Pydantic."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # Entorno
    environment: str = "development"
    debug: bool = True

    # PostgreSQL, un rol por uso (DEC-010). Nunca un superusuario: ignora la RLS.
    database_url: str  # vael_app: peticiones normales y procesos asíncronos
    database_system_url: str  # vael_system (BYPASSRLS): solo la lista cerrada de operaciones
    database_owner_url: str  # vael_owner: dueño de las tablas, solo para las migraciones
    # Administrador del servidor: solo lo usa app.scripts.crear_roles; la app nunca se conecta con él.
    database_admin_url: str | None = None

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15  # DEC-011
    refresh_token_expire_days: int = 7

    # Google Gemini
    gemini_api_key: str = ""
    # ID verificado contra la API en DEV-C-04 (gemini-3-flash no existe). Se fija una versión
    # concreta, no un alias como -latest, para que las mediciones del OE2 sean reproducibles.
    gemini_model: str = "gemini-3.8-flash"
    gemini_live_model: str = "gemini-2.5-flash-native-audio-preview-12-2025"

    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "vael-storage"
    # Solo en desarrollo: S3 local (Adobe S3Mock en docker-compose, DEC-023). Vacío = S3 de AWS.
    s3_endpoint_url: str | None = None
    ses_region: str = "us-east-1"

    # Correos
    email_from: str = "noreply@vael.ai"
    email_from_name: str = "VAEL"

    # SMTP local de desarrollo (no está en la sección 12 del CLAUDE.md; en producción se usa
    # SES vía aws_access_key_id/aws_secret_access_key, estos campos no aplican ahí).
    # Defaults pensados para un catcher local tipo Mailhog/aiosmtpd en localhost:1025.
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_password: str | None = None

    # Interno: también es el secreto HMAC con el que las Lambdas firman sus entregas al
    # backend (/api/interno, DEC-018). Vive en Secrets Manager.
    internal_service_key: str

    # Procesamiento asíncrono (DEC-016, HU-23). "en_proceso": desarrollo y tests, la tarea
    # corre en el mismo proceso. "sqs": producción, se publica en la cola del tipo y la
    # procesa la Lambda.
    despacho_modo: str = "en_proceso"
    sqs_url_analisis_cv: str = ""
    sqs_url_analisis_entrevista: str = ""
    # Solo la Lambda: URL base del backend (https://app.vael.work) para entregar sus resultados
    backend_url_interno: str = ""

    # Contraseñas de los usuarios semilla (app.scripts.semillas, doc 13). Nunca en el repositorio.
    # SEED_PASSWORD es la de respaldo para los roles que no tengan la suya.
    seed_password: str | None = None
    seed_password_admin: str | None = None
    seed_password_reclutador: str | None = None
    seed_password_evaluador: str | None = None
    seed_password_gerente: str | None = None

    # Frontend
    frontend_url: str = "http://localhost:5173"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Convierte ALLOWED_ORIGINS (string separado por comas) en una lista de origenes."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Indica si el entorno actual es de producción."""
        return self.environment.lower() == "production"

    @model_validator(mode="after")
    def _colas_en_modo_sqs(self) -> "Settings":
        """En modo sqs, cada tipo de tarea necesita su cola (DEC-016)."""
        if self.despacho_modo not in ("en_proceso", "sqs"):
            raise ValueError("DESPACHO_MODO debe ser 'en_proceso' o 'sqs'")
        if self.despacho_modo == "sqs" and not (self.sqs_url_analisis_cv and self.sqs_url_analisis_entrevista):
            raise ValueError("DESPACHO_MODO=sqs exige SQS_URL_ANALISIS_CV y SQS_URL_ANALISIS_ENTREVISTA")
        return self

    @model_validator(mode="after")
    def _sin_debug_en_produccion(self) -> "Settings":
        """Impide arrancar con DEBUG=true en producción (expondría /docs y detalles de errores)."""
        if self.is_production and self.debug:
            raise ValueError("DEBUG debe ser false cuando ENVIRONMENT=production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Retorna la instancia cacheada de Settings, leyendo el .env una sola vez."""
    return Settings()


settings: Settings = get_settings()
