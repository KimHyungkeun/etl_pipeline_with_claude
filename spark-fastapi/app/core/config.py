from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "Spark Cluster API"
    debug: bool = False

    spark_master_url: str = "http://localhost:8080"
    spark_submit_master: str = "spark://localhost:7077"
    spark_home: str = f"{Path.home()}/spark"

    class Config:
        env_file = ".env"


settings = Settings()