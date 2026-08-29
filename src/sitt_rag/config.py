import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
VOYAGE_MODEL = "voyage-4"

WIKIPEDIA_LANG = "en"
WIKIPEDIA_ORIGIN = f"https://{WIKIPEDIA_LANG}.wikipedia.org"
LIST_OF_CRYPTIDS_TITLE = "List_of_cryptids"

CC_BY_SA_LICENSE = "CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)"

DATA_DIR = Path(os.environ.get("SITT_RAG_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
GOLDEN_QUERIES_PATH = Path(
    os.environ.get("SITT_RAG_GOLDEN_QUERIES", Path(__file__).resolve().parents[2] / "golden_queries.json")
)

CHUNK_TOKEN_BUDGET = 500
CHUNK_OVERLAP_PARAGRAPHS = 1

USER_AGENT = "sitt-rag/0.1 (https://github.com/randclem/sitt-rag; cryptid RAG MCP server)"
