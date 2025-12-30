from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware


APP_ROOT = Path(__file__).resolve().parent
WORDS_CSV_PATH = APP_ROOT / "fixed_words_with_uz.csv"


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


@lru_cache(maxsize=1)
def load_words() -> list[dict[str, Any]]:
    if not WORDS_CSV_PATH.exists():
        raise FileNotFoundError(f"Missing CSV file: {WORDS_CSV_PATH}")

    with WORDS_CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        items: list[dict[str, Any]] = []
        for idx, row in enumerate(reader, start=1):
            items.append(
                {
                    "id": idx,
                    "word": (row.get("word") or "").strip(),
                    "pronunciation": (row.get("pronunciation") or "").strip(),
                    "definition": (row.get("definition") or "").strip(),
                    "example": (row.get("example") or "").strip(),
                    "audio": (row.get("audio") or "").strip(),
                    "image": (row.get("image") or "").strip(),
                    "file": (row.get("file") or "").strip(),
                    "part_of_speech": (row.get("part_of_speech") or "").strip(),
                    "word_uz": (row.get("word_uz") or "").strip(),
                }
            )
        return items


app = FastAPI(title="Words API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"] ,
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/words/")
def get_words(
    q: str | None = Query(default=None, description="Search in word/definition/example/uz"),
    page: int | None = Query(default=None, ge=1, description="1-based page number"),
    limit: int | None = Query(default=None, ge=1, le=500, description="Items per page"),
) -> Any:
    """
    - If called with no query params, returns all words as a JSON array.
    - If any query param is provided (q/page/limit), returns a paginated response.
    """
    all_words = load_words()

    # Determine whether user wants pagination.
    wants_pagination = any(v is not None for v in (q, page, limit))

    filtered = all_words
    if q is not None and q.strip():
        needle = q.strip().lower()
        filtered = [
            item
            for item in all_words
            if needle in (item.get("word") or "").lower()
            or needle in (item.get("definition") or "").lower()
            or needle in (item.get("example") or "").lower()
            or needle in (item.get("word_uz") or "").lower()
            or needle in (item.get("part_of_speech") or "").lower()
        ]

    if not wants_pagination:
        return filtered

    # Pagination defaults when query params are present.
    page_value = page or 1
    limit_value = limit or 50
    total = len(filtered)
    start = (page_value - 1) * limit_value
    end = start + limit_value
    items = filtered[start:end]
    pages = (total + limit_value - 1) // limit_value if limit_value else 1

    return {
        "meta": {
            "total": total,
            "page": page_value,
            "limit": limit_value,
            "pages": pages,
            "q": q or "",
        },
        "items": items,
    }

