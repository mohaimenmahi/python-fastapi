from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
  model_config = SettingsConfigDict(
    env_file=".env", env_file_encoding="utf-8", extra="ignore"
  )

  app_name: str = "python-fastapi"
  debug: bool = False
  environment: str = "development"

  database_url: str
  test_database_url: str

  jwt_secret_key: str
  jwt_algorithm: str = "HS256"
  access_token_expire_minutes: int = 15
  refresh_token_expire_days: int = 7
  cookie_secure: bool = False


settings = Settings()
