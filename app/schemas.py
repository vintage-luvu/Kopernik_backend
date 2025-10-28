from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    dataset_id: str = Field(..., description="Unique identifier for the uploaded dataset")


class TopCategorySummary(BaseModel):
    column: str
    value: str
    ratio: float


class SummaryResponse(BaseModel):
    row_count: int
    column_count: int
    latest_date: Optional[str] = None
    top_category: Optional[TopCategorySummary] = None
    missing_columns: List[str] = Field(default_factory=list)


class ChartDataPoint(BaseModel):
    label: str
    value: float


class ChartCategoryTop5(BaseModel):
    title: str
    x_label: str
    y_label: str
    data: List[ChartDataPoint]
    explanation: str


class ChartDatePoint(BaseModel):
    date: str
    count: int


class ChartByDate(BaseModel):
    title: str
    x_label: str
    y_label: str
    data: List[ChartDatePoint]
    explanation: str


class ChartsResponse(BaseModel):
    by_category_top5: Optional[ChartCategoryTop5] = None
    by_date: Optional[ChartByDate] = None


class PreviewColumn(BaseModel):
    name: str
    type: str


class PreviewResponse(BaseModel):
    columns: List[PreviewColumn]
    rows: List[List[Optional[str]]]
