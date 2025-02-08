from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from bs4 import BeautifulSoup
import requests


class JobRecommendationView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        return Response({"message": "get JobRecommendationListView"}, status=status.HTTP_200_OK)


class JobDetailView(APIView):
    pass


def get_content(website_url):
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    LANGUAGE = 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT
    session.headers['Accept-Language'] = LANGUAGE
    session.headers['Content-Language'] = LANGUAGE
    return session.get(f'{website_url}').text


def get_jobs_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    job_articles = soup.find_all(
        'article', class_=lambda c: c and '_1fggenz0' in c.split())

    jobs_data = []
    for article in job_articles:
        job_url = None
        job_url_tag = article.find(
            'a', attrs={'data-automation': 'job-list-view-job-link'})
        if job_url_tag and job_url_tag.has_attr('href'):
            job_url = "https://id.jobstreet.com" + job_url_tag['href']

        img_url = None
        img_tag = article.find('img', class_='jsvdfj0')
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
        p_tags = article.find('p', class_='_1fggenz0')
        p_text = p_tags.get_text(strip=True).lower()
        keywords = ["full time", "paruh waktu", "kontrak"]
        for keyword in keywords:
            if keyword in p_text:
                job_type = keyword.lower() if keyword != "full time" else "Purnawaktu"

        salary_text = None
        salary_tag = article.find(attrs={'data-automation': 'jobSalary'})
        if salary_tag:
            salary_text = salary_tag.get_text(strip=True)

        highlight_descriptions = []
        highlight_description_ul_tags = article.find(
            'ul', class_='_1fggenz0 _1fggenz3 _1feq2e75b _1feq2e7hf _1feq2e76n _1feq2e7i7')
        if highlight_description_ul_tags:
            highlight_description_tags = highlight_description_ul_tags.find_all(
                'span', class_='_1fggenz0 _1feq2e74z _474bdu0 _474bdu1 _474bdu21 _18ybopc4 _474bdu7')
            for highlight_description_tag in highlight_description_tags:
                highlight_descriptions.append(
                    highlight_description_tag.get_text(strip=True))

        # short_description = None
        # short_description_tag = article.find(
        #     'span', attrs={'data-automation': 'jobShortDescription'})
        # if short_description_tag:
        #     short_description = short_description_tag.get_text(strip=True)

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
            # "short_description": short_description,
        }
        jobs_data.append(job)

    return jobs_data


class JobScrapingView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    website_url = "https://id.jobstreet.com/id/jobs-in-information-communication-technology"

    def post(self, request):
        try:
            html_content = get_content(self.website_url)
            data = []
            data = get_jobs_data(html_content)
            return Response({"len": len(data), "data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
