"""
Data Lens V2 — Backend API
==========================

FastAPI application that connects the Data Lens frontend (index.html,
script.js, style.css) with the analysis modules in this folder:

    data_overview.py   data_preview.py   data_quality.py
    data_cleaning.py   data_viz.py       statistical.py

Run (from the backend folder)
-----------------------------
    pip install -r requirements.txt
    python main.py                      # or: uvicorn main:app --reload

    API docs  ->  http://127.0.0.1:8000/docs
    Frontend  ->  http://127.0.0.1:8000/   (served from ../frontend if present)

Endpoints used by the frontend
------------------------------
    POST   /api/upload        Upload CSV / XLSX / XLS
    GET    /api/overview      Dataset snapshot
    GET    /api/preview       Search, filter, sort and paginate records
    GET    /api/quality       Completeness, missing values, duplicates
    POST   /api/clean         Apply a cleaning operation
    GET    /api/export        Download the cleaned dataset (CSV / Excel)
    POST   /api/visualize     Render a chart as PNG
    GET    /api/statistics    Descriptive statistics for a numeric column

Extra endpoints
---------------
    GET    /api/health        Service status
    POST   /api/reset         Restore the original uploaded dataset
    DELETE /api/dataset/{id}  Remove a dataset from server memory
    GET    /api/correlation   Correlation matrix
    GET    /api/outliers      IQR outliers for a numeric column
    GET    /api/frequency     Value counts for a column

Configuration (all optional, via environment variables)
-------------------------------------------------------
    DATA_LENS_HOST, DATA_LENS_PORT, DATA_LENS_RELOAD
    DATA_LENS_CORS_ORIGINS        comma separated, default "*"
    DATA_LENS_MAX_UPLOAD_MB       default 50
    DATA_LENS_SESSION_MINUTES     default 120
    DATA_LENS_MAX_DATASETS        default 25
    DATA_LENS_LOG_LEVEL           default INFO
"""

import asyncio
import csv
import io
import json
import logging
import math
import os
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional
from urllib.parse import quote

# Matplotlib must use a headless backend *before* pyplot is imported
# (data_viz.py imports pyplot at module level).
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import APIRouter, FastAPI, File, Query, Request, UploadFile  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import data_cleaning as cleaning  # noqa: E402
import data_overview as overview  # noqa: E402
import data_preview as preview_tools  # noqa: E402
import data_quality as quality  # noqa: E402
import data_viz as viz  # noqa: E402
import statistical as stat  # noqa: E402


# ======================================
# 1. CONFIGURATION
# ======================================

def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    app_name = "Data Lens API"
    version = "2.0.0"

    host = os.getenv("DATA_LENS_HOST", "127.0.0.1")
    port = _env_int("DATA_LENS_PORT", 8000)
    reload = _env_bool("DATA_LENS_RELOAD", False)
    log_level = os.getenv("DATA_LENS_LOG_LEVEL", "INFO").upper()

    max_upload_mb = _env_int("DATA_LENS_MAX_UPLOAD_MB", 50)
    session_minutes = _env_int("DATA_LENS_SESSION_MINUTES", 120)
    max_datasets = _env_int("DATA_LENS_MAX_DATASETS", 25)

    cors_origins = [
        origin.strip()
        for origin in os.getenv("DATA_LENS_CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]

    frontend_dir = BASE_DIR.parent / "frontend"

    allowed_extensions = {".csv", ".xlsx", ".xls"}
    max_excel_rows = 1_048_575
    max_pie_categories = 30
    max_scatter_points = 20_000


settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("data_lens")


# ======================================
# 2. ERRORS
# ======================================

class APIError(Exception):
    """An expected, user-facing error. Always returned as {"detail": message}."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ======================================
# 3. IN-MEMORY DATASET STORE
# ======================================

@dataclass
class Dataset:
    file_id: str
    file_name: str
    original: pd.DataFrame
    working: pd.DataFrame
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    operations: List[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


class DatasetStore:
    """
    Thread-safe store for uploaded datasets.

    Each dataset keeps the untouched original plus a working copy, so cleaning
    operations accumulate and can be compared against (or reset to) the original.
    Datasets expire after a period of inactivity and the oldest are evicted
    when the store is full.
    """

    def __init__(self, ttl_seconds: int, max_datasets: int):
        self._items: Dict[str, Dataset] = {}
        self._lock = threading.RLock()
        self._ttl = ttl_seconds
        self._max = max_datasets

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    def add(self, file_name: str, df: pd.DataFrame) -> Dataset:
        with self._lock:
            self._purge_locked()

            while len(self._items) >= self._max:
                oldest = min(self._items.values(), key=lambda item: item.last_accessed)
                del self._items[oldest.file_id]
                logger.info("Evicted dataset %s (store full)", oldest.file_id)

            dataset = Dataset(
                file_id=uuid.uuid4().hex,
                file_name=file_name,
                original=df,
                working=df.copy(),
            )
            self._items[dataset.file_id] = dataset
            return dataset

    def get(self, file_id: str) -> Dataset:
        with self._lock:
            dataset = self._items.get(file_id)

            if dataset is None or self._is_expired(dataset):
                self._items.pop(file_id, None)
                raise APIError(
                    "Dataset not found or session expired. Please upload your file again.",
                    404,
                )

            dataset.last_accessed = time.time()
            return dataset

    def delete(self, file_id: str) -> bool:
        with self._lock:
            return self._items.pop(file_id, None) is not None

    def purge_expired(self) -> int:
        with self._lock:
            return self._purge_locked()

    def _is_expired(self, dataset: Dataset) -> bool:
        return (time.time() - dataset.last_accessed) > self._ttl

    def _purge_locked(self) -> int:
        expired = [key for key, item in self._items.items() if self._is_expired(item)]

        for key in expired:
            del self._items[key]

        return len(expired)


store = DatasetStore(
    ttl_seconds=settings.session_minutes * 60,
    max_datasets=settings.max_datasets,
)


# ======================================
# 4. SERIALIZATION HELPERS
# ======================================

def to_native(value: Any) -> Any:
    """
    Convert pandas / NumPy values into JSON-safe Python values.
    NaN and infinity become null so responses never fail to encode.
    """
    if value is None or value is pd.NA or value is pd.NaT:
        return None

    if isinstance(value, dict):
        return {str(key): to_native(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_native(item) for item in value]

    if isinstance(value, np.ndarray):
        return [to_native(item) for item in value.tolist()]

    if isinstance(value, (bool, np.bool_)):
        return bool(value)

    if isinstance(value, (int, np.integer)):
        return int(value)

    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None

    if isinstance(value, str):
        return value

    return str(value)


def frame_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """DataFrame -> list of JSON-safe dictionaries (dates as ISO strings)."""
    return json.loads(
        df.to_json(orient="records", date_format="iso", default_handler=str)
    )


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee unique, non-empty, string column names."""
    seen: Dict[str, int] = {}
    names = []

    for position, column in enumerate(df.columns, start=1):
        name = str(column).strip() or f"column_{position}"

        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0

        names.append(name)

    df.columns = names
    return df


def numeric_columns_of(df: pd.DataFrame) -> List[str]:
    return stat.get_numeric_columns(df)


def dataset_snapshot(df: pd.DataFrame) -> Dict[str, Any]:
    """Structure shared by upload, clean and reset responses."""
    return {
        "columns": overview.get_column_names(df),
        "numeric_columns": numeric_columns_of(df),
        "total_rows": overview.get_total_rows(df),
        "total_columns": overview.get_total_columns(df),
    }


# ======================================
# 5. FILE PARSING
# ======================================

def read_limited(upload: UploadFile) -> bytes:
    """Read an upload in chunks and stop as soon as it exceeds the size limit."""
    limit = settings.max_upload_mb * 1024 * 1024
    buffer = bytearray()

    while True:
        chunk = upload.file.read(1024 * 1024)

        if not chunk:
            break

        buffer.extend(chunk)

        if len(buffer) > limit:
            raise APIError(
                f"File is too large. The maximum size is {settings.max_upload_mb} MB.",
                413,
            )

    return bytes(buffer)


def read_csv(content: bytes) -> pd.DataFrame:
    sample = content[:16384].decode("utf-8", errors="ignore")

    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        delimiter = ","

    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(content), sep=delimiter, encoding=encoding)
        except UnicodeDecodeError:
            continue

    raise APIError("Unable to decode the CSV file. Please save it as UTF-8.", 400)


def parse_dataframe(content: bytes, extension: str) -> pd.DataFrame:
    if not content:
        raise APIError("The uploaded file is empty.", 400)

    try:
        if extension == ".csv":
            df = read_csv(content)
        elif extension == ".xlsx":
            df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
        else:
            df = pd.read_excel(io.BytesIO(content), engine="xlrd")

    except APIError:
        raise
    except ImportError as error:
        raise APIError(
            "Reading .xls files requires the 'xlrd' package "
            "(pip install xlrd). Alternatively, save the file as .xlsx.",
            400,
        ) from error
    except pd.errors.EmptyDataError as error:
        raise APIError("The uploaded file contains no data.", 400) from error
    except Exception as error:  # noqa: BLE001 - any parser failure is a bad file
        logger.warning("Could not parse upload: %s", error)
        raise APIError(
            "Could not read the file. Please make sure it is a valid CSV or Excel file.",
            400,
        ) from error

    if df.shape[1] == 0 or df.shape[0] == 0:
        raise APIError("The dataset has no rows or no columns.", 400)

    return normalise_columns(df)


# ======================================
# 6. CLEANING OPERATIONS
# ======================================

class CleanRequest(BaseModel):
    file_id: str
    operation: str
    column: Optional[str] = None
    columns: Optional[List[str]] = None
    value: Optional[str] = None


DTYPE_ALIASES = {
    "integer": "int64",
    "int": "int64",
    "float": "float64",
    "number": "float64",
    "string": "string",
    "str": "string",
    "text": "string",
    "boolean": "boolean",
    "bool": "boolean",
    "category": "category",
    "datetime": "datetime64[ns]",
    "date": "datetime64[ns]",
}


def _target_columns(df: pd.DataFrame, request: CleanRequest) -> Optional[List[str]]:
    """Columns chosen by the user (single `column` and/or a `columns` list)."""
    selected = list(request.columns or [])

    if request.column:
        selected.append(request.column)

    selected = list(dict.fromkeys(selected))
    invalid = [name for name in selected if name not in df.columns]

    if invalid:
        raise APIError(f"Unknown column(s): {', '.join(invalid)}", 400)

    return selected or None


def _require_columns(df: pd.DataFrame, request: CleanRequest) -> List[str]:
    targets = _target_columns(df, request)

    if not targets:
        raise APIError("Please select a column for this operation.", 400)

    return targets


def _numeric_targets(df: pd.DataFrame, request: CleanRequest) -> List[str]:
    targets = _target_columns(df, request)

    if targets is not None:
        return targets

    targets = [
        column for column in df.columns
        if pd.api.types.is_numeric_dtype(df[column])
        and not pd.api.types.is_bool_dtype(df[column])
    ]

    if not targets:
        raise APIError("This dataset has no numeric columns.", 400)

    return targets


def _coerce_fill_value(series: pd.Series, raw: str) -> Any:
    """Convert the typed-in fill value to the column's type."""
    if pd.api.types.is_bool_dtype(series):
        return raw

    if pd.api.types.is_numeric_dtype(series):
        number = float(raw)

        if pd.api.types.is_integer_dtype(series) and number.is_integer():
            return int(number)

        return number

    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.Timestamp(raw)

    return raw


def _op_drop_missing_rows(df, request):
    return cleaning.drop_missing_rows(df, _target_columns(df, request))


def _op_drop_missing_columns(df, request):
    return cleaning.drop_missing_columns(df)


def _op_fill_value(df, request):
    raw = request.value

    if raw is None or str(raw).strip() == "":
        raise APIError("Please enter a value to fill missing cells with.", 400)

    targets = _target_columns(df, request)
    explicit = targets is not None
    result = df

    for column in targets or list(df.columns):
        try:
            value = _coerce_fill_value(df[column], raw)
        except (ValueError, TypeError) as error:
            if explicit:
                raise APIError(
                    f"'{raw}' is not a valid value for column '{column}'.", 400
                ) from error
            continue  # applying to all columns: skip incompatible ones

        result = cleaning.fill_missing_with_value(result, value, [column])

    return result


def _op_fill_mean(df, request):
    return cleaning.fill_missing_with_mean(df, _numeric_targets(df, request))


def _op_fill_median(df, request):
    return cleaning.fill_missing_with_median(df, _numeric_targets(df, request))


def _op_fill_mode(df, request):
    targets = _target_columns(df, request) or list(df.columns)
    return cleaning.fill_missing_with_mode(df, targets)


def _op_remove_duplicate_rows(df, request):
    return cleaning.remove_duplicate_rows(df)


def _op_remove_duplicate_values(df, request):
    return cleaning.remove_duplicate_values(df, _require_columns(df, request))


def _op_drop_selected_columns(df, request):
    return cleaning.drop_selected_columns(df, _require_columns(df, request))


def _op_rename_column(df, request):
    targets = _require_columns(df, request)
    new_name = (request.value or "").strip()

    if len(targets) != 1:
        raise APIError("Select exactly one column to rename.", 400)

    if not new_name:
        raise APIError("Enter the new column name in the value field.", 400)

    if new_name in df.columns and new_name != targets[0]:
        raise APIError(f"A column named '{new_name}' already exists.", 400)

    return cleaning.rename_columns(df, {targets[0]: new_name})


def _op_change_data_type(df, request):
    targets = _require_columns(df, request)
    requested = (request.value or "").strip().lower()

    if len(targets) != 1:
        raise APIError("Select exactly one column to convert.", 400)

    if requested not in DTYPE_ALIASES:
        raise APIError(
            "Choose a data type: " + ", ".join(sorted(set(DTYPE_ALIASES))) + ".", 400
        )

    return cleaning.change_column_data_type(
        df, targets[0], DTYPE_ALIASES[requested]
    )


CLEANING_HANDLERS: Dict[str, Callable[[pd.DataFrame, CleanRequest], pd.DataFrame]] = {
    "drop_missing_rows": _op_drop_missing_rows,
    "drop_missing_columns": _op_drop_missing_columns,
    "fill_missing_with_value": _op_fill_value,
    "fill_missing_with_mean": _op_fill_mean,
    "fill_missing_with_median": _op_fill_median,
    "fill_missing_with_mode": _op_fill_mode,
    "remove_duplicate_rows": _op_remove_duplicate_rows,
    "remove_duplicate_values": _op_remove_duplicate_values,
    "drop_selected_columns": _op_drop_selected_columns,
    "rename_column": _op_rename_column,
    "change_data_type": _op_change_data_type,
}


# ======================================
# 7. VISUALIZATION
# ======================================

class VisualizeRequest(BaseModel):
    file_id: str
    chart_type: Literal[
        "bar", "line", "scatter", "histogram", "pie",
        "box", "area", "horizontal_bar", "heatmap",
    ]
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    title: Optional[str] = None
    bins: int = Field(default=10, ge=1, le=200)


# Matplotlib's pyplot interface keeps global state and is not thread-safe.
_PLOT_LOCK = threading.Lock()

TWO_COLUMN_CHARTS = {
    "bar": (viz.create_bar_chart, "{y} by {x}"),
    "line": (viz.create_line_chart, "{y} over {x}"),
    "scatter": (viz.create_scatter_plot, "{y} vs {x}"),
    "area": (viz.create_area_chart, "{y} over {x}"),
    "horizontal_bar": (viz.create_horizontal_bar_chart, "{y} by {x}"),
}


def render_chart(df: pd.DataFrame, request: VisualizeRequest) -> bytes:
    chart = request.chart_type
    x_column, y_column = request.x_column, request.y_column

    with _PLOT_LOCK:
        try:
            if chart in TWO_COLUMN_CHARTS:
                if not x_column or not y_column:
                    raise APIError(
                        "This chart needs both an X column and a numeric Y column.", 400
                    )

                builder, pattern = TWO_COLUMN_CHARTS[chart]
                title = request.title or pattern.format(x=x_column, y=y_column)
                data = df

                if chart == "scatter" and len(df) > settings.max_scatter_points:
                    data = df.sample(settings.max_scatter_points, random_state=42)

                figure = builder(data, x_column, y_column, title=title)

            elif chart in ("histogram", "box"):
                column = y_column or x_column

                if not column:
                    raise APIError("Please select a numeric column for this chart.", 400)

                if chart == "histogram":
                    figure = viz.create_histogram(
                        df, column, bins=request.bins,
                        title=request.title or f"Distribution of {column}",
                    )
                else:
                    figure = viz.create_box_plot(
                        df, column, title=request.title or f"Box plot of {column}"
                    )

            elif chart == "pie":
                column = x_column or y_column

                if not column:
                    raise APIError("Please select a category column for the pie chart.", 400)

                if column in df.columns and df[column].nunique() > settings.max_pie_categories:
                    raise APIError(
                        f"'{column}' has more than {settings.max_pie_categories} "
                        "categories. Try a bar chart instead.",
                        400,
                    )

                figure = viz.create_pie_chart(
                    df, column, title=request.title or f"Share of {column}"
                )

            else:  # heatmap
                figure = viz.create_correlation_heatmap(
                    df, title=request.title or "Correlation Heatmap"
                )

            buffer = io.BytesIO()
            figure.savefig(
            buffer,
            format="png",
            dpi=150,
            bbox_inches="tight",
            facecolor="white"
)

            image_bytes = buffer.getvalue()
            buffer.close()
            
            return image_bytes

        finally:
            plt.close("all")


# ======================================
# 8. API ROUTES
# ======================================

api = APIRouter(prefix="/api")


# ---------- System ----------

@api.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
        "datasets_loaded": len(store),
        "uptime_seconds": int(time.time() - APP_STARTED_AT),
    }


# ---------- Upload & dataset lifecycle ----------

@api.post("/upload", tags=["Dataset"])
def upload_dataset(file: UploadFile = File(...)):
    raw_name = (overview.get_file_name(file) or "dataset").replace("\\", "/")
    file_name = Path(raw_name).name or "dataset"
    extension = Path(file_name).suffix.lower()

    if extension not in settings.allowed_extensions:
        raise APIError("Unsupported file type. Please upload a CSV, XLSX or XLS file.", 415)

    df = parse_dataframe(read_limited(file), extension)
    dataset = store.add(file_name, df)

    logger.info(
        "Uploaded '%s' (%d rows x %d cols) as %s",
        file_name, len(df), df.shape[1], dataset.file_id,
    )

    return {
        "file_id": dataset.file_id,
        "file_name": dataset.file_name,
        "message": "Dataset uploaded successfully.",
        **to_native(dataset_snapshot(dataset.working)),
    }


@api.post("/reset", tags=["Dataset"])
def reset_dataset(file_id: str = Query(...)):
    dataset = store.get(file_id)

    with dataset.lock:
        dataset.working = dataset.original.copy()
        dataset.operations.clear()

    return {
        "message": "Dataset restored to its original state.",
        **to_native(dataset_snapshot(dataset.working)),
    }


@api.delete("/dataset/{file_id}", tags=["Dataset"])
def delete_dataset(file_id: str):
    if not store.delete(file_id):
        raise APIError("Dataset not found or already removed.", 404)

    return {"message": "Dataset removed."}


# ---------- Overview ----------

@api.get("/overview", tags=["Overview"])
def get_overview(file_id: str = Query(...)):
    dataset = store.get(file_id)
    df = dataset.working

    return to_native({
        "file_name": dataset.file_name,
        "total_rows": overview.get_total_rows(df),
        "total_columns": overview.get_total_columns(df),
        "total_entries": overview.get_total_entries(df),
        "total_missing_values": overview.get_total_missing_values(df),
        "total_duplicates": overview.get_total_duplicates(df),
        "column_names": overview.get_column_names(df),
        "column_data_types": overview.get_column_data_types(df),
        "cleaning_operations_applied": len(dataset.operations),
    })


# ---------- Preview ----------

@api.get("/preview", tags=["Preview"])
def get_preview(
    file_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=500),
    search: str = Query(""),
    column: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    order: Literal["asc", "desc"] = Query("asc"),
):
    """
    `column` focuses the view on one column: only that column is shown,
    and a search term is matched against it alone.
    """
    df = store.get(file_id).working
    term = search.strip()

    data = df

    if column:
        data = preview_tools.get_selected_columns(df, [column])

    if term:
        data = (
            preview_tools.search_column(data, column, term)
            if column
            else preview_tools.search_records(data, term)
        )

    if sort_by:
        data = preview_tools.sort_data(data, sort_by, ascending=(order == "asc"))

    total_records = len(data)
    total_pages = max(1, math.ceil(total_records / page_size))
    page = min(page, total_pages)

    page_data = preview_tools.get_paginated_data(data, page, page_size)

    return {
        "columns": [str(name) for name in page_data.columns],
        "records": frame_to_records(page_data),
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
    }


# ---------- Data quality ----------

@api.get("/quality", tags=["Quality"])
def get_quality(file_id: str = Query(...)):
    return to_native(quality.get_data_quality_summary(store.get(file_id).working))


# ---------- Cleaning & export ----------

@api.post("/clean", tags=["Cleaning"])
def clean_dataset(request: CleanRequest):
    handler = CLEANING_HANDLERS.get(request.operation)

    if handler is None:
        raise APIError(
            f"Unsupported operation '{request.operation}'. "
            f"Available: {', '.join(CLEANING_HANDLERS)}.",
            400,
        )

    dataset = store.get(request.file_id)

    with dataset.lock:
        before_rows, before_cols = dataset.working.shape

        try:
            result = handler(dataset.working, request)
        except (TypeError, KeyError) as error:
            raise APIError(f"The operation could not be applied: {error}", 400) from error

        if result.shape[0] == 0 or result.shape[1] == 0:
            raise APIError(
                "This operation would remove all rows or all columns, "
                "so it was not applied.",
                400,
            )

        dataset.working = result.reset_index(drop=True)
        dataset.operations.append(request.operation)
        summary = cleaning.get_cleaning_summary(dataset.original, dataset.working)

        removed_rows = before_rows - dataset.working.shape[0]
        removed_cols = before_cols - dataset.working.shape[1]

    logger.info(
        "Dataset %s: %s (-%d rows, -%d columns)",
        request.file_id, request.operation, removed_rows, removed_cols,
    )

    return {
        "message": "Cleaning operation completed.",
        "operation": request.operation,
        "summary": to_native(summary),
        "changes": {"rows_removed": removed_rows, "columns_removed": removed_cols},
        **to_native(dataset_snapshot(dataset.working)),
    }


EXPORT_MEDIA_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@api.get("/export", tags=["Cleaning"])
def export_dataset(
    file_id: str = Query(...),
    file_format: str = Query("csv", alias="format"),
):
    export_format = file_format.strip().lower()
    export_format = "xlsx" if export_format in {"xlsx", "excel"} else export_format

    if export_format not in EXPORT_MEDIA_TYPES:
        raise APIError("Supported export formats are CSV and Excel (xlsx).", 400)

    dataset = store.get(file_id)
    df = dataset.working

    if export_format == "xlsx" and len(df) > settings.max_excel_rows:
        raise APIError("Too many rows for an Excel file. Please export as CSV.", 400)

    buffer = cleaning.export_cleaned_data(df, export_format)

    stem = Path(dataset.file_name).stem or "dataset"
    download_name = f"{stem}_cleaned.{export_format}"

    return Response(
        content=buffer.getvalue(),
        media_type=EXPORT_MEDIA_TYPES[export_format],
        headers={
            "Content-Disposition": (
                f'attachment; filename="cleaned_data.{export_format}"; '
                f"filename*=UTF-8''{quote(download_name)}"
            ),
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


# ---------- Visualization ----------

@api.post("/visualize", tags=["Visualization"])
def visualize(request: VisualizeRequest):
    df = store.get(request.file_id).working

    if request.chart_type == "heatmap":
        print("\n--- HEATMAP DEBUG ---")
        print("Dataset columns:")
        print(df.dtypes)

        print("\nNumeric columns:")
        print(df.select_dtypes(include="number").columns.tolist())

        print("\nUnique numeric values:")
        print(df.select_dtypes(include="number").nunique())

    image = render_chart(df, request)

    return Response(
        content=image,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


# ---------- Statistics ----------

@api.get("/statistics", tags=["Statistics"])
def get_statistics(file_id: str = Query(...), column: str = Query(...)):
    df = store.get(file_id).working

    return {
        "column": column,
        **to_native(stat.get_descriptive_statistics(df, column)),
    }


@api.get("/correlation", tags=["Statistics"])
def get_correlation(
    file_id: str = Query(...),
    method: Literal["pearson", "spearman", "kendall"] = Query("pearson"),
):
    df = store.get(file_id).working

    return {
        "method": method,
        "matrix": to_native(stat.get_correlation_matrix(df, method=method)),
    }


@api.get("/outliers", tags=["Statistics"])
def get_outliers(
    file_id: str = Query(...),
    column: str = Query(...),
    limit: int = Query(100, ge=1, le=1000),
):
    df = store.get(file_id).working
    outliers = stat.detect_outliers_iqr(df, column)

    return {
        "column": column,
        "outlier_count": len(outliers),
        "outlier_percentage": round(len(outliers) / len(df) * 100, 2) if len(df) else 0.0,
        "records": frame_to_records(outliers.head(limit)),
    }


@api.get("/frequency", tags=["Statistics"])
def get_frequency(
    file_id: str = Query(...),
    column: str = Query(...),
    limit: int = Query(50, ge=1, le=500),
):
    df = store.get(file_id).working
    counts = stat.get_frequency_distribution(df, column)
    top = list(counts.items())[:limit]

    return {
        "column": column,
        "distinct_values": len(counts),
        "frequencies": [
            {"value": to_native(value), "count": int(count)} for value, count in top
        ],
    }


# ======================================
# 9. APPLICATION FACTORY
# ======================================

APP_STARTED_AT = time.time()


async def _janitor() -> None:
    """Periodically free memory held by expired datasets."""
    while True:
        await asyncio.sleep(300)
        removed = store.purge_expired()

        if removed:
            logger.info("Janitor removed %d expired dataset(s)", removed)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_janitor())

    logger.info(
        "%s v%s ready | upload limit %d MB | session %d min",
        settings.app_name, settings.version,
        settings.max_upload_mb, settings.session_minutes,
    )

    try:
        yield
    finally:
        task.cancel()

        with suppress(asyncio.CancelledError):
            await task


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=(
            "Backend for Data Lens — upload, explore, assess, clean, "
            "visualize and analyze tabular datasets."
        ),
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    # ----- Request timing & access log -----
    @application.middleware("http")
    async def timing_middleware(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000

        response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.1f}"

        if request.url.path.startswith("/api"):
            logger.info(
                "%s %s -> %d (%.0f ms)",
                request.method, request.url.path, response.status_code, elapsed_ms,
            )

        return response

    # ----- Error handling: every error is {"detail": "<readable message>"} -----
    # script.js displays `error.detail`, so it must always be a plain string.
    @application.exception_handler(APIError)
    async def handle_api_error(request: Request, error: APIError):
        return JSONResponse({"detail": error.message}, status_code=error.status_code)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError):
        messages = []

        for item in error.errors():
            location = ".".join(
                str(part) for part in item.get("loc", ())
                if part not in ("body", "query", "path")
            )
            messages.append(f"{location}: {item['msg']}" if location else item["msg"])

        return JSONResponse(
            {"detail": "; ".join(messages) or "Invalid request."}, status_code=422
        )

    @application.exception_handler(ValueError)
    async def handle_value_error(request: Request, error: ValueError):
        # The analysis modules raise ValueError for invalid user input
        # (unknown column, non-numeric column, no valid data, ...).
        return JSONResponse({"detail": str(error)}, status_code=400)

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            {"detail": "An unexpected server error occurred."}, status_code=500
        )

    application.include_router(api)

    # ----- Serve the frontend (must be mounted last) -----
    if settings.frontend_dir.is_dir():
        application.mount(
            "/",
            StaticFiles(directory=settings.frontend_dir, html=True),
            name="frontend",
        )
    else:

        @application.get("/", include_in_schema=False)
        def root():
            return {
                "app": settings.app_name,
                "version": settings.version,
                "docs": "/docs",
                "health": "/api/health",
            }

    return application


app = create_app()


# ======================================
# 10. ENTRY POINT
# ======================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
