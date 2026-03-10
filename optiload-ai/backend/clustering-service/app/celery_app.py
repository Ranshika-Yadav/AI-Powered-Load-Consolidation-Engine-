from celery import Celery
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://optiload:optiload_secret@localhost:5432/optiload_db"
    redis_url: str = "redis://localhost:6379/2"
    rabbitmq_url: str = "amqp://optiload:optiload_rabbit@localhost:5672/"

    class Config:
        env_file = ".env"

settings = Settings()
celery_app = Celery("clustering", broker=settings.rabbitmq_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)