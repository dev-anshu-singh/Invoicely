# Invoicely

Invoicely is an agentic RAG invoice ingestion and analysis app. It accepts invoice PDFs and images, extracts structured invoice data, stores exact fields in SQLite, stores searchable summaries in ChromaDB, and uses a LangGraph agent to decide which retrieval path should answer each user question.

The project currently includes:

- A FastAPI backend for upload, ingestion, invoice listing, health checks, and chat.
- A Streamlit frontend for uploading invoices, viewing stored invoice metadata, and chatting with the assistant.
- A LangGraph agent that chooses between SQL search and vector search.
- A LlamaCloud + Gemini extraction pipeline that turns invoice documents into a strict Pydantic schema.

## How It Works

Invoicely has two main paths:

| Path | Flow | Purpose |
|---|---|---|
| Ingestion | Streamlit/API upload -> FastAPI background task -> LlamaCloud parsing -> Gemini extraction -> SQLite + ChromaDB | Converts invoice files into structured records and searchable semantic context |
| Chat | User question -> LangGraph agent -> SQL tool or vector tool -> assistant response | Answers invoice questions using the best retrieval source for the query |

The split storage design is intentional: SQLite handles exact totals, dates, filters, and aggregations, while ChromaDB handles fuzzy or semantic questions about vendors, categories, summaries, and purchased items.

## Security & Reliability Guardrails

- Prompt injection defense: The ingestion prompt wraps extracted OCR/Markdown text inside explicit `<document_content>` XML delimiters and instructs the model to treat everything inside those tags strictly as untrusted document data, not executable instructions.
- Dynamic schema injection: The SQL tool uses LangChain's `SQLDatabase` utility to inspect the live SQLite schema and sample rows, then injects that context into the tool description instead of relying on a hardcoded database summary.
- Query sandboxing: SQL access is limited to `SELECT` statements, runs through a read-only SQLite connection using `?mode=ro`, and uses a strict `2.0` second timeout so bad or overly complex generated queries cannot freeze the app.
- Agentic circuit breaker: The LangGraph state tracks tool-loop progress with an `operator.add` reducer, enforces a strict 3-step limit, and routes to a graceful fallback that stops database retries and provides the best vector/context-based answer available.

## Features

- Upload invoice files through the API or Streamlit UI.
- Supported frontend upload types: `pdf`, `png`, `jpg`, `jpeg`, `webp`, and `tiff`.
- Process uploads asynchronously with FastAPI background tasks, so the upload response returns immediately.
- Parse uploaded documents with LlamaCloud and return Markdown content.
- Extract invoice data with Google Gemini using structured output.
- Store exact invoice fields in SQLite.
- Store semantic invoice summaries and purchased item descriptions in ChromaDB.
- List stored invoices with document ID, vendor, amount, and invoice date.
- Ask natural-language questions in a stateful chat session.
- Route structured questions to SQL for deterministic results.
- Route semantic questions to ChromaDB vector search.
- Enforce read-only SQL queries with `SELECT`-only validation.
- Automatically cap SQL result sets to 20 rows unless the app is changed.
- Use a short SQL execution timeout to avoid stuck database calls.
- Preserve chat context per `session_id` using LangGraph memory.
- Stop runaway tool loops with a 3-step circuit breaker and fallback response.
- Hide raw SQL/tool output from the user-facing assistant response.

## Extracted Invoice Schema

Each processed invoice is normalized into these fields:

| Field | Description |
|---|---|
| `document_id` | Generated UUID for the stored document |
| `ingestion_time` | Timestamp when the system record is created |
| `source_filename` | Original uploaded filename |
| `vendor_name` | Company issuing the invoice |
| `invoice_number` | Invoice ID, if present |
| `invoice_date` | Date normalized as `YYYY-MM-DD` |
| `total_amount` | Final invoice amount including taxes |
| `tax_amount` | Total tax amount, defaulting to `0.0` when missing |
| `currency` | 3-letter currency code, defaulting to `USD` |
| `category` | Broad expense category such as SaaS, Travel, Hardware, Consulting |
| `summary` | Short natural-language invoice summary |
| `line_items` | Purchased items with description, quantity, unit price, and total |

SQLite stores the structured metadata in the `invoice_metadata` table. ChromaDB stores a searchable text chunk containing the invoice summary and line item descriptions, with vendor and category metadata.

## Tech Stack

| Area | Technology |
|---|---|
| API | FastAPI, Uvicorn |
| Frontend | Streamlit |
| Document parsing | LlamaCloud |
| Extraction model | Google Gemini via LangChain |
| Chat agent | LangGraph |
| Agent tools | LangChain tools |
| Structured storage | SQLite |
| Semantic storage | ChromaDB |
| SQL safety/parsing | sqlglot |
| Environment config | python-dotenv |
| Observability support | LangSmith dependencies |

## Project Structure

```text
.
+-- main.py                         # FastAPI app entrypoint
+-- requirements.txt                # Python dependencies
+-- frontend/
|   +-- app.py                      # Streamlit upload/chat interface
+-- app/
    +-- config.py                   # Environment and storage paths
    +-- llm.py                      # Gemini model factories
    +-- db/
    |   +-- database.py             # SQLite and Chroma setup/persistence
    +-- models/
    |   +-- schemas.py              # Pydantic invoice schemas
    +-- prompts/
    |   +-- templates.py            # Extraction and chat prompts
    +-- routers/
    |   +-- upload.py               # /upload and /invoices endpoints
    |   +-- chat.py                 # /chat endpoint
    +-- services/
        +-- ingestion_logic.py      # LlamaCloud + Gemini ingestion pipeline
        +-- chat_graph.py           # LangGraph agent workflow
        +-- tools/
            +-- sql_search.py       # Read-only SQL search tool
            +-- vector_search.py    # Chroma semantic search tool
```

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
LLAMA_CLOUD_API_KEY=llx-...
GOOGLE_API_KEY=AIza...

# Optional. Defaults are set in app/config.py.
GEMINI_CHAT_MODEL_NAME=gemini-3.1-flash-lite-preview
```

Optional LangSmith variables can also be set if you want tracing:

```env
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=invoicely
```

## Running the App

Start the FastAPI backend:

```bash
uvicorn main:app --reload
```

The API runs at:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs` for Swagger UI

In a second terminal, start the Streamlit frontend:

```bash
streamlit run frontend/app.py
```

The frontend expects the API at `http://127.0.0.1:8000`.

## API Reference

### `GET /`

Health check endpoint.

Example response:

```json
{
  "status": "Invoicely API is running!"
}
```

### `POST /upload`

Uploads an invoice file and queues background processing.

Example:

```bash
curl -X POST http://127.0.0.1:8000/upload \
  -F "file=@invoice.pdf"
```

Example response:

```json
{
  "message": "Invoice received and processing started.",
  "filename": "invoice.pdf"
}
```

### `GET /invoices`

Lists stored invoice metadata from SQLite.

Example response:

```json
{
  "total_invoices": 1,
  "invoices": [
    {
      "document_id": "4d46a07f-42b0-4c3a-ae77-f18c71f640ea",
      "vendor": "Acme Inc.",
      "total": 1200.5,
      "date": "2026-07-30"
    }
  ]
}
```

### `POST /chat`

Sends a message to the LangGraph invoice assistant.

Request body:

```json
{
  "session_id": "user-or-session-id",
  "message": "What is the total spend by vendor?"
}
```

Example response:

```json
{
  "reply": "Here is the total spend by vendor..."
}
```

## Chat Behavior

The assistant has two tools:

| Tool | Used for |
|---|---|
| `search_invoices_sql` | Totals, counts, dates, filters, invoice lists, category/vendor summaries |
| `search_invoices_vector` | Semantic questions about purchased items, services, summaries, and concepts |

Example questions:

- `What is the total spend by vendor?`
- `How many invoices are in each category?`
- `Show invoices above $500.`
- `What is the total tax across all invoices?`
- `Any SaaS expenses?`
- `Find invoices related to cloud software.`
- `What did we buy from Acme?`

## Data Storage Notes

- `SQLITE_DB_PATH` defaults to `invoices.db`.
- `CHROMA_DB_PATH` defaults to `./chroma_db`.
- The SQLite table is created automatically if it does not exist.
- The Chroma collection is created automatically as `invoice_vectors`.
- Uploaded files are temporarily saved as `temp_<filename>` and deleted after processing.

## Important Implementation Details

- The ingestion prompt treats parsed document content as data only, which helps reduce prompt-injection risk from invoice text.
- The extraction model is configured with temperature `0` for deterministic structured extraction.
- The chat model is configured separately from the extraction model.
- SQL search opens SQLite in read-only mode and rejects non-`SELECT` statements.
- The SQL tool injects live database table context into its docstring so the agent can inspect the available schema.
- The Streamlit app keeps a local chat history and creates a new UUID session when the chat is cleared.

## Limitations

- Upload processing happens in-process with FastAPI background tasks; it is not a durable queue.
- The `/upload` response only confirms that processing started, not that extraction succeeded.
- The frontend invoice list is refreshed manually with the Refresh button.
- SQL filtering does not inspect `line_items_json`; semantic item questions should use vector search.
- The current app uses local SQLite and ChromaDB paths, so it is designed for local development and proof-of-concept usage.
