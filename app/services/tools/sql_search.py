import sqlite3
import sqlglot
from sqlglot import exp
from langchain_core.tools import tool
from app.config import SQLITE_DB_PATH

# Schema context baked in so the LLM knows exactly what it's working with
SCHEMA_CONTEXT = """
Table: invoice_metadata
Columns:
  - document_id TEXT (primary key)
  - source_filename TEXT
  - vendor_name TEXT
  - invoice_number TEXT
  - invoice_date TEXT (format: YYYY-MM-DD)
  - total_amount REAL
  - tax_amount REAL
  - currency TEXT
  - category TEXT
  - line_items_json TEXT (JSON string, avoid filtering on this)
  - ingestion_time TEXT (ISO format)
"""

MAX_ROWS = 20


@tool
def search_invoices_sql(query: str) -> str:
    """
    Run a READ-ONLY SQL SELECT query against the invoice_metadata table.
    Use this for structured questions like:
    'Total spend by vendor', 'All invoices above $500', 'Invoices from last month',
    'How many invoices per category', 'What is the total tax amount'.

    Table: invoice_metadata
    Columns:
      - document_id TEXT (primary key)
      - source_filename TEXT
      - vendor_name TEXT
      - invoice_number TEXT
      - invoice_date TEXT (format: YYYY-MM-DD)
      - total_amount REAL
      - tax_amount REAL
      - currency TEXT
      - category TEXT
      - line_items_json TEXT (JSON string, avoid filtering on this)
      - ingestion_time TEXT (ISO format)

    Rules:
    - Only SELECT statements allowed
    - Always LIMIT to 20 rows unless user asks for more
    - Use invoice_date for date filtering (format: YYYY-MM-DD)
    - Do not query line_items_json for filtering
    """

    query = query.strip()
    if not query.upper().startswith("SELECT"):
        return "Error: Only SELECT queries are allowed."

    # Parse AST and enforce query cap
    try:
        expression = sqlglot.parse_one(query, read="sqlite")
        limit_node = expression.find(exp.Limit)
        if limit_node is None:
            expression = expression.limit(MAX_ROWS)
        else:
            try:
                current_limit = int(limit_node.expression.this)
                if current_limit > MAX_ROWS or current_limit <= 0:
                    limit_node.args["expression"] = exp.Literal.number(MAX_ROWS)
            except (ValueError, AttributeError):
                limit_node.args["expression"] = exp.Literal.number(MAX_ROWS)

        capped_query = expression.sql(dialect="sqlite")
    except Exception as e:
        return f"SQL Parsing Error: {str(e)}"

    # Execute query on read-only SQLite connection
    try:
        db_uri = f"file:{SQLITE_DB_PATH}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True)
        cursor = conn.cursor()
        cursor.execute(capped_query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        if not rows:
            return "No results found."

        result = [", ".join(columns)]
        for row in rows:
            result.append(", ".join(str(v) for v in row))

        return "\n".join(result)

    except Exception as e:
        return f"SQL Error: {str(e)}"