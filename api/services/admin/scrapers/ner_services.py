import json
import os
import re

import spacy
from bs4 import BeautifulSoup


def load_ner_model():
    """Load spaCy NER model untuk skill extraction"""
    try:
        model_path = "/app/talent_matching_ner_model"

        if not os.path.exists(model_path):
            return None

        ner_model = spacy.load(model_path)
        return ner_model
    except Exception as e:
        return None


def remove_html_tags(html_string):
    """Pakai fungsi ini sebelum NER untuk membersihkan HTML tags"""
    if not html_string:
        return ""
    soup = BeautifulSoup(html_string, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def extract_entities_from_text(text: str, ner_model) -> dict[str, set[str]]:
    """Extract semua entities dari text menggunakan NER model"""
    if not text or not ner_model:
        return {
            "hardskills": set(),
            "softskills": set(),
            "experience": set(),
        }

    try:
        # Clean text dari HTML tags
        clean_text = remove_html_tags(text)

        # Process text dengan NER model
        doc = ner_model(clean_text)

        # Categorize entities berdasarkan label
        entities = {
            "hardskills": set(),
            "softskills": set(),
            "experience": set(),
        }

        for ent in doc.ents:
            entity_text = ent.text.strip().lower()

            if ent.label_ == "HARDSKILL":
                entities["hardskills"].add(entity_text)
            elif ent.label_ == "SOFTSKILL":
                entities["softskills"].add(entity_text)
            elif ent.label_ == "EXPERIENCE":
                entities["experience"].add(entity_text)

        return entities
    except Exception:
        return {
            "hardskills": set(),
            "softskills": set(),
            "experience": set(),
        }


def filter_softskills_from_skills(skills: list[str], ner_model) -> list[str]:
    """Filter dan hapus softskills dari daftar skills"""
    if not skills or not ner_model:
        return skills

    # Convert skills list menjadi text untuk di-process NER
    skills_text = " , ".join(skills)
    entities = extract_entities_from_text(skills_text, ner_model)

    # Filter out softskills
    softskills = entities["softskills"]
    filtered_skills = []

    for skill in skills:
        skill_lower = skill.strip().lower()
        if skill_lower not in softskills:
            filtered_skills.append(skill)

    return filtered_skills


def parse_experience_entities(experience_entities: set[str]) -> dict[str, int | None]:
    """
    Parse hasil NER experience menjadi minimum_experience dan maximum_experience.
    Support separator: '-', '–', 'sampai', 'to'
    """
    min_exp = None
    max_exp = None

    for exp in experience_entities:
        # Hilangkan kata-kata non-angka
        exp_clean = (
            exp.replace("tahun", "").replace("years", "").replace("thn", "").strip()
        )
        # Cek range dengan berbagai separator
        range_match = re.match(
            r"(\d+)\s*(?:-|–|sampai|to)\s*(\d+)", exp_clean, re.IGNORECASE
        )
        if range_match:
            min_exp = int(range_match.group(1))
            max_exp = int(range_match.group(2))
            break  # Ambil range pertama yang ditemukan
        # Cek single number
        single_match = re.match(r"(\d+)", exp_clean)
        if single_match and min_exp is None:
            min_exp = int(single_match.group(1))
            max_exp = None

    return {
        "minimum_experience": min_exp,
        "maximum_experience": max_exp,
    }


def load_skills_dictionary():
    """Load skills dictionary dari file JSON"""
    try:
        dict_path = os.path.join(
            os.path.dirname(__file__), "dictionary", "skills_dictionary.json"
        )
        with open(dict_path, "r", encoding="utf-8") as f:
            skills_dict = json.load(f)
        return skills_dict
    except Exception:
        return {}


def map_skill_to_main_keyword(skill: str, skills_dict: dict) -> str:
    """Cek skill di kamus, jika ada return keyword utama, jika tidak return seadanya"""
    skill_lower = skill.strip().lower()
    for group in skills_dict.values():
        for main_keyword, variants in group.items():
            if skill_lower == main_keyword.lower() or skill_lower in [
                v.lower() for v in variants
            ]:
                return main_keyword
    return skill


def process_glints_job(
    job: dict[str, any], ner_model, update_state_func=None
) -> dict[str, any]:
    """Process Glints job data dengan NER"""
    try:
        skills_dict = load_skills_dictionary()

        existing_skills = job.get("required_skills", [])
        filtered_skills = filter_softskills_from_skills(existing_skills, ner_model)

        description = job.get("job_description", "")
        description_entities = extract_entities_from_text(description, ner_model)
        hardskills_from_desc = description_entities["hardskills"]

        all_hardskills = set(filtered_skills)
        all_hardskills.update(hardskills_from_desc)

        mapped_skills = set()
        for skill in all_hardskills:
            mapped_skills.add(map_skill_to_main_keyword(skill, skills_dict))
        job["required_skills"] = list(mapped_skills)

        return job
    except Exception:
        return job


def process_kalibrr_job(job: dict[str, any], ner_model) -> dict[str, any]:
    """Process Kalibrr job data dengan NER"""
    try:
        skills_dict = load_skills_dictionary()

        description = job.get("job_description", "")
        description_entities = extract_entities_from_text(description, ner_model)
        hardskills_from_desc = description_entities["hardskills"]

        # Jangan pakai .lower() di sini!
        all_hardskills = set(hardskills_from_desc)

        experience_from_desc = description_entities["experience"]

        mapped_skills = set()
        for skill in all_hardskills:
            mapped_skills.add(map_skill_to_main_keyword(skill, skills_dict))
        job["required_skills"] = list(mapped_skills)

        exp_result = parse_experience_entities(experience_from_desc)
        job["minimum_experience"] = exp_result["minimum_experience"]
        job["maximum_experience"] = exp_result["maximum_experience"]

        return job
    except Exception:
        return job


def process_job_data_with_ner(
    job_data: dict[str, list[dict[str, any]]], ner_model
) -> list[dict[str, any]]:
    """Process job data berdasarkan source (glints/kalibrr)"""
    processed_jobs = []
    glints_data = job_data.get("glints", [])
    kalibrr_data = job_data.get("kalibrr", [])

    if glints_data:
        for job in glints_data:
            processed_job = job
            try:
                processed_job = process_glints_job(job, ner_model)
                processed_jobs.append(processed_job)

            except Exception:
                processed_jobs.append(processed_job)

    if kalibrr_data:
        for job in kalibrr_data:
            try:
                processed_job = process_kalibrr_job(job, ner_model)
                processed_jobs.append(processed_job)

            except Exception:
                processed_jobs.append(job)

    return processed_jobs
