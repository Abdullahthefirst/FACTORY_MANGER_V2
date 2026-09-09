"""AI-generated, evidence-grounded factory suggestions."""

import json

from src.ai.ai_analysis import _generate


def generate_suggestions(client, context):
    prompt = f"""
You are a factory operations decision-support assistant.

Use ONLY the supplied factory data. Never invent facts or expected outcomes.
Return a JSON array with no markdown and no code fences.

Return at most five suggestions. Each item must contain exactly:
priority, area, title, action, evidence.

Use priorities: Critical, High, Medium, or Low.
Make each suggestion practical and tied to supplied evidence.

FACTORY DATA:
{json.dumps(context, default=str)}
"""

    text = _generate(client, prompt, max_output_tokens=1400)
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lstrip().lower().startswith("json"):
            cleaned = cleaned.lstrip()[4:].strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            parsed = parsed.get("suggestions", [])
        if not isinstance(parsed, list):
            raise ValueError("Expected a JSON list")

        suggestions = []
        for item in parsed[:5]:
            if not isinstance(item, dict):
                continue
            suggestions.append({
                "priority": str(item.get("priority", "Medium")),
                "area": str(item.get("area", "Factory")),
                "title": str(item.get("title", "Review factory data")),
                "action": str(item.get("action", "Review the available evidence.")),
                "evidence": str(item.get("evidence", "Evidence is limited.")),
            })

        if not suggestions:
            raise ValueError("No usable suggestions returned")

        return suggestions

    except (json.JSONDecodeError, TypeError, ValueError):
        return [{
            "priority": "Medium",
            "area": "Data quality",
            "title": "Review the AI response",
            "action": "Open AI Analysis for a grounded management summary.",
            "evidence": "The model returned an unexpected response format.",
        }]
