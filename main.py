import argparse
import os
from datetime import datetime, timedelta

from enrichment.event_enricher import EnrichmentPipeline
from MinioLogic import MinioBackend

# ---------------- CONFIG ----------------
from credentials_config import config


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", help="YYYY-MM-DD (optional)")

    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")

    parser.add_argument("--limit", type=int, default=None)

    parser.add_argument("--enable-lpr", action="store_true")

    return parser.parse_args()

def generate_days(start_date_str, end_date_str=None):
    start = datetime.strptime(start_date_str, "%Y-%m-%d")

    if end_date_str:
        end = datetime.strptime(end_date_str, "%Y-%m-%d")
    else:
        end = start # single day mode

    d = start
    while d <= end:
        yield d.strftime("%Y/%m/%d")
        d += timedelta(days=1)

def create_storage():
    return MinioBackend(
        endpoint=config.minio_endpoint,
        access_key=config.minio_access_key,
        secret_key=config.minio_secret_key,
        bucket=config.minio_bucket,
        secure=config.minio_secure,
    )

def check_minio(storage):
    print("[TEST] MinIO connection...")

    try:
        if not storage.bucket_exists():
            raise RuntimeError("Bucket does not exist")

        # lightweight sanity check
        test_iter = storage.list_objects("", max_keys=1)
        first = next(test_iter, None)

        print("[OK] MinIO reachable")
        if first:
            print(f"[OK] Sample object: {first}")
        else:
            print("[OK] Bucket is empty")

    except Exception as e:
        print(f"[ERROR] MinIO connection failed: {e}")
        raise


def main():
    args = parse_args()

    storage = create_storage()

    # ✅ MinIO check
    check_minio(storage)

    pipeline = EnrichmentPipeline(
        storage=storage,
        enable_lpr=args.enable_lpr,
        skip_existing=args.skip_existing,
        dry_run=args.dry_run,
        limit=args.limit,
    )

    days = list(generate_days(args.start_date, args.end_date))

    print(f"[Enrichment] Processing days: {days}")
    print(f"[Config] LPR={args.enable_lpr} dry_run={args.dry_run} skip_existing={args.skip_existing}")

    pipeline.run(days)

if __name__ == "__main__":
    main()