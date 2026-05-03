import streamlit as st
import requests
import uuid

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Invoicely",
    page_icon="🧾",
    layout="wide"
)

st.markdown("""
<style>
    /* Hide default streamlit chrome */
    #MainMenu, footer, header {visibility: hidden;}

    .stChatMessage { border-radius: 12px; }

    .upload-box {
        border: 2px dashed #444;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        color: #888;
        margin-bottom: 1rem;
    }

    .status-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-success { background: #1a3a2a; color: #4ade80; }
    .badge-error   { background: #3a1a1a; color: #f87171; }
</style>
""", unsafe_allow_html=True)

# Session state init
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


# ── Layout ──────────────────────────────────────────────────────────────────
left, right = st.columns([1, 2], gap="large")

# ── LEFT: Upload panel ───────────────────────────────────────────────────────
with left:
    st.markdown("## 🧾 Invoicely")
    st.caption("AI-powered invoice ingestion & analysis")
    st.divider()

    st.markdown("#### Upload Invoice")
    uploaded_file = st.file_uploader(
        "Drop a PDF, image, or document",
        type=["pdf", "png", "jpg", "jpeg", "webp", "tiff"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        if st.button("📤 Ingest Invoice", use_container_width=True):
            with st.spinner("Sending to processing pipeline..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/upload",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
                        timeout=10
                    )
                    if resp.status_code == 200:
                        st.markdown('<span class="status-badge badge-success">✓ Queued for processing</span>', unsafe_allow_html=True)
                        st.caption("Extraction runs in the background. Ask about it in a minute.")
                    else:
                        st.markdown('<span class="status-badge badge-error">✗ Upload failed</span>', unsafe_allow_html=True)
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach API. Is the server running on port 8000?")

    st.divider()

    # Invoice list
    st.markdown("#### Stored Invoices")
    if st.button("🔄 Refresh", use_container_width=True):
        st.session_state.pop("invoices_cache", None)

    if "invoices_cache" not in st.session_state:
        try:
            resp = requests.get(f"{API_BASE}/invoices", timeout=5)
            st.session_state.invoices_cache = resp.json() if resp.status_code == 200 else None
        except requests.exceptions.ConnectionError:
            st.session_state.invoices_cache = None

    inv_data = st.session_state.get("invoices_cache")
    if inv_data is None:
        st.caption("⚠️ Could not reach API")
    elif inv_data["total_invoices"] == 0:
        st.caption("No invoices yet. Upload one above.")
    else:
        st.caption(f"{inv_data['total_invoices']} invoice(s) stored")
        for inv in inv_data["invoices"]:
            with st.expander(f"🏢 {inv['vendor'] or 'Unknown vendor'}"):
                st.write(f"**Amount:** ${inv['total']:,.2f}" if inv['total'] else "**Amount:** N/A")
                st.write(f"**Date:** {inv['date'] or 'N/A'}")
                st.caption(f"ID: {inv['document_id'][:8]}...")

    st.divider()
    # New chat session button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()


# ── RIGHT: Chat panel ────────────────────────────────────────────────────────
with right:
    st.markdown("#### Ask about your invoices")
    st.caption(f"Session: `{st.session_state.session_id[:8]}...`")

    # Chat history
    chat_container = st.container(height=520)
    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div style='color:#666; text-align:center; margin-top:120px;'>
                💬 Ask anything about your invoices<br>
                <small>e.g. "Total spend by vendor" or "Any SaaS expenses?"</small>
            </div>
            """, unsafe_allow_html=True)
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Ask about your invoices..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        resp = requests.post(
                            f"{API_BASE}/chat",
                            json={
                                "session_id": st.session_state.session_id,
                                "message": prompt
                            },
                            timeout=60
                        )
                        if resp.status_code == 200:
                            reply = resp.json()["reply"]
                        else:
                            reply = f"Error {resp.status_code}: {resp.text}"
                    except requests.exceptions.ConnectionError:
                        reply = "⚠️ Cannot reach API. Is the server running on port 8000?"
                    except requests.exceptions.Timeout:
                        reply = "⚠️ Request timed out. The model may still be processing."

                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})