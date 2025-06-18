import json
import os
import re


def load_city_province_mapping():
    """Load city-province mapping dari file JSON"""
    try:
        dict_path = os.path.join(
            os.path.dirname(__file__), "dictionary", "city_province_dictionary.json"
        )
        with open(dict_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
            return mapping
    except Exception as e:
        return {
            "South Tangerang": "Banten",
            "Tangerang Selatan": "Banten",
            "Jakarta Selatan": "DKI Jakarta",
            "Central Jakarta": "DKI Jakarta",
            "South Jakarta": "DKI Jakarta",
            "Jakarta": "DKI Jakarta",
            "Tangerang": "Banten",
            "Bandung": "Jawa Barat",
            "Surabaya": "Jawa Timur",
            "Medan": "Sumatera Utara",
            "Makassar": "Sulawesi Selatan",
        }


def normalize_kalibrr_city_province(city_text: str | None) -> dict[str, str | None]:
    """Normalize city dari Kalibrr dan dapatkan province"""
    try:
        if not city_text:
            return {"city": None, "province": None}

        city_province_mapping = load_city_province_mapping()

        city = city_text.strip()

        # Mapping untuk nama kota yang tidak konsisten dari Kalibrr
        city_normalization = {
            "South Tangerang": "Tangerang Selatan",
            "Jakarta Selatan": "South Jakarta",
            "Central Jakarta": "Central Jakarta",
            "South Jakarta": "South Jakarta",
            "Jakarta": "Central Jakarta",  # Default Jakarta ke Central
            "Tangerang Kota": "Tangerang",
        }

        # Normalize city name
        normalized_city = city_normalization.get(city, city)

        # Get province from mapping
        province = city_province_mapping.get(normalized_city)

        return {"city": normalized_city, "province": province}
    except Exception:
        return {"city": None, "province": None}


def normalize_kalibrr_salary(salary_text: str | None) -> dict[str, int | None]:
    """Parse dan normalize salary dari Kalibrr"""
    try:
        if not salary_text:
            return {"minimum_salary": None, "maximum_salary": None}

        # Remove currency dan normalize
        cleaned = salary_text.replace("IDR", "").replace("/ month", "").strip()

        # Pattern untuk range salary: "10.000.000,00 - 15.000.000,00"
        range_pattern = r"([\d\.,]+)\s*-\s*([\d\.,]+)"
        match = re.search(range_pattern, cleaned)

        def parse_salary_component(s: str) -> int | None:
            parts = s.split(",")
            main_part = parts[0]
            main_part = main_part.replace(".", "")
            try:
                value = int(main_part)
                return value
            except ValueError:
                return None

        if match:
            min_salary = parse_salary_component(match.group(1))
            max_salary = parse_salary_component(match.group(2))
            return {"minimum_salary": min_salary, "maximum_salary": max_salary}

        # Pattern untuk single salary
        single_pattern = r"([\d\.,]+)"
        match = re.search(single_pattern, cleaned)

        if match:
            salary = parse_salary_component(match.group(1))
            return {"minimum_salary": salary, "maximum_salary": None}

        return {"minimum_salary": None, "maximum_salary": None}
    except Exception:
        return {"minimum_salary": None, "maximum_salary": None}


def normalize_kalibrr_employment_type(employment_type: str | None) -> str | None:
    """Normalize employment type dari Kalibrr ke format standar"""
    try:
        if not employment_type:
            return None

        employment_mapping = {
            "Pekerja lepas / Freelance": "Freelance",
        }

        return employment_mapping.get(employment_type.strip(), employment_type)
    except Exception:
        return employment_type


def normalize_kalibrr_work_setup(work_setup: str | None) -> str | None:
    """Normalize work setup dari Kalibrr ke format standar"""
    try:
        if not work_setup:
            return None

        work_setup_mapping = {
            "Hibrida": "Kerja di kantor atau rumah",
            "Jarak jauh": "Kerja dari rumah",
        }

        result = work_setup_mapping.get(work_setup.strip(), work_setup)
        return result
    except Exception:
        return work_setup


def normalize_kalibrr_education(education_text: str | None) -> str | None:
    """Normalize education dari Kalibrr ke format standar"""
    try:
        if not education_text:
            return None

        education = education_text.strip()

        # Mapping manual untuk data Kalibrr
        education_mapping = {
            "Semua Tingkat Pendidikan": None,
            "Di bawah SMA": "SMA",
            "SMA": "SMA/SMK",
            "Lulus SMA": "SMA/SMK",
            "Vokasi (D3)": "Diploma (D1-D4)",
            "Lulus program Vokasi (D3)": "Diploma (D1-D4)",
            "Diploma (D3)": "Diploma (D1-D4)",
            "Lulus program Diploma (D3)": "Diploma (D1-D4)",
            "Sarjana (S1)": "Sarjana (S1)",
            "Lulus program Sarjana (S1)": "Sarjana (S1)",
            "Program Magister (S2)": "Magister (S2)",
            "Lulus program Magister (S2)": "Magister (S2)",
            "Program Doktor (S3)": "Doktor (S3)",
            "Lulus program Doktor (S3)": "Doktor (S3)",
        }

        return education_mapping.get(education, education)
    except Exception:
        return education_text


def normalize_kalibrr_job_data(
    job_list: list[dict[str, str | int | list[str] | None]],
) -> list[dict[str, str | int | list[str] | None]]:
    """Normalize semua job data dari Kalibrr"""
    normalized = []

    for idx, job in enumerate(job_list):
        try:
            location_info = normalize_kalibrr_city_province(job.get("city"))
            salary_info = normalize_kalibrr_salary(job.get("salary"))
            employment_type = normalize_kalibrr_employment_type(
                job.get("employment_type")
            )
            work_setup = normalize_kalibrr_work_setup(job.get("work_setup"))
            education = normalize_kalibrr_education(job.get("minimum_education"))
            experience_info = job.get("minimum_experience")

            normalized.append(
                {
                    "job_url": job.get("job_url"),
                    "image_url": job.get("image_url"),
                    "job_title": job.get("job_title"),
                    "company_name": job.get("company_name"),
                    "subdistrict": None,
                    "city": location_info["city"],
                    "province": location_info["province"],
                    "minimum_salary": salary_info["minimum_salary"],
                    "maximum_salary": salary_info["maximum_salary"],
                    "employment_type": employment_type,
                    "work_setup": work_setup,
                    "minimum_education": education,
                    "minimum_experience": experience_info,
                    "maximum_experience": None,
                    "required_skills": job.get("required_skills"),
                    "job_description": job.get("job_description"),
                    "scraped_at": job.get("scraped_at"),
                }
            )
        except Exception:
            continue
    return normalized
