from core.scrapers.glints_scraper import scrape_glints_jobs
from core.scrapers.kalibrr_scraper import scrape_kalibrr_jobs


def scrape_all_websites(task_id: str, update_state_func=None):
    # Initialize an empty dictionary to store job data
    job_data = []

    # Scrape job data from Glints
    glints_job_data = scrape_glints_jobs(task_id, update_state_func)
    job_data.extend(glints_job_data)

    # Scrape job data from Kalibrr
    # kalibrr_job_data = scrape_kalibrr_jobs(task_id, update_state_func)
    # job_data["kalibrr"] = kalibrr_job_data

    return job_data
