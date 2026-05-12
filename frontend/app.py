import os
import uuid
from html import escape
from typing import Any

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


st.set_page_config(
    page_title="Drive Discovery Assistant",
    page_icon=":mag:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
    .main .block-container { max-width: 980px; padding-top: 2rem; }
    .drive-card {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 14px 16px;
        margin: 10px 0;
        background: #ffffff;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
    }
    .drive-card-title {
        font-weight: 650;
        font-size: 1rem;
        margin-bottom: 4px;
        color: #111827;
    }
    .drive-card-meta {
        color: #4b5563;
        font-size: 0.86rem;
        margin-bottom: 8px;
    }
    .status-pill {
        display: inline-block;
        border: 1px solid #c7d2fe;
        color: #3730a3;
        background: #eef2ff;
        padding: 4px 8px;
        border-radius: 999px;
        font-size: 0.78rem;
        margin: 4px 0 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi. Ask me to find files in your shared Google Drive folder.",
                "files": [],
            }
        ]


def chat_request(message: str) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/chat",
        json={"message": message, "session_id": st.session_state.session_id},
        timeout=75,
    )
    response.raise_for_status()
    return response.json()


def render_file_card(file: dict[str, Any]) -> None:
    name = escape(str(file.get("name", "Untitled")))
    mime_type = escape(str(file.get("mimeType", "unknown")))
    modified = escape(str(file.get("modifiedTime") or "Unknown modified date"))
    web_link = file.get("webViewLink")
    download_link = file.get("webContentLink")
    file_id = escape(str(file.get("id", "")))

    actions = []
    if web_link:
        actions.append(f"<a href='{escape(str(web_link), quote=True)}' target='_blank'>Preview</a>")
    if download_link:
        actions.append(f"<a href='{escape(str(download_link), quote=True)}' target='_blank'>Download</a>")
    action_html = " &middot; ".join(actions) if actions else "No link available"

    st.markdown(
        f"""
        <div class="drive-card">
            <div class="drive-card-title">{name}</div>
            <div class="drive-card-meta">{mime_type} &middot; Modified {modified}</div>
            <div class="drive-card-meta">File ID: {file_id}</div>
            <div>{action_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_message(message: dict[str, Any]) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message.get("content", ""))
        query = message.get("generated_query")
        if query:
            with st.expander("Generated Drive query"):
                st.code(query, language="sql")
        files = message.get("files") or []
        if files:
            st.markdown(f"<span class='status-pill'>{len(files)} result(s)</span>", unsafe_allow_html=True)
            for file in files:
                render_file_card(file)


initialize_state()

left, right = st.columns([0.78, 0.22], vertical_alignment="center")
with left:
    st.title("Drive Discovery Assistant")
    st.caption("Conversational search for a restricted Google Drive folder")
with right:
    if st.button("New chat", use_container_width=True):
        try:
            requests.delete(f"{API_BASE_URL}/chat/{st.session_state.session_id}", timeout=10)
        except requests.RequestException:
            pass
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Fresh chat ready. What should I search for?",
                "files": [],
            }
        ]
        st.rerun()


for item in st.session_state.messages:
    render_message(item)


prompt = st.chat_input("Search by name, type, content, or date...")
if prompt:
    user_message = {"role": "user", "content": prompt, "files": []}
    st.session_state.messages.append(user_message)
    render_message(user_message)

    with st.chat_message("assistant"):
        with st.spinner("Searching Google Drive..."):
            try:
                payload = chat_request(prompt)
                assistant_message = {
                    "role": "assistant",
                    "content": payload.get("answer", ""),
                    "files": payload.get("files", []),
                    "generated_query": payload.get("generated_query"),
                }
            except requests.RequestException as exc:
                assistant_message = {
                    "role": "assistant",
                    "content": f"I could not reach the backend or complete the search: {exc}",
                    "files": [],
                }

        st.markdown(assistant_message["content"])
        if assistant_message.get("generated_query"):
            with st.expander("Generated Drive query"):
                st.code(assistant_message["generated_query"], language="sql")
        for file in assistant_message.get("files", []):
            render_file_card(file)

    st.session_state.messages.append(assistant_message)
