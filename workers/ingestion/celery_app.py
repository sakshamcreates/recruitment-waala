import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv(".env")

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
if not broker_url.startswith(("redis://", "rediss://")):
    raise RuntimeError("CELERY_BROKER_URL must use redis or rediss.")

app = Celery("recruitment_ingestion", broker=broker_url)
app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    task_ignore_result=True,
    task_default_queue="ingestion",
    broker_connection_retry_on_startup=True,
)
