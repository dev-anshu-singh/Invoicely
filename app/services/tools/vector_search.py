from langchain_core.tools import tool
from app.routers.upload import chroma_collection

@tool
def search_invoices_vector(query: str) -> str:
    """
    Search invoices using semantic similarity.
    Use this to answer questions like:
    'Find invoices related to cloud software' or 'Any travel expenses?'
    """
    results = chroma_collection.query(
        query_texts=[query],
        n_results=5
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    if not docs:
        return "No relevant invoices found."

    output = []
    for doc, meta in zip(docs, metas):
        output.append(
            f"- Vendor: {meta.get('vendor')} | Category: {meta.get('category')}\n  {doc}"
        )

    return "\n".join(output)



