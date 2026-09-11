"""Authentication and role-profile helpers."""

from __future__ import annotations

from typing import Any


def get_user_id(user: Any) -> str | None:
    """Return a Supabase user's UUID."""
    if isinstance(user, dict):
        return user.get("id")
    return getattr(user, "id", None)


def load_user_profile(supabase: Any, user_id: str) -> dict:
    """Load the active FactoryOps profile for an authenticated user."""
    response = (
        supabase
        .table("user_profiles")
        .select(
            "user_id,display_name,role,department_id,active"
        )
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    profiles = response.data or []

    if not profiles:
        raise PermissionError(
            "Your account has no FactoryOps profile. "
            "Ask an administrator to assign your role."
        )

    profile = profiles[0]

    if not profile.get("active", False):
        raise PermissionError(
            "Your FactoryOps account is inactive. "
            "Contact an administrator."
        )

    return profile


def role_label(role: str | None) -> str:
    """Convert an internal role name into a readable label."""
    if not role:
        return "Unassigned"

    return role.replace("_", " ").title()
