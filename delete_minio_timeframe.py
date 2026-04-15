from minio import Minio
from datetime import datetime, timezone
from minio_backend import MinioBackend
from data_loader import StorageBackend
import os

# ENV variables import
from dotenv import load_dotenv
load_dotenv()

# Create raw MinIO client
client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)

bucket_name = os.getenv("MINIO_BUCKET")

# Timeframe (UTC)
from_datetime = datetime(2026, 3, 18, 0, 0, tzinfo=timezone.utc)
to_datetime   = datetime(2026, 3, 18, 23, 59, 59, tzinfo=timezone.utc)

# Gather objects in timeframe
objects_to_delete = [
    obj.object_name
    for obj in client.list_objects(bucket_name, recursive=True)
    if from_datetime <= obj.last_modified <= to_datetime
]

# Delete individually
if objects_to_delete:
    print(f"Found {len(objects_to_delete)} objects to delete:")
    for obj_name in objects_to_delete:
        client.remove_object(bucket_name, obj_name)
        print(f"Deleted {obj_name}")
else:
    print("No objects found in the specified timeframe")