import sqlite3
import json
from app.config import SQLITE_DB_PATH, CHROMA_DB_PATH

import chromadb
from app.models.schemas import SystemDocumentRecord


def setup_databases():
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    cursor = sqlite_conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_metadata (
            document_id TEXT PRIMARY KEY,
            source_filename TEXT,
            vendor_name TEXT,
            invoice_number TEXT,
            invoice_date TEXT,
            total_amount REAL,
            tax_amount REAL,
            currency TEXT,
            category TEXT,
            needs_review INTEGER,
            line_items_json TEXT,
            ingestion_time TEXT
        )
    """)
    sqlite_conn.commit()

    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    chroma_collection = chroma_client.get_or_create_collection(name="invoice_vectors")

    return sqlite_conn, chroma_collection


def save_to_databases(doc_record: SystemDocumentRecord, sqlite_conn, chroma_collection):
    cursor = sqlite_conn.cursor()

    line_items_str = json.dumps([item.model_dump() for item in doc_record.extraction_data.line_items])

    cursor.execute("""
        INSERT INTO invoice_metadata
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        doc_record.document_id,
        doc_record.source_filename,
        doc_record.extraction_data.vendor_name,
        doc_record.extraction_data.invoice_number,
        doc_record.extraction_data.invoice_date,
        doc_record.extraction_data.total_amount,
        doc_record.extraction_data.tax_amount,
        doc_record.extraction_data.currency,
        doc_record.extraction_data.category,
        int(doc_record.extraction_data.needs_review),
        line_items_str,
        doc_record.ingestion_time
    ))
    sqlite_conn.commit()

    text_chunk = f"Summary: {doc_record.extraction_data.summary} "
    if doc_record.extraction_data.line_items:
        items = ", ".join([item.description or 'Unknown' for item in doc_record.extraction_data.line_items])
        text_chunk += f"Items purchased: {items}"

    chroma_collection.add(
        documents=[text_chunk],
        metadatas=[{
            "doc_id": doc_record.document_id,
            "vendor": doc_record.extraction_data.vendor_name,
            "category": doc_record.extraction_data.category
        }],
        ids=[doc_record.document_id]
    )