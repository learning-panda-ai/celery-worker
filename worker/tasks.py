import logging
from datetime import datetime, timedelta, timezone

from worker.celery_app import celery_app
from services.milvus import IngestError, ingest_pdf

logger = logging.getLogger(__name__)


# ── Periodic maintenance ───────────────────────────────────────────────────────


@celery_app.task(name="purge_expired_otp_tokens")
def purge_expired_otp_tokens() -> dict:
    """
    Delete OTP token rows that expired more than 24 hours ago.

    Run via Celery Beat (see beat_schedule in celery_app.py).
    Prevents the otp_tokens table from growing unboundedly, which would
    degrade the DB-backed rate-limit query performance over time.
    """
    import sqlalchemy
    from core.config import settings

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    engine = sqlalchemy.create_engine(
        settings.DATABASE_URL.replace("+asyncpg", ""),
        pool_pre_ping=True,
    )
    with engine.begin() as conn:
        result = conn.execute(
            sqlalchemy.text(
                "DELETE FROM otp_tokens WHERE expires_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
        deleted = result.rowcount

    logger.info("purge_expired_otp_tokens: deleted %d rows", deleted)
    return {"deleted": deleted}


# ── Content ingestion ──────────────────────────────────────────────────────────


@celery_app.task(bind=True, name="ingest_pdf_task")
def ingest_pdf_task(self, url: str, replace: bool = False) -> dict:
    """
    Celery task that runs the full PDF ingestion pipeline.

    Delegates to ``ingest_pdf`` from services/milvus.py.
    Any exception raised inside that service is caught and re-raised as a
    plain Exception so Celery can serialise the failure cleanly.
    """

    try:
        result = ingest_pdf(url, replace)
    except IngestError as exc:
        raise Exception(str(exc)) from exc

    return {
        "collection": result.collection,
        "board": result.board,
        "state": result.state,
        "standard": result.standard,
        "subject": result.subject,
        "chunks_inserted": result.chunks_inserted,
        "source_url": result.source_url,
    }
