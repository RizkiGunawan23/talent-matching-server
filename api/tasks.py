import datetime

from celery import shared_task
from django.utils import timezone
from neomodel import db

from api.models import ScrapingTask
from api.services.matchers.matchers_functions import matching_after_scraping
from api.services.scrapers.main_scraper import scrape_all_websites


@shared_task(bind=True)
def scrape_job_data(self):
    """Task Celery untuk scraping data"""
    task_id = self.request.id

    try:
        result = scrape_all_websites(task_id, self.update_state)
        return result
    except Exception as e:
        # Update scraping task status to ERROR when exception occurs
        try:
            scraping_task = ScrapingTask.nodes.filter(uid=task_id).first_or_none()
            if scraping_task:
                db.begin()
                try:
                    scraping_task.status = "ERROR"
                    scraping_task.message = "Scraping task failed due to an error."
                    scraping_task.save()
                    db.commit()
                except Exception as db_error:
                    db.rollback()
                    print(f"Failed to update scraping task status: {db_error}")
        except Exception as update_error:
            print(f"Error updating task status: {update_error}")

        # Re-raise the exception so Celery marks the task as FAILURE
        raise e


@shared_task(bind=True)
def matching_job_after_scraping(self, jobs_data=[]):
    """Task Celery untuk melakukan matching job setelah scraping selesai"""
    task_id = self.request.id

    try:
        matching_after_scraping(task_id, self.update_state, jobs_data)
        cypher = """
        MATCH (m:Maintenance)
        SET m.isMaintenance = false
        """
        db.cypher_query(cypher)

        db.begin()
        try:
            print("Updating MatchingTask status to IMPORTED")

            cypher = """
            MATCH (m:MatchingTask {uid: $task_id})<-[:HAS_PROCESS]-(s:ScrapingTask)
            SET s.status = 'IMPORTED', 
                s.finishedAt = $finished_at,
                m.status = 'IMPORTED',
                m.finishedAt = $finished_at
            """
            params = {
                "task_id": task_id,
            }
            db.cypher_query(cypher, params)
            db.commit()
            print("Done Updating MatchingTask status to IMPORTED")
        except Exception as e:
            db.rollback()
    except Exception as e:
        db.begin()
        try:
            cypher = """
            MATCH (m:MatchingTask {uid: $task_id})
            SET m.status = 'ERROR',
                m.finishedAt = $finished_at
            RETURN m
            """
            params = {
                "task_id": task_id,
                "finished_at": timezone.now(),
            }
            db.cypher_query(cypher, params)
            db.commit()
        except Exception as e:
            db.rollback()

        # Re-raise the exception so Celery marks the task as FAILURE
        raise e
