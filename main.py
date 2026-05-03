from fastapi import FastAPI
from app.routers import upload

app = FastAPI(
    title="Invoicely POC",
    description="AI-Powered Invoice Ingestion Engine",
)

# Attach your router
app.include_router(upload.router, tags=["Ingestion"])

@app.get("/")
def health_check():
    return {"status": "Invoicely API is running!"}