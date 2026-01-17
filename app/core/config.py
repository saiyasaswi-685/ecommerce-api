import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = "HS256"
    DATABASE_URL = os.getenv("DATABASE_URL")
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")

settings = Settings()