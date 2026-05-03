from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

class LineItem(BaseModel):
    description: str = Field(description="Name or description of the product/service")
    quantity: Optional[float] = Field(None, description="Quantity of items")
    unit_price: Optional[float] = Field(None, description="Price per unit")
    total: float = Field(description="Total cost for this line item")

class InvoiceExtraction(BaseModel):
    vendor_name: str = Field(description="Name of the company issuing the invoice")
    invoice_number: Optional[str] = Field(None, description="Unique invoice ID")
    invoice_date: str = Field(description="Date in YYYY-MM-DD format")
    total_amount: float = Field(description="Final total amount charged including taxes")
    tax_amount: Optional[float] = Field(0.0, description="Total tax applied")
    currency: str = Field("USD", description="3-letter currency code")
    category: str = Field(description="Expense category (e.g., 'SaaS', 'Travel')")
    summary: str = Field(description="2-3 sentence summary of the invoice")
    line_items: List[LineItem] = Field(default_factory=list, description="List of purchased items")

class SystemDocumentRecord(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ingestion_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    source_filename: str
    extraction_data: InvoiceExtraction