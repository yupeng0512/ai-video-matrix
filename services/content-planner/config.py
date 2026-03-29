from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://matrix:password@localhost:5432/ai_video_matrix"
    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    openai_api_key: str = ""

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
