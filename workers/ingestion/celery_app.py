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


@app.task(name="recruitment.ingestion.dispatch", ignore_result=True)
def dispatch():
    from recruitment_api.ingestion.runner import due_sources

    for source_id in due_sources():
        poll.apply_async(args=[str(source_id)], expires=180)


@app.task(
    bind=True,
    name="recruitment.ingestion.poll",
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=3,
    soft_time_limit=90,
    time_limit=105,
)
def poll(self, source_id: str):
    from uuid import UUID

    from recruitment_api.ingestion.runner import run_source
    from recruitment_api.ingestion.transport import FetchError

    try:
        return run_source(UUID(source_id))
    except FetchError as error:
        if error.retry and self.request.retries < self.max_retries and error.retry_after <= 3600:
            raise self.retry(countdown=error.retry_after + 1) from None
        return {"state": "failed", "code": error.code}


app.conf.beat_schedule = {
    "recruitment-ingestion-due": {
        "task": "recruitment.ingestion.dispatch",
        "schedule": 60.0,
        "options": {"expires": 55},
    }
}


@app.task(name="recruitment.ingestion.release_reviewed", soft_time_limit=45, time_limit=55)
def release_reviewed():
    from recruitment_api.ingestion.release import release_reviewed as release

    return release()


app.conf.beat_schedule["recruitment-ingestion-release"] = {
    "task": "recruitment.ingestion.release_reviewed",
    "schedule": 60.0,
    "options": {"expires": 55},
}
