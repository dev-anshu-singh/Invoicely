from fastapi import APIRouter
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from app.services.chat_graph import chat_graph

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/chat")
def chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.session_id}}

    result = chat_graph.invoke(
        {"messages": [HumanMessage(content=req.message)]},
        config=config
    )

    return {"reply": result["messages"][-1].content}