"""Gemini generation functions for management analysis."""

import json


GENERATION_MODEL = "gemini-3.6-flash"


def _generate(client, prompt, max_output_tokens=1800):
    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
        config={
            "max_output_tokens": max_output_tokens,
        },
    )
    return (response.text or "").strip()


def generate_management_analysis(client, context):
    prompt = f"""
You are a production-operations analyst for a factory manager.

Analyze ONLY the supplied factory data. Never invent facts, causes, quantities,
people, dates, or outcomes. If data is missing, clearly identify the gap.

Prioritize production performance, delayed orders, inventory risks, machine
issues, quality, workforce availability, safety, and practical next actions.

FACTORY DATA:
{json.dumps(context, default=str)}

Return concise markdown with exactly these sections:

### Executive assessment
2-4 sentences.

### Priority findings
Up to 7 evidence-based bullets.

### Recommended actions
Up to 6 actions ordered by urgency.

### Data gaps affecting confidence
Mention meaningful missing information.
"""

    return _generate(client, prompt, max_output_tokens=1800)
