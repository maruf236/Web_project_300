import os
from dotenv import load_dotenv
load_dotenv()

def _need(k):
    v = os.getenv(k)
    if not v:
        raise RuntimeError(f"Missing env {k}")
    return v

class Config:
    DATABASE_URL = _need("DATABASE_URL")
    JWT_SECRET = _need("JWT_SECRET")
    CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:5173")
    STUDENT_DOMAINS = tuple(os.getenv("STUDENT_EMAIL_DOMAINS", ".ac.bd,.edu.bd").split(","))
    BASE_RATE_BDT_PER_KM = 10  # FR-030
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024
