# Invoicely

An AI-powered invoice ingestion and agentic query engine. Upload invoice PDFs/images and ask natural language questions about them, semantic questions go to ChromaDB vector database, exact number queries go to SQLite database.

---

## How It Works

### Ingestion (Write Path)
1. You upload an invoice (PDF or image) via the API.
2. **LlamaParse** converts it to clean Markdown.
3. **Google Gemini** reads the Markdown and extracts structured data (vendor, amounts, dates, line items) into a strict JSON schema.
4. The data is split into two stores:
   - **SQLite** — for structured queries (totals, tax, dates)
   - **ChromaDB** — for semantic search (descriptions, summaries)

The upload endpoint returns immediately; all processing happens in the background.

### Querying (Read Path)
A **LangGraph** agent takes your natural language question and routes it:
- *"What did we buy from Acme?"* → ChromaDB (vector search)
- *"What is the total tax this month?"* → SQLite (deterministic SQL)

This dual-store design guarantees exact numbers always come from SQL, never from LLM memory. Conversations are stateful — each `session_id` maintains its own thread.

---

## Stack

| | |
|---|---|
| API | FastAPI + Uvicorn |
| Document Parsing | LlamaParse (LlamaCloud) |
| LLM | Google Gemini 2.5 Flash |
| Agent | LangGraph |
| Vector Store | ChromaDB |
| Relational Store | SQLite |
| Frontend | Streamlit |
| Observability | LangSmith + OpenTelemetry |

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/your-username/invoicely.git
cd invoicely
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
# Required
LLAMA_CLOUD_API_KEY='llx-...'
GOOGLE_API_KEY='AIza...'

# Optional — defaults to gemini-2.5-flash
GEMINI_MODEL_NAME='gemini-2.5-flash'
GEMINI_CHAT_MODEL_NAME='gemini-2.5-flash'

# LangSmith observability (optional but recommended)
export LANGSMITH_TRACING=true
export LANGSMITH_ENDPOINT='https://api.smith.langchain.com'
export LANGSMITH_API_KEY='lsv2_...'
export LANGSMITH_PROJECT='invoicely'
```

> The LangSmith variables can also be exported directly in your shell instead of the `.env` file.

### 3. Run the API

```bash
uvicorn main:app --reload
```

API runs at `http://localhost:8000` — interactive docs at `http://localhost:8000/docs`.

### 4. Run the Streamlit frontend

```bash
streamlit run app.py
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload` | Upload an invoice (PDF/image) for async processing |
| `GET` | `/invoices` | List all stored invoices |
| `POST` | `/chat` | Send a message to the LangGraph agent |
| `GET` | `/` | Health check |

### Example: upload an invoice

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@invoice.pdf"
```

Response:
```json
{
  "message": "Invoice received and processing started.",
  "filename": "invoice.pdf"
}
```

### Example: query the agent

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user-123", "message": "What is the total tax across all invoices?"}'
```

Response:
```json
{
  "reply": "The total tax across all invoices is $340.50."
}
```