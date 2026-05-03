from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import GEMINI_MODEL_NAME, GEMINI_CHAT_MODEL_NAME

def get_extraction_llm():
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL_NAME,
        temperature=0
    )

def get_chat_llm():
    return ChatGoogleGenerativeAI(model=GEMINI_CHAT_MODEL_NAME, temperature=0.7)