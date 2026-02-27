# Analysis Service Layer

```
reid_analysis/
    ├── data_loader.py
    ├── index_builder.py
    ├── reidentifier.py
    ├── lpr_module.py
    ├── time_constraint_module.py
    ├── run_experiment.py

```

## Aim:

* connects to MinIO
* loads data
* builds temporary vector index (FAISS / sklearn)
* analyses sightings / tracks
* assigns vehicle IDs
* writes updated JSONs back

## Components:

### Data Loader


