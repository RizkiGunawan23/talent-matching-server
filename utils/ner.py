import os

import spacy
from django.conf import settings

# Path relatif dari BASE_DIR
NER_MODEL_PATH = os.path.join(settings.BASE_DIR, "talent_matching_ner_model")


def load_ner_model():
    """Load model NER Spacy"""
    if not os.path.exists(NER_MODEL_PATH):
        raise FileNotFoundError(f"Model NER tidak ditemukan di {NER_MODEL_PATH}")

    return spacy.load(NER_MODEL_PATH)
