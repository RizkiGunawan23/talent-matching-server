from celery import shared_task

from core.scrapers.main_scraper import scrape_all_websites


@shared_task(bind=True)
def scrape_job_data(self):
    """Task Celery untuk scraping data Glints"""
    return scrape_all_websites(self.request.id, self.update_state)
