"""Streamlit application entry point."""

import streamlit as st
from supabase import create_client


st.set_page_config(page_title="FactoryOps", layout="wide")
st.title("FactoryOps")

# Configure these values in Streamlit Cloud → App → Settings → Secrets.
# Use only the publishable Supabase key; never use a database password or
# service-role key in Streamlit Cloud.
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Temporary Step 1.3 connection check. Replace with the manager dashboard flow
# after authentication and RLS policies are added in the next step.
try:
    result = supabase.table("departments").select("*").execute()
    st.success("Supabase connected successfully.")
    st.write(result.data)
except Exception as error:
    st.error(f"Supabase connection failed: {error}")
