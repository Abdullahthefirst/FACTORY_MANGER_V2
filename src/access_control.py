"""FactoryOps role-based navigation."""

from __future__ import annotations

ALL_MANAGER_PAGES = [
    "📊 Overview",
    "🤖 AI Center",
    "📈 Reports & Alerts",
    "📦 Orders & Demand",
    "🏭 Production",
    "📦 Inventory & Supply",
    "⚙️ Machines & Maintenance",
    "✅ Quality",
    "👥 Workforce",
    "🚚 Logistics",
    "💰 Costs",
    "🛡️ Safety & Risk",
]

ROLE_PAGES = {
    "system_admin": ALL_MANAGER_PAGES,
    "general_manager": ALL_MANAGER_PAGES,
    "production_manager": [
        "🏭 Production",
        "📦 Orders & Demand",
        "⚙️ Machines & Maintenance",
        "✅ Quality",
        "📈 Reports & Alerts",
    ],
    "inventory_manager": [
        "📦 Inventory & Supply",
        "📈 Reports & Alerts",
    ],
    "maintenance_manager": [
        "⚙️ Machines & Maintenance",
        "🏭 Production",
        "📈 Reports & Alerts",
    ],
    "quality_manager": [
        "✅ Quality",
        "🏭 Production",
        "📈 Reports & Alerts",
    ],
    "workforce_manager": [
        "👥 Workforce",
        "📈 Reports & Alerts",
    ],
    "logistics_manager": [
        "🚚 Logistics",
        "📦 Orders & Demand",
        "📈 Reports & Alerts",
    ],
    "finance_manager": [
        "💰 Costs",
        "📈 Reports & Alerts",
    ],
    "safety_manager": [
        "🛡️ Safety & Risk",
        "📈 Reports & Alerts",
    ],
    "supervisor": [
        "📊 Overview",
        "🏭 Production",
        "✅ Quality",
        "📈 Reports & Alerts",
    ],
    "read_only_viewer": [
        "📊 Overview",
    ],
}


def get_allowed_pages(role: str | None) -> list[str]:
    """Return pages allowed for the supplied role."""
    return ROLE_PAGES.get(role or "", [])


def default_page(role: str | None) -> str | None:
    """Return the first permitted page."""
    pages = get_allowed_pages(role)
    return pages[0] if pages else None
