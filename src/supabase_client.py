"""Supabase client factory for both Streamlit applications."""

from __future__ import annotations

from typing import Any


def create_supabase_from_secrets(secrets: Any):
    from supabase import create_client

    url = secrets.get("SUPABASE_URL")
    key = secrets.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Add SUPABASE_URL and SUPABASE_KEY under Streamlit Cloud App Settings → Secrets."
        )
    return create_client(url, key)
