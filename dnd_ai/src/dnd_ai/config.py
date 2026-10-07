from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PDF_PATH = (
    PROJECT_ROOT.parent
    / "Learning_master"
    / "SP_SRD_CC_v5.2.1.pdf"
)
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
JSON_DIR = DATA_DIR / "json"
CHROMA_DIR = DATA_DIR / "chroma"
MODELS_DIR = DATA_DIR / "models"
ML_DIR = DATA_DIR / "ml"
LLM_DIR = DATA_DIR / "llm"
CLASS_PRIMER_PATH = LLM_DIR / "clases_contexto.md"
GUIDE_DIR = DATA_DIR / "guides"
FIRST_CLASS_GUIDE_PATH = GUIDE_DIR / "primera_clase.md"

SRD_ATTRIBUTION = (
    "Esta obra incluye material procedente del documento de referencia del sistema 5.2.1 "
    "(\"SRD 5.2.1\") de Wizards of the Coast LLC, disponible en https://www.dndbeyond.com/srd. "
    "Licencia CC-BY-4.0: https://creativecommons.org/licenses/by/4.0/legalcode."
)

#: Secciones del SRD a procesar en la fase 1 (rangos de índice de página del PDF,
#: válidos porque la página impresa = índice + 1 en este documento).
SECTIONS: dict[str, dict[str, object]] = {
    "reglas": {
        "titulo": "Reglas de juego (Cómo jugar)",
        "start_heading": "Cómo jugar",
        "first_page": 4,
        "last_page": 20,
    },
    "clases": {
        "titulo": "Clases",
        "start_heading": "Clases",
        "first_page": 31,
        "last_page": 88,
    },
    "glosario": {
        "titulo": "Glosario de reglas",
        "start_heading": "Glosario de reglas",
        "first_page": 193,
        "last_page": 210,
    },
}

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
OLLAMA_BASE_URL = os.environ.get("DND_OLLAMA_URL", "http://127.0.0.1:11434")
# qwen2.5:3b cabe en 8 GB de RAM por CPU. qwen3:4b se reserva para un equipo con más memoria.
OLLAMA_MODEL = os.environ.get("DND_OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_SMALL_MODEL = "qwen2.5:1.5b"
OLLAMA_NUM_CTX = 4096


def ensure_dirs() -> None:
    for d in (RAW_DIR, JSON_DIR, CHROMA_DIR, MODELS_DIR, ML_DIR):
        d.mkdir(parents=True, exist_ok=True)
