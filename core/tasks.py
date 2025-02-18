from celery import shared_task
from celery.utils.log import get_task_logger
from bs4 import BeautifulSoup
import requests
from django.core.cache import cache

logger = get_task_logger(__name__)


def get_content():
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    LANGUAGE = 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT
    session.headers['Accept-Language'] = LANGUAGE
    session.headers['Content-Language'] = LANGUAGE
    return session


def get_jobs_data(html_content) -> list:
    soup = BeautifulSoup(html_content, 'html.parser')

    job_articles = soup.find_all(
        'article', attrs={'data-testid': 'job-card'})

    jobs_data = []
    for article in job_articles:
        job_url = None
        job_url_tag = article.find(
            'a', attrs={'data-automation': 'job-list-view-job-link'})
        if job_url_tag and job_url_tag.has_attr('href'):
            job_url = "https://id.jobstreet.com" + job_url_tag['href']

        img_url = None
        img_container = article.find(
            'div', attrs={'data-automation': 'company-logo'})
        if img_container:
            img_tag = img_container.find('img')
            if img_tag and img_tag.has_attr('src'):
                img_url = img_tag['src']

        title_text = None
        title_tag = article.find('a', attrs={'data-automation': 'jobTitle'})
        if title_tag:
            title_text = title_tag.get_text(strip=True)

        company_text = None
        company_tag = article.find(
            'a', attrs={'data-automation': 'jobCompany'})
        if company_tag:
            company_text = company_tag.get_text(strip=True)

        location_text = None
        location_tags = article.find_all(
            'a', attrs={'data-automation': 'jobLocation'})
        if location_tags:
            locations = [tag.get_text(strip=True) for tag in location_tags]
            location_text = ", ".join(locations)

        category_text = None
        subcat_tag = article.find(
            attrs={'data-automation': 'jobSubClassification'})
        if subcat_tag:
            category_text = subcat_tag.get_text(strip=True)

        job_type = None
        all_div_tags = article.findAll('div')
        for div_tag in all_div_tags:
            children = [
                child for child in div_tag.children if hasattr(child, 'name')]
            if len(children) == 1 and children[0].name == 'p':
                p_text = children[0].get_text(strip=True).lower()
                keywords = ["full time", "paruh waktu", "kontrak"]
                for keyword in keywords:
                    if keyword in p_text:
                        job_type = keyword.capitalize() if keyword != "full time" else "Purnawaktu"

        salary_text = None
        salary_tag = article.find(
            'span', attrs={'data-automation': 'jobSalary'})
        if salary_tag:
            salary_text = salary_tag.get_text(strip=True)

        highlight_descriptions = []
        highlight_description_ul_tags = article.find('ul')
        if highlight_description_ul_tags:
            highlight_description_tags = highlight_description_ul_tags.find_all(
                'span')
            for highlight_description_tag in highlight_description_tags:
                highlight_descriptions.append(
                    highlight_description_tag.get_text(strip=True))

        job = {
            "job_url": job_url,
            "image": img_url,
            "title": title_text,
            "company": company_text,
            "location": location_text,
            "category": category_text,
            "job_type": job_type,
            "salary": salary_text,
            "highlight_descriptions": highlight_descriptions,
        }
        jobs_data.append(job)

    return jobs_data


@shared_task(bind=True)
def scrape_jobstreet_data(self):
    website_url = "https://id.jobstreet.com/id/jobs-in-information-communication-technology"
    total_pages = 30

    scraped_data = []
    for page in range(total_pages):
        current_page_url = f"{website_url}?page={page+1}" if page > 0 else website_url

        html_content = get_content().get(f'{current_page_url}').text
        new_data = get_jobs_data(html_content)
        scraped_data.extend(new_data)
        progress = int(((page + 1) / total_pages) * 100)
        cache.set(
            f'scraping_progress_{self.request.id}', progress, timeout=3600)
        self.update_state(state='PROGRESS', meta={'progress': progress})

    cache.set(f'scraping_progress_{self.request.id}', 100, timeout=3600)

    return {"total_data": len(scraped_data), "data": scraped_data}
