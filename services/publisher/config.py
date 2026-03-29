from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://matrix:password@localhost:5432/ai_video_matrix"
    redis_url: str = "redis://redis:6379/0"
    rabbitmq_url: str = "amqp://matrix:password@rabbitmq:5672/"
    minio_endpoint: str = "http://minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket: str = "videos"
    proxy_pool_url: str = ""
    max_workers: int = 5
    publish_interval_seconds: int = 300
    content_router_url: str = "http://content-router:8000"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
