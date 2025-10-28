from __future__ import annotations

import io
from uuid import UUID, uuid4

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import ChartsResponse, PreviewResponse, SummaryResponse, UploadResponse
from app.services.analysis import analyze_dataset
from app.storage.memory import DatasetBundle, InMemoryDatasetStore

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


app = FastAPI(title="Kopernik Analytics API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


store = InMemoryDatasetStore()


def get_store() -> InMemoryDatasetStore:
    return store


@app.post("/upload", response_model=UploadResponse)
async def upload_dataset(
    file: UploadFile = File(..., description="CSV dataset"),
    store: InMemoryDatasetStore = Depends(get_store),
) -> UploadResponse:
    if file.content_type not in {"text/csv", "application/vnd.ms-excel", "application/csv"}:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a CSV file.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 10MB.")

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:  # pragma: no cover - pandas specific errors
        raise HTTPException(status_code=400, detail="Failed to parse CSV file.") from exc

    summary, charts, preview, _column_types = analyze_dataset(df)

    dataset_id = uuid4()
    bundle = DatasetBundle(dataframe=df, summary=summary, charts=charts, preview=preview)
    store.save_dataset(dataset_id, bundle)

    return UploadResponse(dataset_id=str(dataset_id))


@app.get("/datasets/{dataset_id}/summary", response_model=SummaryResponse)
def get_summary(
    dataset_id: UUID,
    store: InMemoryDatasetStore = Depends(get_store),
) -> SummaryResponse:
    bundle = _get_dataset_bundle(store, dataset_id)
    return bundle.summary


@app.get("/datasets/{dataset_id}/charts", response_model=ChartsResponse)
def get_charts(
    dataset_id: UUID,
    store: InMemoryDatasetStore = Depends(get_store),
) -> ChartsResponse:
    bundle = _get_dataset_bundle(store, dataset_id)
    return bundle.charts


@app.get("/datasets/{dataset_id}/preview", response_model=PreviewResponse)
def get_preview(
    dataset_id: UUID,
    store: InMemoryDatasetStore = Depends(get_store),
) -> PreviewResponse:
    bundle = _get_dataset_bundle(store, dataset_id)
    return bundle.preview


def _get_dataset_bundle(store: InMemoryDatasetStore, dataset_id: UUID) -> DatasetBundle:
    try:
        return store.get_dataset(dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Dataset not found.") from exc
