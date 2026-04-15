import os
from dotenv import load_dotenv

load_dotenv()  # does nothing if no .env file exists

class Config:
    def __init__(self):
        # --- MinIO ---
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY")
        self.minio_bucket = os.getenv("MINIO_BUCKET")
        self.minio_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

config = Config()