from celery import shared_task
from celery.result import AsyncResult
from django.core.cache import cache
from django.utils import timezone
from neomodel import db

from api.models import Maintenance, MatchingTask, ScrapingTask
from api.services.admin.scrapers.scraper_services import scrape_all_websites
from api.services.matchers.matchers_services import matching_after_scraping


@shared_task(bind=True)
def scrape_job_data(self):
    """Task Celery untuk scraping data"""
    task_id = self.request.id

    try:
        result = scrape_all_websites(task_id, self.update_state)
        scraping_task: ScrapingTask | None = (
            ScrapingTask.nodes.filter(status__in=["RUNNING"])
            .order_by("-startedAt")
            .first_or_none()
        )
        db.begin()
        try:
            scraping_task.status = "FINISHED"
            scraping_task.message = "Task selesai"
            if not scraping_task.finishedAt:
                scraping_task.finishedAt = timezone.now()
            scraping_task.save()
            db.commit()
        except Exception:
            db.rollback()
        return result
    except Exception as e:
        # Update scraping task status to ERROR when exception occurs
        try:
            scraping_task = (
                ScrapingTask.nodes.filter(uid=task_id, status__in=["RUNNING"])
                .order_by("-startedAt")
                .first_or_none()
            )
            if scraping_task:
                db.begin()
                try:
                    scraping_task.status = "ERROR"
                    scraping_task.message = "Scraping task failed due to an error"
                    scraping_task.save()
                    db.commit()
                except Exception:
                    db.rollback()

            cache.set(f"scraping_cancel_{scraping_task.uid}", True, timeout=600)
            cache.delete(f"scraping_progress_{scraping_task.uid}")
        except Exception:
            pass

        # Re-raise the exception so Celery marks the task as FAILURE
        raise e


@shared_task(bind=True)
def matching_job_after_scraping(self, jobs_data=[]):
    """Task Celery untuk melakukan matching job setelah scraping selesai"""
    task_id = self.request.id

    try:
        print(f"[MATCHING_INFO] Starting matching process for task {task_id}")

        # Execute matching process
        matching_after_scraping(task_id, self.update_state, jobs_data)

        # Disable maintenance mode
        Maintenance.set_maintenance(False)
        print(f"[MATCHING_INFO] Maintenance mode disabled")

        # Find matching task using ORM
        matching_task = MatchingTask.nodes.get_or_none(uid=task_id)

        if not matching_task:
            print(f"[MATCHING_ERROR] MatchingTask {task_id} not found")
            return

        # PERBAIKAN: Find related scraping task using ORM relationship
        scraping_task = None
        try:
            # Get all scraping tasks and check which one has this matching task
            scraping_tasks = (
                ScrapingTask.nodes.all()
            )  # PERBAIKAN: Gunakan ScrapingTask.nodes.all()
            for st in scraping_tasks:
                connected_matching_tasks = st.has_process.all()  # Ini benar
                for mt in connected_matching_tasks:
                    if mt.uid == task_id:
                        scraping_task = st
                        break
                if scraping_task:
                    break
        except Exception as e:
            print(f"[MATCHING_WARNING] Could not find related scraping task: {str(e)}")

        # Update task statuses using ORM
        db.begin()
        try:
            print(f"[MATCHING_INFO] Updating task statuses to IMPORTED")

            # Update MatchingTask
            matching_task.status = "IMPORTED"
            matching_task.finishedAt = timezone.now()
            matching_task.save()
            print(f"[MATCHING_SUCCESS] MatchingTask {task_id} updated to IMPORTED")

            # Update ScrapingTask if found
            if scraping_task:
                scraping_task.status = "IMPORTED"
                scraping_task.finishedAt = timezone.now()
                scraping_task.save()
                print(
                    f"[MATCHING_SUCCESS] ScrapingTask {scraping_task.uid} updated to IMPORTED"
                )
            else:
                print(f"[MATCHING_WARNING] No related ScrapingTask found to update")

            db.commit()
            print(
                f"[MATCHING_SUCCESS] Matching process completed successfully for task {task_id}"
            )

        except Exception as e:
            db.rollback()
            print(f"[MATCHING_ERROR] Database error during status update: {str(e)}")
            raise e

    except Exception as e:
        print(f"[MATCHING_ERROR] Fatal error in matching process: {str(e)}")

        # Update matching task status to ERROR
        db.begin()
        try:
            matching_task = MatchingTask.nodes.get_or_none(uid=task_id)

            if matching_task:
                matching_task.status = "ERROR"
                matching_task.finishedAt = timezone.now()
                matching_task.save()
                print(
                    f"[MATCHING_ERROR] MatchingTask {task_id} status updated to ERROR"
                )
            else:
                print(
                    f"[MATCHING_ERROR] Could not find MatchingTask {task_id} to update error status"
                )

            db.commit()

        except Exception as db_error:
            db.rollback()
            print(
                f"[MATCHING_ERROR] Database error during error status update: {str(db_error)}"
            )

        # Re-raise the exception so Celery marks the task as FAILURE
        raise e
