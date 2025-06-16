import re


def parse_glints_salary(salary_text: str | None) -> dict[str, str | int | None]:
    if not salary_text:
        return {
            "minimum_salary": None,
            "maximum_salary": None,
        }

    text: str = salary_text.lower()
    numbers: list[int] = None
    min_salary: int | None = None
    max_salary: int | None = None

    numbers = re.findall(r"\d[\d\.,]*", text)
    numbers = [int(n.replace(".", "")) for n in numbers]

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
    }


def parse_kalibrr_work_setup(work_setup: str | None) -> str | None:
    """Normalize work setup dari Kalibrr ke format standar"""
    if not work_setup:
        return None

    work_setup_mapping = {
        "Hybrid": "Kerja di kantor atau rumah",
        "Remote/Dari rumah": "Kerja dari rumah",
    }

    return work_setup_mapping.get(work_setup.strip(), work_setup)


def parse_glints_education(edu_text: str | None) -> str | None:
    if not edu_text:
        return None
    return re.sub(r"minimal\s*", "", edu_text, flags=re.IGNORECASE).strip()


def parse_glints_experience(experience_text: str | None) -> dict[str, int | None]:
    if not experience_text:
        return {"minimum_experience": None, "maximum_experience": None}

    text: str = experience_text.lower()

    if "kurang dari" in text or "less than" in text:
        return {"minimum_experience": 0, "maximum_experience": 1}

    # Ambil angka: "1 - 3 tahun pengalaman"
    numbers: list[str] = re.findall(r"\d+", text)
    if len(numbers) == 2:
        return {
            "minimum_experience": int(numbers[0]),
            "maximum_experience": int(numbers[1]),
        }
    elif len(numbers) == 1:
        return {"minimum_experience": int(numbers[0]), "maximum_experience": None}

    return {"minimum_experience": None, "maximum_experience": None}


def normalize_glints_job_data(
    job_list: list[dict[str, str | int | list[str] | None]],
) -> list[dict[str, str | int | list[str] | None]]:
    normalized = []

    for job in job_list:
        salary_info = parse_glints_salary(job.get("salary"))
        work_setup = parse_kalibrr_work_setup(job.get("work_setup"))
        education = parse_glints_education(job.get("minimum_education"))
        experience_info = parse_glints_experience(job.get("minimum_experience"))

        normalized.append(
            {
                "job_url": job.get("job_url"),
                "image_url": job.get("image_url"),
                "job_title": job.get("job_title"),
                "company_name": job.get("company_name"),
                "subdistrict": job.get("subdistrict"),
                "city": job.get("city"),
                "province": job.get("province"),
                "minimum_salary": salary_info["minimum_salary"],
                "maximum_salary": salary_info["maximum_salary"],
                "employment_type": job.get("employment_type"),
                "work_setup": work_setup,
                "minimum_education": education,
                "minimum_experience": experience_info["minimum_experience"],
                "maximum_experience": experience_info["maximum_experience"],
                "required_skills": job.get("required_skills"),
                "job_description": job.get("job_description"),
                "scraped_at": job.get("scraped_at"),
            }
        )

    return normalized
