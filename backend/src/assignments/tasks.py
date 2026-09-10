from celery import shared_task
from .services import close_overdue_attempts


@shared_task(name="assignments.close_overdue_attempts")
def close_overdue_attempts_task():
    return close_overdue_attempts()
