import os
from minio_backend import MinioBackend
from data_loader import StorageBackend
from data_loader import load_day

# ENV variables import
from dotenv import load_dotenv
load_dotenv()

def create_storage_from_env() -> StorageBackend:
    # Tailor the values to your MinIO credentials
    return MinioBackend(
        endpoint=os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        bucket=os.getenv("MINIO_BUCKET"),
        secure=False,
    )

def main():
    storage = create_storage_from_env()

    if not storage.bucket_exists():
        print("Bucket does not exist.")
        return

    load_day(storage, day = "2026/02/26/", model = "sp4_ep6_ft_noCEL_070126_26ep.engine")


if __name__ == "__main__":
    main()