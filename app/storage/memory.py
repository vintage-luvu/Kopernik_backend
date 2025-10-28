from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
from uuid import UUID

import pandas as pd

from app.schemas import ChartsResponse, PreviewResponse, SummaryResponse


@dataclass
class DatasetBundle:
    dataframe: pd.DataFrame
    summary: SummaryResponse
    charts: ChartsResponse
    preview: PreviewResponse


class InMemoryDatasetStore:
    def __init__(self) -> None:
        self._datasets: Dict[UUID, DatasetBundle] = {}

    def save_dataset(self, dataset_id: UUID, bundle: DatasetBundle) -> None:
        self._datasets[dataset_id] = bundle

    def get_dataset(self, dataset_id: UUID) -> DatasetBundle:
        try:
            return self._datasets[dataset_id]
        except KeyError as exc:
            raise KeyError("Dataset not found") from exc

    def dataset_exists(self, dataset_id: UUID) -> bool:
        return dataset_id in self._datasets
