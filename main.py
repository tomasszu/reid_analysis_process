import os
from datetime import datetime, timedelta

from minio_backend import MinioBackend
from data_loader import StorageBackend, load_sightings_day, save_analysis_sighting, load_analysis_day, update_analysis

from tracking_correction.size_and_static_corrections import StaticVehicleCorrector
from tracking_correction.daytime_check import DaylightFilter

from license_plate_detection.lpr_annotator import LPRAnnotator

# ENV variables import
from dotenv import load_dotenv
load_dotenv()


# Parsing args nneds to be implemented here
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


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
    
    #initialize size and static detections corrector
    corrector = StaticVehicleCorrector(storage)

    #initialize daylight filter
    daylight_filter = DaylightFilter(
        latitude=56.98,
        longitude=24.19,
        timezone="Europe/Riga"
    )

    lpr_annotator = LPRAnnotator(storage)

    # We loop through the days in the dataset and load the data for each day.
    #date of first and last recording that would be in the dataset, adjust as needed
    start_date = datetime.fromisoformat("2026-02-12")
    end_date = datetime.today()  # or provide explicitly

    current = start_date
    candidate_days = []

    while current <= end_date:
        candidate_days.append(current.strftime("%Y/%m/%d"))
        current += timedelta(days=1)

    for day_str in candidate_days:

        # <<<<<<<<<<<<<<<<<<<<<<<< Load Sightings >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        # cheap existence check
        # objects = list(storage.list_objects(f"sightings/{day_str}", recursive=False, max_keys=1))
        # if not objects:
        #     continue

        # # Load all sighting JSONs for that day
        # sightings = load_sightings_day(storage, day_str)

        # # Mark adequate_size and duplicate
        # corr_sightings = corrector.mark_sightings(sightings)

        # # Save augmented JSONs to analysis/

        # for sighting in corr_sightings:
        #     save_analysis_sighting(storage, sighting)

        # <<<<<<<<<<<<<<<<<<<<<<<<<<< Load Analysis >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

        objects = list(storage.list_objects(f"analysis/{day_str}", recursive=False, max_keys=1))
        if not objects:
            continue

        # # Load all analysis JSONs for that day
        analysies = load_analysis_day(storage, day_str)

        # analysies = daylight_filter.mark_daytime(analysies)

        if lpr_annotator.run_test():
            lpr_annotator.process(analysies)
        else:
            print("Skipping License Plate recognition, models not working properly.")



        # save back to analysis/

        for a in analysies:
            update_analysis(storage, a)






            

        # Save augmented JSONs under analysis/
        #save_augmented_rows(storage, rows)

    

    #load_day(storage, day = "2026/02/26/", model = "sp4_ep6_ft_noCEL_070126_26ep.engine")


if __name__ == "__main__":
    main()


## Using the sightings

# sightings = load_sightings_day(storage, "2026/02/26")

# for sighting in sightings:
#     # Access original fields
#     vehicle_id = sighting.data["vehicle_id"]
#     timestamp = sighting.data["timestamp_utc"]

#     # Example augmentation
#     sighting.data["lpr_plate"] = lpr_processor.recognize_plate(sighting.data["image_path"])

#     # Save back to analysis/
#     save_analysis_json(storage, sighting.data, sighting.obj_key)


## Optional flattening helper

# def flatten_sightings_for_embeddings(sightings):
#     rows = []
#     for sighting in sightings:
#         for model_name, emb_info in sighting.data["embeddings"].items():
#             rows.append({
#                 "sighting_id": sighting.data["sighting_id"],
#                 "timestamp_utc": sighting.data["timestamp_utc"],
#                 "camera_id": sighting.data["camera_id"],
#                 "track_id": sighting.data["track_id"],
#                 "vehicle_id": sighting.data["vehicle_id"],
#                 "image_path": sighting.data["image_path"],
#                 "model_name": model_name,
#                 "embedding_path": emb_info["path"],
#                 "embedding_dim": emb_info["dim"],
#                 "embedding_normalized": emb_info["normalized"]
#             })
#     return rows