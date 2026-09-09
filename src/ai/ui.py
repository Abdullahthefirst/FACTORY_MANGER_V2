"""Optional AI Center UI for the Supabase manager dashboard."""

import json

import streamlit as st

from src.ai.ai_analysis import generate_management_analysis
from src.ai.ai_analysis import GENERATION_MODEL
from src.ai.rag_engine import build_index, retrieve
from src.ai.recommendations import generate_suggestions

try:
    from google import genai
except Exception:  # pragma: no cover - handled in the UI
    genai = None


def init_ai_state():
    defaults = {
        "ai_api_key": None,
        "ai_client": None,
        "ai_error": None,
        "ai_analysis": None,
        "ai_suggestions": [],
        "ai_rag_index": None,
        "ai_rag_error": None,
        "ai_chat_history": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _load_context(load_table):
    tables = [
        "customer_orders",
        "production_records",
        "production_plans",
        "inventory",
        "materials",
        "machines",
        "maintenance_records",
        "quality_inspections",
        "employee_attendance",
        "shipments",
        "operating_costs",
        "safety_incidents",
    ]

    context = {}

    for table_name in tables:
        try:
            dataframe = load_table(table_name)
            if not dataframe.empty:
                context[table_name] = dataframe.head(250).to_dict(
                    orient="records"
                )
        except Exception as exc:
            context[f"{table_name}_unavailable"] = str(exc)

    return context


def _documents_from_context(context):
    documents = []

    for table_name, records in context.items():
        if not isinstance(records, list):
            continue

        for record in records:
            fields = "; ".join(
                f"{key}: {value}"
                for key, value in record.items()
            )
            documents.append(
                f"Factory table: {table_name}. {fields}"
            )

    return documents


def _show_key_panel():
    if genai is None:
        st.error(
            "The Gemini client is not available in this deployment. "
            "Streamlit Cloud will install it from requirements.txt on the next deploy."
        )
        return False

    if st.session_state.ai_client is not None:
        st.success("Gemini key is active for this session.")

        if st.button("Remove Gemini key", key="remove_ai_key"):
            st.session_state.ai_api_key = None
            st.session_state.ai_client = None
            st.session_state.ai_analysis = None
            st.session_state.ai_suggestions = []
            st.session_state.ai_rag_index = None
            st.session_state.ai_chat_history = []
            st.rerun()

        return True

    st.info(
        "Enter a Gemini API key to use AI Analysis, AI Suggestions, and the "
        "RAG chatbot. The rest of the manager dashboard works without it."
    )

    with st.form("gemini_key_form", clear_on_submit=False):
        api_key = st.text_input(
            "Gemini API key",
            type="password",
            placeholder="Paste your key here",
            help="The key is kept only in this Streamlit session.",
        )
        submitted = st.form_submit_button(
            "Activate AI",
            type="primary",
        )

    if submitted:
        if not api_key.strip():
            st.warning("Enter a Gemini API key first.")
        else:
            try:
                st.session_state.ai_api_key = api_key.strip()
                st.session_state.ai_client = genai.Client(
                    api_key=st.session_state.ai_api_key
                )
                st.session_state.ai_error = None
                st.rerun()
            except Exception as exc:
                st.session_state.ai_client = None
                st.session_state.ai_error = str(exc)

    if st.session_state.ai_error:
        st.error(
            "The Gemini key could not be activated. Check the key and try again."
        )

    return False


def _require_data():
    if not st.session_state.get("user"):
        st.info("Log in to the manager dashboard first.")
        return False
    return True


def _render_suggestion_cards(suggestions):
    if not suggestions:
        st.info(
            "No suggestions generated yet. Click the button above to create them."
        )
        return

    colors = {
        "critical": "#b91c1c",
        "high": "#c2410c",
        "medium": "#a16207",
        "low": "#15803d",
    }

    for suggestion in suggestions:
        priority = suggestion.get("priority", "Medium")
        color = colors.get(priority.lower(), "#475569")

        with st.container(border=True):
            st.markdown(
                f"<span style='color:{color};font-weight:700'>"
                f"{priority.upper()}</span> · "
                f"<strong>{suggestion.get('area', 'Factory')}</strong>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"**{suggestion.get('title', 'Suggestion')}**"
            )
            st.write(
                suggestion.get(
                    "action",
                    "Review the available evidence.",
                )
            )
            st.caption(
                "Evidence: "
                + suggestion.get(
                    "evidence",
                    "Not provided.",
                )
            )


def _render_chatbot():
    if not st.session_state.get("ai_chat_history"):
        st.caption(
            "Ask about production, orders, inventory, machines, quality, workforce, "
            "costs, or safety."
        )

    for message in st.session_state.ai_chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input(
        "Ask a question about the factory...",
        key="factory_ai_question",
    )

    if not question:
        return

    context = st.session_state.get("ai_context", {})
    index = st.session_state.get("ai_rag_index")
    client = st.session_state.ai_client

    st.session_state.ai_chat_history.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching factory records..."):
                hits = retrieve(client, index, question)
                evidence = "\n\n".join(
                    f"[{index + 1}] {hit['text']}"
                    for index, hit in enumerate(hits)
                )

                prompt = f"""
You are a factory manager's assistant.

Answer only from the retrieved factory records below.
If the evidence is insufficient, say that clearly.
Do not invent facts or recommendations unsupported by the records.

QUESTION:
{question}

RETRIEVED FACTORY RECORDS:
{evidence or "No matching records were found."}
"""

                response = client.models.generate_content(
                    model=GENERATION_MODEL,
                    contents=prompt,
                    config={"max_output_tokens": 1200},
                )
                answer = (response.text or "").strip()

            st.markdown(answer or "No answer was returned.")
            st.session_state.ai_chat_history.append(
                {
                    "role": "assistant",
                    "content": answer or "No answer was returned.",
                }
            )

            if hits:
                with st.expander("Retrieved evidence"):
                    for hit in hits:
                        st.caption(
                            f"Similarity: {hit['score']:.3f}"
                        )
                        st.write(hit["text"])

        except Exception as exc:
            st.error(
                "The chatbot could not answer this question. "
                "Check the key, model access, and current data."
            )
            st.caption(str(exc))


def render_ai_page(load_table):
    init_ai_state()

    st.title("AI Operations Center")
    st.caption(
        "Optional Gemini assistance over the factory data in this session."
    )

    _show_key_panel()

    analysis_tab, suggestions_tab, rag_tab = st.tabs(
        ["AI Analysis", "AI Suggestions", "RAG Chatbot"]
    )

    if st.session_state.ai_client is None:
        with analysis_tab:
            st.info("Activate Gemini above to use AI Analysis.")
        with suggestions_tab:
            st.info("Activate Gemini above to use AI Suggestions.")
        with rag_tab:
            st.info("Activate Gemini above to use the RAG chatbot.")
        return

    if not _require_data():
        return

    context = _load_context(load_table)
    st.session_state.ai_context = context

    with analysis_tab:
        st.subheader("Management analysis")

        if st.button(
            "Generate / refresh analysis",
            type="primary",
            key="generate_ai_analysis",
        ):
            try:
                with st.spinner("Preparing management analysis..."):
                    st.session_state.ai_analysis = generate_management_analysis(
                        st.session_state.ai_client,
                        context,
                    )
            except Exception as exc:
                st.error(
                    "AI analysis failed safely. The manager dashboard is still available."
                )
                st.caption(str(exc))

        if st.session_state.ai_analysis:
            st.markdown(st.session_state.ai_analysis)
        else:
            st.info("No AI analysis has been generated yet.")

    with suggestions_tab:
        st.subheader("AI Suggestions")
        st.caption(
            "Suggestions generated here will appear on the Overview dashboard."
        )

        if st.button(
            "Generate / refresh suggestions",
            type="primary",
            key="generate_ai_suggestions",
        ):
            try:
                with st.spinner("Preparing prioritized suggestions..."):
                    st.session_state.ai_suggestions = generate_suggestions(
                        st.session_state.ai_client,
                        context,
                    )
                st.success(
                    f"Generated {len(st.session_state.ai_suggestions)} suggestion(s)."
                )
            except Exception as exc:
                st.error(
                    "AI suggestions failed safely. The manager dashboard is still available."
                )
                st.caption(str(exc))

        _render_suggestion_cards(
            st.session_state.ai_suggestions
        )

    with rag_tab:
        st.subheader("Factory RAG chatbot")

        if st.session_state.ai_rag_index is None:
            st.info(
                "Build the session knowledge index before asking questions."
            )

            if st.button(
                "Build / refresh knowledge index",
                type="primary",
                key="build_ai_rag_index",
            ):
                try:
                    documents = _documents_from_context(context)

                    with st.spinner("Building factory knowledge index..."):
                        st.session_state.ai_rag_index = build_index(
                            st.session_state.ai_client,
                            documents,
                        )

                    st.success(
                        f"Indexed {len(documents)} factory records."
                    )
                except Exception as exc:
                    st.session_state.ai_rag_index = None
                    st.error(
                        "The knowledge index could not be built. "
                        "The rest of the dashboard is unaffected."
                    )
                    st.caption(str(exc))

        if st.session_state.ai_rag_index is not None:
            st.success(
                f"Knowledge index ready: "
                f"{len(st.session_state.ai_rag_index['documents'])} records."
            )
            _render_chatbot()


def render_dashboard_ai_suggestions():
    suggestions = st.session_state.get(
        "ai_suggestions",
        [],
    )

    st.subheader("AI Suggestions")

    if not suggestions:
        st.caption(
            "Generate suggestions in AI Center to show prioritized actions here."
        )
        return

    for suggestion in suggestions[:3]:
        st.info(
            f"**{suggestion.get('priority', 'Medium')} · "
            f"{suggestion.get('area', 'Factory')}** — "
            f"{suggestion.get('title', 'Review factory data')}\n\n"
            f"{suggestion.get('action', 'Review the available evidence.')}",
            icon="💡",
        )
