from api.services.admin.scrapers.glints_scraper import scrape_glints_jobs
from api.services.admin.scrapers.helper import is_task_cancelled
from api.services.admin.scrapers.kalibrr_scraper import scrape_kalibrr_jobs
from api.services.admin.scrapers.ner_services import (
    load_ner_model,
    process_job_data_with_ner,
)
from api.services.admin.scrapers.normalize_glints_data import normalize_glints_job_data
from api.services.admin.scrapers.normalize_kalibrr_data import (
    normalize_kalibrr_job_data,
)


def scrape_all_websites(task_id: str, update_state_func=None):
    try:
        """Main function untuk scraping dan skill extraction"""
        # Load NER model
        if update_state_func:
            update_state_func(task_id, "LOADING_NER_MODEL", {})

        ner_model = load_ner_model()

        # Initialize job data list
        all_job_data = {
            "glints": [],
            "kalibrr": [],
        }
        scraped_jobs = 0

        # Scrape job data from Glints
        if update_state_func:
            update_state_func(task_id, "SCRAPING_GLINTS", {})

        glints_job_data = scrape_glints_jobs(task_id, update_state_func)

        if is_task_cancelled(task_id):
            return []

        glints_job_data = normalize_glints_job_data(glints_job_data)

        if is_task_cancelled(task_id):
            return []

        scraped_jobs += len(glints_job_data)

        all_job_data["glints"] = glints_job_data

        # Scrape job data from Kalibrr
        if update_state_func:
            update_state_func(
                task_id, "SCRAPING_KALIBRR", {"scraped_jobs": scraped_jobs}
            )

        kalibrr_job_data = scrape_kalibrr_jobs(task_id, update_state_func, scraped_jobs)

        if is_task_cancelled(task_id):
            return []

        kalibrr_job_data = normalize_kalibrr_job_data(kalibrr_job_data)

        if is_task_cancelled(task_id):
            return []

        scraped_jobs += len(kalibrr_job_data)

        all_job_data["kalibrr"] = kalibrr_job_data

        if is_task_cancelled(task_id):
            return []

        if not ner_model:
            final_job_data = []
            final_job_data.extend(glints_job_data if glints_job_data else [])
            final_job_data.extend(kalibrr_job_data if kalibrr_job_data else [])
            return final_job_data

        if update_state_func:
            update_state_func(
                task_id, "PROCESSING_JOB_WITH_NER", {"scraped_jobs": scraped_jobs}
            )

        if is_task_cancelled(task_id):
            return []

        post_processed_jobs = process_job_data_with_ner(all_job_data, ner_model)

        if is_task_cancelled(task_id):
            return []

        # Final processing complete
        if update_state_func:
            update_state_func(
                task_id,
                "NER_PROCESSING_COMPLETE",
                {"total_jobs": len(post_processed_jobs)},
            )

        if is_task_cancelled(task_id):
            return []

        return post_processed_jobs
    except Exception as e:
        print(f"Error during scraping process: {e}")
        raise e
