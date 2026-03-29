from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://matrix:password@localhost:5432/ai_video_matrix"
    redis_url: str = "redis://redis:6379/0"
    rabbitmq_url: str = "amqp://matrix:password@rabbitmq:5672/"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
