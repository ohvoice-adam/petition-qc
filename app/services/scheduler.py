"""APScheduler integration for scheduled database backups."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="UTC")
_JOB_ID = "scheduled_backup"


def init_app(app) -> None:
    """Start the scheduler and apply the current backup schedule."""
    if not _scheduler.running:
        _scheduler.start()
    apply_schedule(app)


def apply_schedule(app) -> None:
    """Update the scheduled backup job to match the current settings."""
    with app.app_context():
        from app.models import Settings
        schedule = Settings.get("backup_schedule", "")

    if _scheduler.get_job(_JOB_ID):
        _scheduler.remove_job(_JOB_ID)

    trigger = _make_trigger(schedule)
    if trigger:
        _scheduler.add_job(
            _run_scheduled_backup,
            trigger=trigger,
            id=_JOB_ID,
            args=[app],
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info("Backup scheduled: %s", schedule)
    else:
        logger.info("Backup schedule disabled.")


def _make_trigger(schedule: str):
    if schedule == "hourly":
        return CronTrigger(minute=0)
    elif schedule == "daily":
        return CronTrigger(hour=2, minute=0)
    elif schedule == "weekly":
        return CronTrigger(day_of_week="sun", hour=2, minute=0)
    return None


def _run_scheduled_backup(app) -> None:
    from app.services.backup import run_backup_sync
    try:
        run_backup_sync(app)
    except Exception:
        logger.exception("Scheduled backup failed")
