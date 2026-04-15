import json
import numpy as np
import cv2
import argparse
import os
from io import BytesIO
from datetime import datetime

from data_loader import StorageBackend
from minio_backend import MinioBackend


# ENV variables import
from dotenv import load_dotenv
load_dotenv()



def _load_json(raw_bytes):
    return json.loads(raw_bytes.decode("utf-8"))


def _load_npy_from_bytes(raw_bytes):
    return np.load(BytesIO(raw_bytes))


def _encode_png_hex(image):
    success, buffer = cv2.imencode(".png", image)
    if not success:
        raise RuntimeError("PNG encoding failed")
    return buffer.tobytes().hex()


def _parse_timestamp_ns(ts_str):
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1e9)


def build_fake_reid_messages(storage, day: str, model: str, limit=None):
    """
    Convert MinIO day data into mock ReID messages.
    Output matches expected broker payload schema.
    """

    messages = []
    prefix = f"analysis/{day}"

    for i, obj_key in enumerate(storage.list_objects(prefix)):
        if limit and i >= limit:
            break

        try:
            sighting = _load_json(storage.get_object(obj_key))

            # --- basic fields ---
            dupe_bool = sighting["duplicate"]
            size_bool = sighting["adequate_size"]
            daytime_bool = sighting["daytime"]

            if dupe_bool == False and size_bool == True and daytime_bool == True:

                camera_id = sighting["camera_id"]
                track_id = sighting["track_id"]  # keep int
                timestamp_ns = sighting.get("timestamp_ns") or _parse_timestamp_ns(
                    sighting["timestamp_utc"]
                )

                # --- embedding ---
                emb_info = sighting["embeddings"][model]
                emb_bytes = storage.get_object(emb_info["path"])
                embedding = _load_npy_from_bytes(emb_bytes)

                # enforce format consistency
                embedding = embedding.astype(np.float32)
                if embedding.ndim != 1:
                    raise ValueError(f"Embedding not 1D: shape={embedding.shape}")

                embedding = embedding.tolist()

                # --- cropped image (already cropped) ---
                img_bytes = storage.get_object(sighting["image_path"])
                img_np = np.frombuffer(img_bytes, dtype=np.uint8)
                image = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

                if image is None:
                    raise ValueError(f"Failed to decode image: {sighting['image_path']}")

                crop_hex = _encode_png_hex(image)

                # --- final message ---
                msg = {
                    "camera_id": camera_id,
                    "track_id": track_id,
                    "timestamp": timestamp_ns,
                    "bbox": None,  # explicitly absent
                    "embedding": embedding,
                    "cropped_image": crop_hex,
                }

                messages.append(msg)

        except Exception as e:
            print(f"[ERROR] {obj_key}: {e}")
            continue

    return messages

def save_messages_jsonl(messages, out_path):
    with open(out_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Build fake ReID stream from MinIO data")

    parser.add_argument("--day", default="2026/02/12", help="Day in format YYYY/MM/DD")
    parser.add_argument("--model", default="sp4_ep6_ft_noCEL_070126_26ep.engine", help="Embedding model name")
    parser.add_argument("--output", default="MinIO_toJSONL/2026/02/12.jsonl", help="Output JSONL file path")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for debugging")
    parser.add_argument("--store-key", default=None, help="Optional MinIO key to store result")

    args = parser.parse_args()

    # --- init your storage backend here ---
    # Replace this with your actual implementation
    storage = create_storage_from_env()

    print(f"[INFO] Building fake stream for day={args.day}, model={args.model}")

    messages = build_fake_reid_messages(
        storage=storage,
        day=args.day,
        model=args.model,
        limit=args.limit
    )

    print(f"[INFO] Generated {len(messages)} messages")

    # --- save locally (JSONL) ---
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    with open(args.output, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    print(f"[INFO] Saved to {args.output}")

    # --- optionally store back to MinIO ---
    if args.store_key:
        print(f"[INFO] Uploading to storage: {args.store_key}")

        # store as bytes
        payload = "\n".join(json.dumps(m) for m in messages).encode("utf-8")
        storage.put_object(args.store_key, payload)

        print("[INFO] Upload complete")


def create_storage_from_env() -> StorageBackend:
    # Tailor the values to your MinIO credentials
    return MinioBackend(
        endpoint=os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        bucket=os.getenv("MINIO_BUCKET"),
        secure=False,
    )


if __name__ == "__main__":
    main()