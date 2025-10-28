# Kopernik Backend

FastAPI application that ingests CSV datasets and exposes summaries for quick analysis.

## Development

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the API locally:

```bash
uvicorn app.main:app --reload
```

The primary endpoints are:

- `POST /upload` – Upload a CSV file (max 10MB) and receive a `dataset_id`.
- `GET /datasets/{dataset_id}/summary` – Retrieve dataset highlights for summary cards.
- `GET /datasets/{dataset_id}/charts` – Get chart-ready aggregations (category Top5 and daily trend).
- `GET /datasets/{dataset_id}/preview` – Fetch the first 20 rows with inferred column types for table previews.

Uploaded datasets are stored in-memory for the MVP.
