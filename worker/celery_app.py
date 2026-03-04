import os
import sys

# Resolve the celery_worker/ directory from this file's location.
# This file lives at celery_worker/worker/celery_app.py, so two dirname
# calls get us to celery_worker/.
_celery_worker_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ensure_path() -> None:
    """Add celery_worker/ to sys.path if it isn't there yet."""
    if _celery_worker_dir not in sys.path:
        sys.path.insert(0, _celery_worker_dir)


# Run immediately in the main/parent process.
_ensure_path()

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

from core.config import settings


@worker_process_init.connect
def setup_worker_path(**kwargs):
    """Fired inside every forked/spawned worker process before tasks run."""
    _ensure_path()

celery_app = Celery(
    "learningpanda",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["worker.tasks"],
)

celery_app.conf.update(
    # Don't fetch the next task until the current long one finishes
    worker_prefetch_multiplier=1,
    # Acknowledge only after completion so crashed workers requeue the task
    task_acks_late=True,
    # Expose the STARTED state so /status can show "processing"
    task_track_started=True,
    # Keep task results in Redis for 24 hours
    result_expires=86400,
    # Use JSON for cross-language compatibility
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # ── Periodic tasks (Celery Beat) ──────────────────────────────────────────
    beat_schedule={
        "purge-expired-otp-tokens": {
            "task": "purge_expired_otp_tokens",
            # Run once a day at 03:00 UTC
            "schedule": crontab(hour=3, minute=0),
        },
    },
)
