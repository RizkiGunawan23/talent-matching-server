from celery.result import AsyncResult
from django.core.cache import cache
from django.utils import timezone
from neomodel import db
from rest_framework import status
from rest_framework.exceptions import APIException

from api.models import ScrapingTask, User
from api.tasks import scrape_job_data


def start_scraping_task(user: User) -> None:
    """
    Memulai task scraping data pekerjaan di background.
    """
    # Cek apakah ada task yang sedang berjalan/selesai
    scraping_task = (
        ScrapingTask.nodes.filter(status__in=["RUNNING", "FINISHED"])
        .order_by("-startedAt")
        .first_or_none()
    )

    raise APIException(
        detail=f"Scraping sedang dalam status {scraping_task.status}, silakan tunggu hingga selesai atau cancel dahulu",
        code=status.HTTP_400_BAD_REQUEST,
    )
    if scraping_task:
        raise APIException(
            detail=f"Scraping sedang dalam status {scraping_task.status}, silakan tunggu hingga selesai atau cancel dahulu",
            code=status.HTTP_400_BAD_REQUEST,
        )

    # Mulai task celery
    task = scrape_job_data.delay()

    db.begin()
    try:
        scraping_task = ScrapingTask(
            uid=task.id,
            status="RUNNING",
            message="Scraping sedang berjalan",
            startedAt=timezone.now(),
        ).save()
        scraping_task.triggered_by.connect(user)
        db.commit()
    except Exception as e:
        db.rollback()


def cancel_scraping_task() -> None:
    """
    Membatalkan task scraping yang sedang berjalan.
    """
    scraping_task = (
        ScrapingTask.nodes.filter(status__in=["RUNNING", "FINISHED"])
        .order_by("-startedAt")
        .first_or_none()
    )

    if not scraping_task:
        raise APIException(
            detail="Tidak ada scraping yang bisa dibatalkan",
            code=status.HTTP_404_NOT_FOUND,
        )

    db.begin()
    try:
        scraping_task.status = "DUMPED"
        scraping_task.message = "Task dibatalkan oleh admin"
        scraping_task.save()
        db.commit()
    except Exception as e:
        db.rollback()
        raise APIException(
            detail=f"Terjadi kesalahan server, tidak bisa membatalkan scraping",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    cache.set(f"scraping_cancel_{scraping_task.uid}", True, timeout=600)
    cache.delete(f"scraping_progress_{scraping_task.uid}")
    result = AsyncResult(scraping_task.uid)
    result.forget()


def get_scraping_task_status(user: User) -> None:
    """
    Mendapatkan status dari task scraping yang sedang berjalan.
    """
    scraping_task: ScrapingTask | None = (
        ScrapingTask.nodes.filter(status__in=["RUNNING", "FINISHED"])
        .order_by("-startedAt")
        .first_or_none()
    )
    if not scraping_task:
        raise APIException(
            detail="Tidak ada task scraping terbaru yang sedang berjalan",
            code=status.HTTP_404_NOT_FOUND,
        )

    task_id: str = scraping_task.uid
    result: AsyncResult = AsyncResult(task_id)
    task_status: str = result.status

    progress_data: dict[str, int | None] = cache.get(f"scraping_progress_{task_id}", {})

    scraped_jobs: int = progress_data.get("scraped_jobs", 0)

    data = None

    if task_status == "SUCCESS":
        db.begin()
        try:
            scraping_task.status = "FINISHED"
            scraping_task.message = "Task selesai"
            if not scraping_task.finishedAt:
                scraping_task.finishedAt = timezone.now()
            scraping_task.save()
            db.commit()
        except Exception as e:
            db.rollback()
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        data = result.result
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = []

        # Handle Celery task failure
    elif task_status == "FAILURE":
        db.begin()
        try:
            scraping_task.status = "ERROR"
            error_message = (
                str(result.info) if result.info else "Unknown error occurred"
            )
            scraping_task.message = f"Task failed: {error_message}"
            if not scraping_task.finishedAt:
                scraping_task.finishedAt = timezone.now()
            scraping_task.save()
            db.commit()
        except Exception as e:
            db.rollback()
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    current_time = timezone.now()
    started_at = scraping_task.startedAt
    finished_at = scraping_task.finishedAt

    # Make sure both datetimes have the same timezone awareness
    if not is_aware(started_at):
        started_at = make_aware(started_at)

    if finished_at:
        if not is_aware(finished_at):
            finished_at = make_aware(finished_at)
        time_spent_seconds = (finished_at - started_at).total_seconds()
        print(f"masuk ke finished_at: {time_spent_seconds}")
    else:
        time_spent_seconds = (current_time - started_at).total_seconds()
        print(f"masuk ke not finished_at: {time_spent_seconds}")

    return Response(
        {
            "task_id": task_id,
            "status": task_status,
            "scraped_jobs": scraped_jobs or None,
            "started_at": scraping_task.startedAt.isoformat(),
            "time_spent": time_spent_seconds,
            "result": data or None,
        }
    )
