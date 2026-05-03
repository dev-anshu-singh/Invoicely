import chromadb
from langchain_core.tools import tool
from app.config import CHROMA_DB_PATH

# Initialize the Chroma client outside the function so it is ready immediately
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
chroma_collection = chroma_client.get_or_create_collection(name="invoice_vectors")


@tool
def search_invoice_contents(query: str) -> str:
    """
    Search the contents, summaries, and line items of all stored invoices.
    Use this tool when the user asks about specific items purchased,
    descriptions of services, or general semantic searches across document contents.
    Do NOT use this for calculating total spend or exact dates.
    """
    results = chroma_collection.query(
        query_texts=[query],
        n_results=5
    )

    if not results["documents"] or not results["documents"][0]:
        return "No matching invoice contents found."

    formatted_results = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        formatted_results.append(f"Vendor: {meta['vendor']}, Category: {meta['category']} - Info: {doc}")

    return "\n".join(formatted_results)