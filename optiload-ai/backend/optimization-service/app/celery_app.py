from celery import Celery
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://optiload:optiload_secret@localhost:5432/optiload_db"
    redis_url: str = "redis://localhost:6379/3"
    rabbitmq_url: str = "amqp://optiload:optiload_rabbit@localhost:5672/"
    alpha: float = 0.3   # distance weight
    beta: float = 0.2    # empty capacity weight
    gamma: float = 0.2   # trips weight
    delta: float = 0.2   # carbon weight
    epsilon: float = 0.1 # delay penalty weight
    emission_factor: float = 2.68  # kg CO2 per liter diesel

    class Config:
        env_file = ".env"

settings = Settings()
celery_app = Celery("optimization", broker=settings.rabbitmq_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)