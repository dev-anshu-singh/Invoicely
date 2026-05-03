import os
from llama_cloud import LlamaCloud

from app.config import LLAMA_CLOUD_API_KEY
from app.models.schemas import InvoiceExtraction, SystemDocumentRecord
from app.prompts.templates import ingestion_prompt
from app.llm import get_extraction_llm

os.environ["LLAMA_CLOUD_API_KEY"] = LLAMA_CLOUD_API_KEY


def extract_invoice_llamacloud(file_path: str) -> str:
    client = LlamaCloud()
    file = client.files.create(file=file_path, purpose="parse")

    result = client.parsing.parse(
        file_id=file.id,
        tier="cost_effective",
        version="latest",
        expand=["markdown"]
    )

    return "\n\n".join(page.markdown for page in result.markdown.pages)


def structure_data_with_gemini(raw_markdown: str) -> InvoiceExtraction:
    llm = get_extraction_llm()

    structured_llm = llm.with_structured_output(InvoiceExtraction)
    chain = ingestion_prompt | structured_llm

    return chain.invoke({"raw_markdown": raw_markdown})


def process_invoice(file_path: str, filename: str) -> SystemDocumentRecord:
    
    raw_markdown = extract_invoice_llamacloud(file_path)
    extraction_obj = structure_data_with_gemini(raw_markdown)

    return SystemDocumentRecord(
        source_filename=filename,
        extraction_data=extraction_obj
    )