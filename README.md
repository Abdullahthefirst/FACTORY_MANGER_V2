# Factory Ops AI

Streamlit + Supabase factory operations application architecture.

This repository currently contains the project structure only. Application logic, database records, sample data, and AI functionality will be added in later phases.

## Top-level flow

`app.py` → Login → Manager Dashboard / Data Entry / AI Assistant

## Layout

- `src/pages/` — application pages
- `src/data_entry/` — data-entry forms
- `src/database/` — Supabase queries, writes, updates, and validation
- `src/analytics/` — domain analytics
- `src/components/` — reusable Streamlit UI components
- `src/ai/` — reserved for RAG, embeddings, analysis, and recommendations
- `sample_data/` — reserved for future seed files
- `sql/` — Supabase schema, RLS policies, and database functions

## Local configuration

Keep `.env` and `.streamlit/secrets.toml` local. Never commit credentials or secrets.
