from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.schemas import (
    ChartCategoryTop5,
    ChartDataPoint,
    ChartByDate,
    ChartDatePoint,
    ChartsResponse,
    PreviewColumn,
    PreviewResponse,
    SummaryResponse,
    TopCategorySummary,
)

DATE_THRESHOLD = 0.5
NUMBER_THRESHOLD = 0.7
CATEGORY_MAX_UNIQUE = 50
CATEGORY_RATIO_THRESHOLD = 0.4
MAX_PREVIEW_ROWS = 20
MAX_TEXT_LENGTH = 200
MISSING_RATIO_THRESHOLD = 0.3


def _safe_string(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    text = str(value)
    if len(text) > MAX_TEXT_LENGTH:
        return text[:MAX_TEXT_LENGTH] + "…"
    return text


def infer_column_type(series: pd.Series) -> str:
    if series.empty:
        return "text"

    non_null = series.dropna()
    if non_null.empty:
        return "text"

    sample = non_null.head(200)

    # Try date
    parsed_dates = pd.to_datetime(sample, errors="coerce", infer_datetime_format=True)
    if parsed_dates.notna().mean() >= DATE_THRESHOLD:
        return "date"

    # Try numeric
    numeric = pd.to_numeric(sample, errors="coerce")
    if numeric.notna().mean() >= NUMBER_THRESHOLD:
        return "number"

    # Category: relatively few unique values and short strings
    if sample.dtype == object or pd.api.types.is_string_dtype(sample):
        unique_count = sample.nunique(dropna=True)
        avg_length = sample.astype(str).str.len().mean()
        if unique_count <= CATEGORY_MAX_UNIQUE and avg_length <= 50:
            return "category"

    return "text"


def infer_column_types(df: pd.DataFrame) -> Dict[str, str]:
    return {column: infer_column_type(df[column]) for column in df.columns}


def compute_summary(
    df: pd.DataFrame,
    column_types: Dict[str, str],
) -> SummaryResponse:
    row_count, column_count = df.shape

    latest_date = _find_latest_date(df, column_types)
    top_category_summary = _find_top_category(df, column_types)
    missing_columns = _find_missing_columns(df)

    return SummaryResponse(
        row_count=row_count,
        column_count=column_count,
        latest_date=latest_date,
        top_category=top_category_summary,
        missing_columns=missing_columns,
    )


def _find_latest_date(df: pd.DataFrame, column_types: Dict[str, str]) -> Optional[str]:
    date_columns = [col for col, col_type in column_types.items() if col_type == "date"]
    if not date_columns:
        return None

    max_value: Optional[pd.Timestamp] = None
    for column in date_columns:
        parsed = pd.to_datetime(df[column], errors="coerce")
        column_max = parsed.max()
        if pd.isna(column_max):
            continue
        if max_value is None or column_max > max_value:
            max_value = column_max

    if max_value is None:
        return None

    if isinstance(max_value, pd.Timestamp):
        return max_value.normalize().isoformat()

    return str(max_value)


def _find_top_category(
    df: pd.DataFrame, column_types: Dict[str, str]
) -> Optional[TopCategorySummary]:
    category_columns = [col for col, col_type in column_types.items() if col_type == "category"]
    if not category_columns:
        return None

    selected_column = _select_best_category_column(df, category_columns)
    if selected_column is None:
        return None

    counts = df[selected_column].dropna()
    if counts.empty:
        return None

    counts = counts.astype(str).value_counts()
    if counts.empty:
        return None

    top_label = counts.index[0]
    top_count = counts.iloc[0]
    ratio = float(top_count / counts.sum())

    return TopCategorySummary(column=selected_column, value=str(top_label), ratio=ratio)


def _select_best_category_column(df: pd.DataFrame, category_columns: List[str]) -> Optional[str]:
    if not category_columns:
        return None

    best_column = None
    best_score = -math.inf
    for column in category_columns:
        counts = df[column].dropna()
        if counts.empty:
            continue

        counts = counts.astype(str).value_counts()
        unique_count = len(counts)
        if unique_count == 0:
            continue

        top_ratio = counts.iloc[0] / counts.sum()
        score = unique_count - (top_ratio * 2)  # prefer spread-out distributions
        if score > best_score:
            best_score = score
            best_column = column

    return best_column


def _find_missing_columns(df: pd.DataFrame) -> List[str]:
    if df.empty:
        return []
    ratios = df.isna().mean()
    missing_columns = [col for col, ratio in ratios.items() if ratio >= MISSING_RATIO_THRESHOLD]
    return missing_columns


def compute_charts(df: pd.DataFrame, column_types: Dict[str, str]) -> ChartsResponse:
    category_chart = _build_category_top5_chart(df, column_types)
    date_chart = _build_date_chart(df, column_types)

    return ChartsResponse(by_category_top5=category_chart, by_date=date_chart)


def _build_category_top5_chart(
    df: pd.DataFrame, column_types: Dict[str, str]
) -> Optional[ChartCategoryTop5]:
    category_columns = [col for col, col_type in column_types.items() if col_type == "category"]
    if not category_columns:
        return None

    selected_column = _select_best_category_column(df, category_columns)
    if selected_column is None:
        return None

    counts = df[selected_column].dropna()
    if counts.empty:
        return None

    counts = counts.astype(str).value_counts().head(5)
    if counts.empty:
        return None

    data = [ChartDataPoint(label=str(label), value=int(count)) for label, count in counts.items()]

    return ChartCategoryTop5(
        title=f"{selected_column}別の件数Top5",
        x_label=selected_column,
        y_label="件数",
        data=data,
        explanation="主要カテゴリ別の件数上位です。数が多いほど関心が集中しています。",
    )


def _build_date_chart(df: pd.DataFrame, column_types: Dict[str, str]) -> Optional[ChartByDate]:
    date_columns = [col for col, col_type in column_types.items() if col_type == "date"]
    if not date_columns:
        return None

    selected_column = date_columns[0]
    parsed = pd.to_datetime(df[selected_column], errors="coerce")
    parsed = parsed.dropna()
    if parsed.empty:
        return None

    # Group by day and count
    grouped = parsed.dt.floor("D").value_counts().sort_index()
    data = [
        ChartDatePoint(date=index.date().isoformat(), count=int(count))
        for index, count in grouped.items()
    ]

    return ChartByDate(
        title=f"{selected_column}単位の日次推移",
        x_label="日付",
        y_label="件数",
        data=data,
        explanation="日付ごとの件数推移です。増減から傾向を把握できます。",
    )


def compute_preview(df: pd.DataFrame, column_types: Dict[str, str]) -> PreviewResponse:
    preview_df = df.head(MAX_PREVIEW_ROWS)

    columns = [PreviewColumn(name=col, type=column_types.get(col, "text")) for col in preview_df.columns]

    rows: List[List[Optional[str]]] = []
    for _, row in preview_df.iterrows():
        serialized_row = [_safe_string(row[col]) for col in preview_df.columns]
        rows.append(serialized_row)

    return PreviewResponse(columns=columns, rows=rows)


def analyze_dataset(df: pd.DataFrame) -> Tuple[SummaryResponse, ChartsResponse, PreviewResponse, Dict[str, str]]:
    column_types = infer_column_types(df)
    summary = compute_summary(df, column_types)
    charts = compute_charts(df, column_types)
    preview = compute_preview(df, column_types)
    return summary, charts, preview, column_types
