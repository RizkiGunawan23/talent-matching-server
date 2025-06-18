from celery.result import AsyncResult
from django.utils import timezone
from neomodel import db
from rest_framework import status
from rest_framework.exceptions import APIException

from api.models import MatchingTask, ScrapingTask
from api.tasks import matching_job_after_scraping


def start_matching_scraped_job_data() -> None:
    """
    Memulai task scraping data pekerjaan di background.
    """
    # Cek apakah ada task yang sedang berjalan/selesai
    scraping_task: ScrapingTask | None = (
        ScrapingTask.nodes.filter(status__in=["FINISHED"])
        .order_by("-startedAt")
        .first_or_none()
    )

    if not scraping_task:
        raise APIException(
            detail="Belum ada task scraping yang selesai",
            code=status.HTTP_404_NOT_FOUND,
        )

    scraping_task_id: str = scraping_task.uid
    result = AsyncResult(scraping_task_id)

    task = matching_job_after_scraping.delay(jobs_data=result.result)

    db.begin()
    try:
        matching_task = MatchingTask(
            uid=task.id,
            status="RUNNING",
            startedAt=timezone.now(),
            finishedAt=None,
        )
        matching_task.save()
        scraping_task.has_process.connect(matching_task)
        db.commit()
    except Exception as e:
        db.rollback()
        raise APIException(
            detail=f"Error saat memulai matching job: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def scraping_task_status() -> dict[str, int | str | None]:
    """
    Mendapatkan status dari task matching yang sedang berjalan.
    """
    scraping_task: ScrapingTask | None = (
        ScrapingTask.nodes.filter(status__in=["FINISHED"])
        .order_by("-startedAt")
        .first_or_none()
    )

    if not scraping_task:
        raise APIException(
            detail="Tidak ada task scraping yang selesai",
            code=status.HTTP_404_NOT_FOUND,
        )

    matching_tasks = scraping_task.has_process.all()

    # Get the latest matching task that's RUNNING or FINISHED
    matching_task = None
    for task in matching_tasks:
        if task.status in ["RUNNING", "FINISHED"]:
            if not matching_task or task.startedAt > matching_task.startedAt:
                matching_task = task

    if not matching_task:
        raise APIException(
            detail="Tidak ada task matching yang sedang berjalan",
            code=status.HTTP_404_NOT_FOUND,
        )

    matching_uid = matching_task.uid

    result = AsyncResult(matching_uid)
    task_status: str = result.status

    if task_status == "FAILURE":
        raise APIException(
            detail="Task matching gagal",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return {
        "task_id": matching_uid,
        "status": task_status,
    }
