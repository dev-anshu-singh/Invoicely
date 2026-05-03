import os
from dotenv import load_dotenv

load_dotenv()

LLAMA_CLOUD_API_KEY: str = os.getenv("LLAMA_CLOUD_API_KEY")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")

SQLITE_DB_PATH: str = "invoices.db"
CHROMA_DB_PATH: str = "./chroma_db"

GEMINI_MODEL_NAME: str = "gemini-2.5-flash"