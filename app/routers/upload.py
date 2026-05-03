import os
import shutil
from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from app.services.ingestion_logic import process_invoice
from app.db.database import setup_databases, save_to_databases

router = APIRouter()

# Initialize databases when the router loads
sqlite_conn, chroma_collection = setup_databases()


def process_and_store(file_path: str, filename: str):
    try:
        final_record = process_invoice(file_path, filename)
        save_to_databases(final_record, sqlite_conn, chroma_collection)
    except Exception as e:
        print(f"Error processing {filename}: {e}")
    finally:
        # Always clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/upload")
async def upload_invoice(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    temp_file_path = f"temp_{file.filename}"

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Send to background so the user gets an instant response
    background_tasks.add_task(process_and_store, temp_file_path, file.filename)

    return {
        "message": "Invoice received and processing started.",
        "filename": file.filename
    }