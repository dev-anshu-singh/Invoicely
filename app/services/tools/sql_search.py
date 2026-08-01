import sqlite3
import sqlglot
from sqlglot import exp
from langchain_core.tools import tool
from langchain_community.utilities import SQLDatabase
from app.config import SQLITE_DB_PATH

MAX_ROWS = 20

# Initialize the LangChain SQLDatabase utility for dynamic schema inspection
db = SQLDatabase.from_uri(f"sqlite:///{SQLITE_DB_PATH}", sample_rows_in_table_info=3)


@tool
def search_invoices_sql(query: str) -> str:
    """
    Run a READ-ONLY SQL SELECT query against the database.
    Use this for structured questions like:
    'Total spend by vendor', 'All invoices above $500', 'Invoices from last month',
    'How many invoices per category', 'What is the total tax amount'.

    Database Context:
    {db_context}

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

    # Execute query on read-only SQLite connection with a strict timeout
    try:
        db_uri = f"file:{SQLITE_DB_PATH}?mode=ro"
        # The timeout=2.0 ensures the agent doesn't hang on bad queries
        conn = sqlite3.connect(db_uri, uri=True, timeout=2.0)
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


# Inject the dynamic schema into the tool's docstring so the LLM sees it
search_invoices_sql.__doc__ = search_invoices_sql.__doc__.format(
    db_context=db.get_table_info()
)