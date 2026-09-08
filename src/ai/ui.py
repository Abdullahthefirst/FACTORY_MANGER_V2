"""AI UI and optional Gemini-powered insights for the FactoryOps dashboard."""

from __future__ import annotations

from typing import Callable

import pandas as pd
import streamlit as st

try:
    from google import genai
except Exception:  # pragma: no cover - optional dependency
    genai = None


def init_ai_state() -> None:
    """Initialize optional AI state only after the manager dashboard auth is ready."""
    st.session_state.setdefault("gemini_api_key", "")
    st.session_state.setdefault("ai_active", False)
    st.session_state.setdefault("ai_analysis", "")
    st.session_state.setdefault("ai_suggestions", [])
    st.session_state.setdefault("rag_history", [])


def _get_gemini_client() -> object | None:
    """Return a configured Gemini client when the API key is available."""
    api_key = st.session_state.get("gemini_api_key", "").strip()
    if not api_key or genai is None:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def _safe_ai_status(message: str) -> None:
    """Display a safe, non-blocking informational message when AI is unavailable."""
    st.info(message)


def _make_ai_prompt(question: str, context: str | None = None) -> str:
    """Build a prompt that blends the manager's question with current dashboard context."""
    if context:
        return f"Context:\n{context}\n\nQuestion:\n{question}"
    return question


def render_dashboard_ai_suggestions() -> None:
    """Render quick AI suggestion cards inside the Overview dashboard."""
    api_key = st.session_state.get("gemini_api_key", "").strip()
    if not api_key:
        st.caption("AI suggestions are available after adding a Gemini API key in AI Center.")
        return

    st.subheader("AI Suggestions")
    suggested_actions = [
        "Review delayed production orders and flag any schedule risk.",
        "Check inventory reorder gaps before tomorrow's staffing plan.",
        "Prioritize machine maintenance on the highest-impact issues.",
    ]

    cols = st.columns(len(suggested_actions))
    for i, suggestion in enumerate(suggested_actions):
        with cols[i]:
            st.markdown(
                f"""
                <div style="border:1px solid #dfe7f1; border-radius:12px; padding:14px; background:#f8fbff; min-height:120px;">
                    <div style="font-weight:700; color:#17324d; margin-bottom:8px;">Suggested action</div>
                    <div style="color:#334155;">{suggestion}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_ai_page(load_table: Callable[[str], pd.DataFrame]) -> None:
    """Render the AI Center interface with optional Gemini-powered analysis and chat."""
    st.title("🤖 AI Center")
    st.caption("Optional AI assistance for diagnostics, recommendations, and facility guidance.")

    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=st.session_state.get("gemini_api_key", ""),
        help="Add your Gemini key to enable AI analysis. This stays optional and does not block the dashboard.",
    )
    if api_key:
        st.session_state.gemini_api_key = api_key
        st.session_state.ai_active = True
    else:
        st.session_state.ai_active = False

    if not st.session_state.ai_active:
        _safe_ai_status(
            "AI is optional. The manager dashboard remains fully active without a Gemini key."
        )
        return

    client = _get_gemini_client()
    if client is None:
        st.warning("The Gemini key appears invalid or the package is unavailable. AI features will remain off until it is fixed.")
        st.session_state.ai_active = False
        return

    tab1, tab2, tab3 = st.tabs(["AI Analysis", "AI Suggestions", "RAG Chatbot"])

    with tab1:
        st.subheader("AI Analysis")
        if st.button("Run AI analysis"):
            try:
                context = "\n".join(
                    [
                        "Factory overview summary",
                        f"Production records rows: {len(load_table('production_records'))}",
                        f"Orders rows: {len(load_table('customer_orders'))}",
                        f"Inventory rows: {len(load_table('inventory'))}",
                        f"Machines rows: {len(load_table('machines'))}",
                    ]
                )
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=_make_ai_prompt(
                        "Provide a concise operational summary and highlight top risks for the factory.",
                        context,
                    ),
                )
                st.session_state.ai_analysis = response.text
                st.write(st.session_state.ai_analysis)
            except Exception as error:
                st.error(f"AI analysis could not run: {error}")
        else:
            if st.session_state.ai_analysis:
                st.write(st.session_state.ai_analysis)
            else:
                st.info("Use the AI analysis tab to generate an operational summary.")

    with tab2:
        st.subheader("AI Suggestions")
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=_make_ai_prompt(
                    "Provide 5 concise operational suggestions for a factory manager focused on production, inventory, quality, and maintenance.",
                    None,
                ),
            )
            st.session_state.ai_suggestions = [
                line.strip()
                for line in str(response.text).splitlines()
                if line.strip()
            ]
        except Exception as error:
            st.session_state.ai_suggestions = []
            st.warning(f"AI suggestions are unavailable: {error}")

        if st.session_state.ai_suggestions:
            for suggestion in st.session_state.ai_suggestions:
                st.markdown(f"- {suggestion}")
        else:
            st.info("No AI suggestions are available right now.")

    with tab3:
        st.subheader("RAG Chatbot")
        if "rag_history" not in st.session_state:
            st.session_state.rag_history = []

        user_question = st.text_input("Ask about operations, delays, materials, or machine issues")
        if st.button("Send") and user_question.strip():
            try:
                conversations = "\n".join(
                    [f"Q: {entry['question']}\nA: {entry['answer']}" for entry in st.session_state.rag_history]
                )
                prompt = _make_ai_prompt(
                    user_question,
                    (
                        "Recent conversation history:\n"
                        f"{conversations}\n\nCurrent factory context: production, inventory, orders, quality, and maintenance."
                        if conversations
                        else "Current factory context: production, inventory, orders, quality, and maintenance."
                    ),
                )
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                )
                answer = str(response.text)
                st.session_state.rag_history.append({"question": user_question, "answer": answer})
                for item in st.session_state.rag_history[-3:]:
                    with st.expander(f"Q: {item['question']}"):
                        st.write(item["answer"])
            except Exception as error:
                st.error(f"Chatbot request failed: {error}")

        if not st.session_state.rag_history:
            st.info("Ask the chatbot a question to begin the conversation.")
