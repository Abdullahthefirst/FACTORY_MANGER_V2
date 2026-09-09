# FactoryOps AI

Streamlit + Supabase factory operations manager and smart data-entry platform.

## Applications

- `app.py` — manager dashboard: overview, orders, production, supply, machines, quality, workforce, logistics, costs, safety, reports, and optional AI Center.
- `data_entry_app.py` — separate operator application using the same Supabase project. It provides smart forms, recent-entry suggestions, validation, submission history, and review workflow.

The two applications are independently deployable Streamlit Cloud apps. They share the same Supabase database, authentication, and audit trail; changing one does not require the other application to be running.

## Supabase setup

Run these files in Supabase SQL Editor in order:

1. `sql/001_schema.sql`
2. `sql/002_rls_policies.sql`
3. `sql/003_sample_functions.sql`
4. `sql/004_operations_and_entry.sql`

The scripts are designed to be rerunnable with `IF NOT EXISTS` safeguards. Existing UUID primary keys are retained. Human-readable codes such as `EMP-001` and `PROD-001` are used in the UI.

## Streamlit Cloud configuration

For the manager app, set these secrets under **App → Settings → Secrets**:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-publishable-or-anon-key"
```

For the optional AI Center, the Gemini key is entered inside the app and held only in the current Streamlit session. The dashboard remains usable when it is blank.

Deploy `app.py` as one Streamlit Cloud app and `data_entry_app.py` as a second Streamlit Cloud app if operators need a separate URL.

## Sample data

`sample_data/seed_database.py` can be run from a controlled environment with Supabase credentials to load or refresh realistic test data. It inserts master data first, then linked operational records, and keeps generated records easy to identify.

## Security

Keep `.env` and `.streamlit/secrets.toml` local. Never commit credentials or service-role keys. The included RLS policies require authenticated users; production deployments should additionally assign roles and department permissions before opening the app to staff.
