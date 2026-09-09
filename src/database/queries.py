"""Small, defensive query helpers shared by the manager and entry apps."""

from __future__ import annotations

from typing import Any

import pandas as pd


def fetch_table(client: Any, table_name: str, limit: int | None = None) -> pd.DataFrame:
    """Return a table as a DataFrame; missing optional tables become empty."""
    try:
        query = client.table(table_name).select("*")
        if limit:
            query = query.limit(limit)
        response = query.execute()
        return pd.DataFrame(response.data or [])
    except Exception:
        return pd.DataFrame()


def recent_rows(
    client: Any,
    table_name: str,
    date_column: str,
    limit: int = 25,
) -> pd.DataFrame:
    """Load recent rows when the table supports the requested date column."""
    try:
        response = (
            client.table(table_name)
            .select("*")
            .order(date_column, desc=True)
            .limit(limit)
            .execute()
        )
        return pd.DataFrame(response.data or [])
    except Exception:
        return fetch_table(client, table_name, limit=limit)


def lookup_options(
    client: Any,
    table_name: str,
    label_column: str = "name",
    active_only: bool = True,
) -> pd.DataFrame:
    """Return lookup rows sorted for human-friendly selectboxes."""
    frame = fetch_table(client, table_name)
    if frame.empty:
        return frame
    if active_only and "active" in frame.columns:
        frame = frame[frame["active"].fillna(True).astype(bool)]
    if label_column in frame.columns:
        frame = frame.sort_values(label_column, na_position="last")
    return frame.reset_index(drop=True)
