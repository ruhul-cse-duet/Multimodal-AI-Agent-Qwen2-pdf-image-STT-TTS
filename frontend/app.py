"""
Streamlit frontend (v2) that talks to the FastAPI backend.
"""

import logging
import os
from pathlib import Path

import requests
from requests.exceptions import RequestException
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT = 360


def api_url(path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{API_BASE_URL}{path}"


def check_backend() -> bool:
    try:
        response = requests.get(api_url("/health"), timeout=360)
        return response.ok
    except RequestException as exc:
        logger.warning("Backend health check failed: %s", exc)
        return False


def ensure_backend_ready() -> bool:
    backend_ok = check_backend()
    st.session_state.initialized = backend_ok
    if not backend_ok:
        st.error("Backend not reachable. Start: python -m uvicorn v2.backend.main:app --host 127.0.0.1 --port 8000")
        return False
    return True


def initialize_state():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "processing_status" not in st.session_state:
        st.session_state.processing_status = {"success": 0, "failed": 0}
    st.session_state.initialized = check_backend()


def load_css():
    css_path = Path(__file__).resolve().parents[2] / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def process_documents(files):
    if not files:
        st.warning("Please upload at least one document.")
        return
    if not ensure_backend_ready():
        return

    allowed_types = [".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".gif"]
    payload_files = []
    skipped = []

    for uploaded_file in files:
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix not in allowed_types:
            skipped.append(f"{uploaded_file.name} (unsupported type)")
            continue
        if uploaded_file.size > 50 * 1024 * 1024:
            skipped.append(f"{uploaded_file.name} (file too large)")
            continue
        payload_files.append((
            "files",
            (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "application/octet-stream")
        ))

    if not payload_files:
        if skipped:
            st.warning("Skipped files: " + ", ".join(skipped))
        st.error("No valid files to process.")
        return

    try:
        with st.spinner("Processing documents..."):
            response = requests.post(api_url("/process"), files=payload_files, timeout=REQUEST_TIMEOUT)
        if not response.ok:
            raise RequestException(f"{response.status_code} - {response.text}")
        result = response.json()
    except RequestException as exc:
        st.error(f"Backend request failed: {exc}")
        return
    except ValueError:
        st.error("Invalid response from backend.")
        return

    all_skipped = skipped + result.get("skipped", [])
    if all_skipped:
        st.warning("Skipped files: " + ", ".join(all_skipped))

    processed_files = [Path(p).name for p in result.get("processed_files", [])]
    if processed_files:
        st.session_state.uploaded_files.extend(processed_files)

    st.session_state.processing_status["success"] += result.get("success", 0)
    st.session_state.processing_status["failed"] += result.get("failed", 0)

    if result.get("success", 0) > 0:
        st.success(f"Processed {result['success']} file(s).")
    if result.get("failed", 0) > 0:
        errors = "\n".join(result.get("errors", []))
        st.error(f"Failed {result['failed']} file(s):\n{errors}")


def handle_query(query_text: str, use_speech: bool):
    if not query_text.strip():
        st.warning("Please enter a question.")
        return
    if not ensure_backend_ready():
        return

    try:
        with st.spinner("Thinking..."):
            response = requests.post(
                api_url("/query"),
                json={"query": query_text},
                timeout=REQUEST_TIMEOUT
            )
        if not response.ok:
            raise RequestException(f"{response.status_code} - {response.text}")
        result = response.json()
    except RequestException as exc:
        st.error(f"Backend request failed: {exc}")
        return
    except ValueError:
        st.error("Invalid response from backend.")
        return

    if result.get("error"):
        st.error(f"Error: {result['error']}")
        return

    response_text = result.get("response", "No response generated.")
    st.markdown(
        f"""
        <div class="response-box">
            <strong>Response:</strong><br><br>
            {response_text}
        </div>
        """,
        unsafe_allow_html=True
    )

    if use_speech:
        try:
            with st.spinner("Generating speech..."):
                tts_response = requests.post(
                    api_url("/tts"),
                    json={"text": response_text},
                    timeout=REQUEST_TIMEOUT
                )
            if tts_response.status_code == 503:
                # TTS not configured
                error_detail = tts_response.json().get("detail", "TTS not configured")
                st.info(
                    "🔇 Text-to-Speech is not configured.\n\n"
                    "To enable TTS:\n"
                    "1. Download Piper TTS: https://github.com/rhasspy/piper/releases\n"
                    "2. Download a voice model: https://github.com/rhasspy/piper/releases/tag/2023.11.14-2\n"
                    "3. Set PIPER_MODEL_PATH in .env\n"
                    "4. Restart the backend"
                )
            elif not tts_response.ok:
                raise RequestException(f"{tts_response.status_code} - {tts_response.text}")
            else:
                st.audio(tts_response.content, format="audio/wav")
        except RequestException as exc:
            st.warning(f"TTS failed: {exc}")

    context = result.get("context", [])
    if context:
        with st.expander("View sources"):
            for index, ctx in enumerate(context, 1):
                source = ctx.get("metadata", {}).get("source", "Unknown")
                st.markdown(f"Source {index}: {Path(source).name}")
                content = ctx.get("content", "")
                preview = f"{content[:300]}..." if len(content) > 300 else content
                st.text(preview)
                score = ctx.get("score", 0.0)
                st.markdown(f"Relevance score: {score:.4f}")
                st.divider()

    st.session_state.chat_history.append({
        "query": query_text,
        "response": response_text
    })


initialize_state()
st.set_page_config(page_title="Multimodal Agent AI", layout="wide")
load_css()

st.title("Multimodal Agent AI ")
st.caption("FastAPI backend + Streamlit frontend.")

with st.sidebar:
    st.header("System Status")
    st.caption(f"API: {API_BASE_URL}")
    if st.session_state.get("initialized", False):
        st.success("Backend connected")
    else:
        st.error("Backend not reachable")
        if st.button("Reconnect Backend", use_container_width=True):
            st.session_state.initialized = check_backend()
            st.rerun()

    st.divider()
    try:
        response = requests.get(api_url("/stats"), timeout=300)
        if response.ok:
            stats = response.json()
            st.metric("Documents in Database", stats.get("total_documents", 0))
        else:
            st.metric("Documents in Database", 0)
    except RequestException:
        st.metric("Documents in Database", 0)

    st.divider()
    st.header("Processing Stats")
    st.metric("Files Processed", st.session_state.processing_status["success"])
    st.metric("Files Failed", st.session_state.processing_status["failed"])

    st.divider()
    st.header("Uploaded Files")
    if st.session_state.uploaded_files:
        for idx, file_name in enumerate(st.session_state.uploaded_files, 1):
            st.text(f"{idx}. {file_name}")
    else:
        st.info("No files uploaded yet.")

    st.divider()
    if st.button("Clear DB", use_container_width=True):
        try:
            response = requests.post(api_url("/clear"), timeout=300)
            if response.ok:
                st.session_state.uploaded_files = []
                st.session_state.processing_status = {"success": 0, "failed": 0}
                st.success("Database cleared!")
                st.rerun()
            else:
                st.error("Failed to clear database.")
        except RequestException:
            st.error("Backend not reachable.")

tab_upload, tab_query, tab_history = st.tabs(["Upload", "Ask", "History"])

with tab_upload:
    st.subheader("Upload Documents")
    st.info("Supported: PDF, DOCX, PNG, JPG, JPEG, BMP, TIFF, GIF (max 50MB)")
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        type=["pdf", "docx", "doc", "png", "jpg", "jpeg", "bmp", "tiff", "gif"],
        accept_multiple_files=True
    )
    if uploaded_files:
        st.info(f"{len(uploaded_files)} file(s) selected")
        if st.button("Process Files", use_container_width=True, type="primary"):
            process_documents(uploaded_files)

with tab_query:
    st.subheader("Ask Questions")
    input_method = st.radio(
        "Select input method:",
        ["Text", "Speech (Audio Upload)"],
        horizontal=True
    )
    query_text = ""
    if input_method == "Text":
        query_text = st.text_area("Enter your question:", height=150, max_chars=5000)
    else:
        audio_file = st.file_uploader("Upload audio file:", type=["wav", "mp3", "ogg"])
        if audio_file:
            try:
                if ensure_backend_ready():
                    response = requests.post(
                        api_url("/transcribe"),
                        files={
                            "file": (
                                audio_file.name,
                                audio_file.getvalue(),
                                audio_file.type or "audio/wav"
                            )
                        },
                        timeout=REQUEST_TIMEOUT
                    )
                    if not response.ok:
                        raise RequestException(f"{response.status_code} - {response.text}")
                    data = response.json()
                    query_text = data.get("text", "")
                    if query_text:
                        st.success(f"Transcribed: {query_text}")
                    else:
                        st.warning("No speech detected.")
            except RequestException as exc:
                st.error(f"Transcription error: {exc}")
            except ValueError:
                st.error("Invalid response from backend.")

    col1, col2 = st.columns([4, 1])
    with col1:
        output_speech = st.checkbox("Enable speech output")
    with col2:
        ask_button = st.button("Ask", use_container_width=True, type="primary")
    if ask_button and query_text:
        handle_query(query_text, output_speech)

with tab_history:
    st.subheader("Conversation History")
    if st.session_state.chat_history:
        for index, chat in enumerate(reversed(st.session_state.chat_history), 1):
            st.markdown(f"Conversation {index}")
            st.markdown(f"Question: {chat['query']}")
            st.markdown(f"Answer: {chat['response']}")
            st.divider()
    else:
        st.info("No conversation history yet.")
