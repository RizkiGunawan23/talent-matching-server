import re
from typing import Dict, List


def parse_glints_salary(salary_text: str | None) -> Dict[str, str | int | None]:
    if not salary_text:
        return {
            "minimum_salary": None,
            "maximum_salary": None,
            "salary_unit": None,
            "salary_type": None
        }

    text: str = salary_text.lower()
    salary_type: str | None = None
    unit: str | None = None
    numbers: List[int] = None
    min_salary: int | None = None
    max_salary: int | None = None

    if "bonus" in text:
        salary_type = "Bonus"
    else:
        salary_type = "Base"

    if "bulan" in text or "month" in text:
        unit = "Month"
    elif "tahun" in text or "year" in text:
        unit = "Year"
    elif "project" in text:
        unit = "Project"
    else:
        unit = None

    numbers = re.findall(r'\d[\d\.,]*', text)
    numbers = [int(n.replace('.', '')) for n in numbers]

    if len(numbers) == 0:
        min_salary = max_salary = None
    elif len(numbers) == 1:
        min_salary = numbers[0]
        max_salary = None
    else:
        min_salary = numbers[0]
        max_salary = numbers[1]

    return {
        "minimum_salary": min_salary,
        "maximum_salary": max_salary,
        "salary_unit": unit,
        "salary_type": salary_type
    }


def clean_glints_education(edu_text: str | None) -> str | None:
    if not edu_text:
        return None
    return re.sub(r'minimal\s*', '', edu_text, flags=re.IGNORECASE).strip()


def parse_glints_experience(experience_text: str | None) -> Dict[str, int | None]:
    if not experience_text:
        return {
            "minimum_experience": None,
            "maximum_experience": None
        }

    text: str = experience_text.lower()

    if "kurang dari" in text or "less than" in text:
        return {
            "minimum_experience": 0,
            "maximum_experience": 1
        }

    # Ambil angka: "1 - 3 tahun pengalaman"
    numbers: List[str] = re.findall(r'\d+', text)
    if len(numbers) == 2:
        return {
            "minimum_experience": int(numbers[0]),
            "maximum_experience": int(numbers[1])
        }
    elif len(numbers) == 1:
        return {
            "minimum_experience": int(numbers[0]),
            "maximum_experience": None
        }

    return {
        "minimum_experience": None,
        "maximum_experience": None
    }


def normalize_glints_job_data(job_list: List[Dict[str, str | int | List[str] | None]]) -> List[Dict[str, str | int | List[str] | None]]:
    normalized: List[Dict[str, str | int | List[str] | None]] = []

    for job in job_list:
        salary_info: Dict[str, str | int |
                          None] = parse_glints_salary(job.get("salary"))
        education: str | None = clean_glints_education(
            job.get("minimum_education"))
        experience_info: Dict[str, int | None] = parse_glints_experience(
            job.get("minimum_experience"))

        normalized.append({
            "job_url": job.get("job_url"),
            "image_url": job.get("image_url"),
            "job_title": job.get("job_title"),
            "company_name": job.get("company_name"),
            "subdistrict": job.get("subdistrict"),
            "city": job.get("city"),
            "province": job.get("province"),

            # Normalisasi salary
            "minimum_salary": salary_info["minimum_salary"],
            "maximum_salary": salary_info["maximum_salary"],
            "salary_unit": salary_info["salary_unit"],
            "salary_type": salary_info["salary_type"],

            # Langsung pakai field employment_type dan work_setup
            "employment_type": job.get("employment_type"),
            "work_setup": job.get("work_setup"),

            # Normalisasi education dan experience
            "minimum_education": education,
            "minimum_experience": experience_info["minimum_experience"],
            "maximum_experience": experience_info["maximum_experience"],

            # Tambahan fields (bisa kamu olah lebih lanjut jika mau)
            "required_skills": job.get("required_skills"),
            "job_description": job.get("job_description")
        })

    return normalized
