"""Create one unpublished, explicitly marked sample in a dedicated development database."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import database_url, engine
from .models import Details, Job, Organisation, Publication
from .settings import setting


def main():
    url = database_url()
    if setting("RW_ENV") != "development" or not (url.database or "").endswith("_demo"):
        raise SystemExit("Use RW_ENV=development and a dedicated database ending in _demo.")
    with Session(engine()) as db, db.begin():
        if db.scalar(select(Organisation.id).where(Organisation.slug == "demo-editorial")):
            return
        org = Organisation(name="Demo Editorial Board (fictional)", slug="demo-editorial")
        db.add(org)
        db.flush()
        job = Job(
            organisation_id=org.id,
            title="Illustrative recruitment notice",
            cycle_key="demo",
            opportunity_key="editorial",
            category="government_job",
        )
        db.add(job)
        db.flush()
        db.add_all(
            [
                Details(job_id=job.id, description="Fictional draft for local testing."),
                Publication(job_id=job.id, is_demo=True),
            ]
        )


if __name__ == "__main__":
    main()
