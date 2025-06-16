from api.services.scrapers.glints_scraper import scrape_glints_jobs
from api.services.scrapers.helper import is_task_cancelled
from api.services.scrapers.kalibrr_scraper import scrape_kalibrr_jobs
from api.services.scrapers.ner_functions import (
    load_ner_model,
    process_job_data_with_ner,
)
from api.services.scrapers.normalize_glints_data import normalize_glints_job_data
from api.services.scrapers.normalize_kalibrr_data import normalize_kalibrr_job_data


def scrape_all_websites(task_id: str, update_state_func=None):
    try:
        """Main function untuk scraping dan skill extraction"""
        print("Starting scraping process with NER skill extraction...")

        # Load NER model
        ner_model = load_ner_model()

        # Initialize job data list
        all_job_data = {
            "glints": [],
            "kalibrr": [],
        }
        scraped_jobs = 0

        # Scrape job data from Glints
        print("Scraping Glints...")
        if update_state_func:
            update_state_func(task_id, "SCRAPING_GLINTS", {})

        glints_job_data, total_glints_jobs = scrape_glints_jobs(
            task_id, update_state_func
        )

        glints_job_data = normalize_glints_job_data(glints_job_data)

        scraped_jobs += len(glints_job_data)

        all_job_data["glints"] = glints_job_data

        # Scrape job data from Kalibrr
        print("Scraping Kalibrr...")
        if update_state_func:
            update_state_func(
                task_id, "SCRAPING_KALIBRR", {"scraped_jobs": scraped_jobs}
            )

        kalibrr_job_data, total_kalibrr_jobs = scrape_kalibrr_jobs(
            task_id, update_state_func, scraped_jobs
        )

        kalibrr_job_data = normalize_kalibrr_job_data(kalibrr_job_data)

        scraped_jobs += len(kalibrr_job_data)

        all_job_data["kalibrr"] = kalibrr_job_data

        if is_task_cancelled(task_id):
            return []

        if not ner_model:
            print("NER model not loaded. Returning raw scraped data...")
            final_job_data = []

            final_job_data.extend(glints_job_data if glints_job_data else [])
            final_job_data.extend(kalibrr_job_data if kalibrr_job_data else [])
            return final_job_data

        print(f"Processing {scraped_jobs} jobs with NER...")
        if update_state_func:
            update_state_func(
                task_id, "PROCESSING_JOB_WITH_NER", {"scraped_jobs": scraped_jobs}
            )

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

        print(
            f"Scraping and NER processing complete. Total jobs: {len(post_processed_jobs)}"
        )
        print(f"- Glints: {len(glints_job_data) if glints_job_data else 0} jobs")
        print(f"- Kalibrr: {len(kalibrr_job_data) if kalibrr_job_data else 0} jobs")

        return post_processed_jobs

    except Exception as e:
        print(f"Error during scraping process: {e}")
        return []
