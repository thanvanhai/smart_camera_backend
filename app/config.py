from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application Configuration
    app_name: str = Field("Smart Camera Backend", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    debug: bool = Field(False, env="DEBUG")
    environment: str = Field("development", env="ENVIRONMENT")
    
    # API Configuration
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_prefix: str = Field("/api/v1", env="API_PREFIX")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    algorithm: str = Field("HS256", env="ALGORITHM")
    
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    database_echo: bool = Field(False, env="DATABASE_ECHO")
    database_pool_size: int = Field(5, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(10, env="DATABASE_MAX_OVERFLOW")
    
    # Redis Configuration
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    redis_db: int = Field(0, env="REDIS_DB")
    
    # RabbitMQ Configuration
    rabbitmq_url: str = Field("amqp://guest:guest@localhost:5672/", env="RABBITMQ_URL")
    rabbitmq_queue_detections: str = Field("ros2_detections", env="RABBITMQ_QUEUE_DETECTIONS")
    rabbitmq_queue_tracking: str = Field("ros2_tracking", env="RABBITMQ_QUEUE_TRACKING")
    rabbitmq_queue_faces: str = Field("ros2_faces", env="RABBITMQ_QUEUE_FACES")
    rabbitmq_exchange: str = Field("ros2_exchange", env="RABBITMQ_EXCHANGE")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8080"], 
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(
        ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], 
        env="CORS_ALLOW_METHODS"
    )
    cors_allow_headers: List[str] = Field(["*"], env="CORS_ALLOW_HEADERS")
    
    # File Storage
    upload_dir: str = Field("./uploads", env="UPLOAD_DIR")
    max_file_size: int = Field(10485760, env="MAX_FILE_SIZE")  # 10MB
    
    # Analytics Configuration
    data_retention_days: int = Field(90, env="DATA_RETENTION_DAYS")
    cleanup_interval_hours: int = Field(24, env="CLEANUP_INTERVAL_HOURS")
    stats_calculation_interval_minutes: int = Field(60, env="STATS_CALCULATION_INTERVAL_MINUTES")
    
    # WebSocket Configuration
    ws_max_connections: int = Field(100, env="WS_MAX_CONNECTIONS")
    ws_heartbeat_interval: int = Field(30, env="WS_HEARTBEAT_INTERVAL")
    
    # Monitoring
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    metrics_port: int = Field(8001, env="METRICS_PORT")
    
    # Email Configuration
    smtp_host: Optional[str] = Field(None, env="SMTP_HOST")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_user: Optional[str] = Field(None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(None, env="SMTP_PASSWORD")
    smtp_from_email: str = Field("noreply@smartcamera.com", env="SMTP_FROM_EMAIL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency to get settings instance."""
    return settings