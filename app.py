"""Streamlit application entry point."""

import streamlit as st
from supabase import create_client


st.set_page_config(page_title="FactoryOps", layout="wide")

# Configure these values in Streamlit Cloud -> App -> Settings -> Secrets.
# Use only the publishable Supabase key; never use a database password or
# service-role key in Streamlit Cloud.
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("FactoryOps Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Log in"):
        try:
            response = supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            st.session_state.user = response.user
            st.success("Login successful.")
            st.rerun()
        except Exception:
            st.error("Incorrect email or password.")

    st.stop()

if st.sidebar.button("Log out"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

st.title("FactoryOps")

# Temporary Step 1.3 connection check. Replace with the manager dashboard flow
# after authentication and RLS policies are added in the next step.
try:
    result = supabase.table("departments").select("*").execute()
    st.success("Supabase connected successfully.")
    st.write(result.data)
except Exception as error:
    st.error(f"Supabase connection failed: {error}")
