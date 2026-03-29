from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://matrix:password@localhost:5432/ai_video_matrix"
    minio_endpoint: str = "http://minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket: str = "videos"
    similarity_threshold: float = 0.70

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
