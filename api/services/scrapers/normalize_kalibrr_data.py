import json
import os
import re


def load_city_province_mapping():
    """Load city-province mapping dari file JSON"""
    try:
        dict_path = os.path.join(
            os.path.dirname(__file__), "dictionary", "city_province_dictionary.json"
        )
        print(f"[DEBUG] Loading city-province mapping from: {dict_path}")
        with open(dict_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
            print(f"[DEBUG] Loaded {len(mapping)} city-province pairs")
            return mapping
    except Exception as e:
        print(f"[ERROR] Error loading city-province dictionary: {e}")
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
        print(f"[DEBUG] Normalizing city: {city_text}")
        if not city_text:
            print("[DEBUG] City text is None or empty")
            return {"city": None, "province": None}

        city_province_mapping = load_city_province_mapping()

        # Clean city name
        city = city_text.strip()
        print(f"[DEBUG] Cleaned city: {city}")

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
        print(f"[DEBUG] Normalized city: {normalized_city}")

        # Get province from mapping
        province = city_province_mapping.get(normalized_city)
        print(f"[DEBUG] Province for '{normalized_city}': {province}")

        if province is None:
            print(f"[WARNING] Province not found for city '{normalized_city}'")
        return {"city": normalized_city, "province": province}
    except Exception as e:
        print(f"[ERROR] Error normalizing city and province: {city_text}, Error: {e}")
        return {"city": None, "province": None}


def normalize_kalibrr_salary(salary_text: str | None) -> dict[str, int | None]:
    """Parse dan normalize salary dari Kalibrr"""
    try:
        print(f"[DEBUG] Normalizing salary: {salary_text}")
        if not salary_text:
            print("[DEBUG] Salary text is None or empty")
            return {"minimum_salary": None, "maximum_salary": None}

        # Remove currency dan normalize
        cleaned = salary_text.replace("IDR", "").replace("/ month", "").strip()
        print(f"[DEBUG] Cleaned salary text: {cleaned}")

        # Pattern untuk range salary: "10.000.000,00 - 15.000.000,00"
        range_pattern = r"([\d\.,]+)\s*-\s*([\d\.,]+)"
        match = re.search(range_pattern, cleaned)

        def parse_salary_component(s: str) -> int | None:
            parts = s.split(",")
            main_part = parts[0]
            main_part = main_part.replace(".", "")
            try:
                value = int(main_part)
                print(f"[DEBUG] Parsed salary component '{s}' -> {value}")
                return value
            except ValueError:
                print(f"[ERROR] Failed to parse salary component: {s}")
                return None

        if match:
            min_salary = parse_salary_component(match.group(1))
            max_salary = parse_salary_component(match.group(2))
            print(f"[DEBUG] Salary range: {min_salary} - {max_salary}")
            return {"minimum_salary": min_salary, "maximum_salary": max_salary}

        # Pattern untuk single salary
        single_pattern = r"([\d\.,]+)"
        match = re.search(single_pattern, cleaned)

        if match:
            salary = parse_salary_component(match.group(1))
            print(f"[DEBUG] Single salary: {salary}")
            return {"minimum_salary": salary, "maximum_salary": None}

        print("[DEBUG] Salary pattern not matched")
        return {"minimum_salary": None, "maximum_salary": None}
    except Exception as e:
        print(f"[ERROR] Error parsing salary: {salary_text}, Error: {e}")
        return {"minimum_salary": None, "maximum_salary": None}


def normalize_kalibrr_employment_type(employment_type: str | None) -> str | None:
    """Normalize employment type dari Kalibrr ke format standar"""
    try:
        print(f"[DEBUG] Normalizing employment_type: {employment_type}")
        if not employment_type:
            print("[DEBUG] Employment type is None or empty")
            return None

        employment_mapping = {
            "Pekerja lepas / Freelance": "Freelance",
        }

        result = employment_mapping.get(employment_type.strip(), employment_type)
        print(f"[DEBUG] Normalized employment_type: {result}")
        return result
    except Exception as e:
        print(
            f"[ERROR] Error normalizing employment type: {employment_type}, Error: {e}"
        )
        return employment_type


def normalize_kalibrr_work_setup(work_setup: str | None) -> str | None:
    """Normalize work setup dari Kalibrr ke format standar"""
    try:
        print(f"[DEBUG] Normalizing work_setup: {work_setup}")
        if not work_setup:
            print("[DEBUG] Work setup is None or empty")
            return None

        work_setup_mapping = {
            "Hibrida": "Kerja di kantor atau rumah",
            "Jarak jauh": "Kerja dari rumah",
        }

        result = work_setup_mapping.get(work_setup.strip(), work_setup)
        print(f"[DEBUG] Normalized work_setup: {result}")
        return result
    except Exception as e:
        print(f"[ERROR] Error normalizing work setup: {work_setup}, Error: {e}")
        return work_setup


def normalize_kalibrr_education(education_text: str | None) -> str | None:
    """Normalize education dari Kalibrr ke format standar"""
    try:
        print(f"[DEBUG] Normalizing education: {education_text}")
        if not education_text:
            print("[DEBUG] Education text is None or empty")
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

        result = education_mapping.get(education, education)
        print(f"[DEBUG] Normalized education: {result}")
        return result
    except Exception as e:
        print(f"[ERROR] Error normalizing education: {education_text}, Error: {e}")
        return education_text


def normalize_kalibrr_job_data(
    job_list: list[dict[str, str | int | list[str] | None]],
) -> list[dict[str, str | int | list[str] | None]]:
    """Normalize semua job data dari Kalibrr"""
    print(f"[DEBUG] Start normalizing {len(job_list) if job_list else 0} jobs")
    normalized = []

    for idx, job in enumerate(job_list):
        print(
            f"\n[DEBUG] Normalizing job #{idx+1}: {job.get('job_title')} ({job.get('job_url')})"
        )
        try:
            # Normalize location (city and province)
            location_info = normalize_kalibrr_city_province(job.get("city"))
            print(f"[DEBUG] Location info: {location_info}")

            # Normalize salary
            salary_info = normalize_kalibrr_salary(job.get("salary"))
            print(f"[DEBUG] Salary info: {salary_info}")

            # Normalize employment details
            employment_type = normalize_kalibrr_employment_type(
                job.get("employment_type")
            )
            print(f"[DEBUG] Employment type: {employment_type}")

            work_setup = normalize_kalibrr_work_setup(job.get("work_setup"))
            print(f"[DEBUG] Work setup: {work_setup}")

            # Normalize education
            education = normalize_kalibrr_education(job.get("minimum_education"))
            print(f"[DEBUG] Education: {education}")

            # Parse experience
            experience_info = job.get("minimum_experience")
            print(f"[DEBUG] Experience info: {experience_info}")

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
            print(f"[DEBUG] Normalized job data appended.")
        except Exception as e:
            print(
                f"[ERROR] Error normalizing job data: {job.get('job_url')}, Error: {e}"
            )
            continue

    print(f"[DEBUG] Finished normalizing. Total normalized: {len(normalized)}")
    return normalized
