from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage

from app.prompts.templates import CHAT_SYSTEM_PROMPT

from app.llm import get_chat_llm
from app.services.tools.vector_search import search_invoices_vector
from app.services.tools.sql_search import search_invoices_sql

tools = [search_invoices_vector, search_invoices_sql]

def build_chat_graph():
    llm = get_chat_llm()
    llm_with_tools = llm.bind_tools(tools)

    def call_llm(state: MessagesState):
        messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)] + state["messages"]
        return {"messages": [llm_with_tools.invoke(messages)]}

    graph = StateGraph(MessagesState)
    graph.add_node("llm", call_llm)
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "llm")
    graph.add_conditional_edges("llm", tools_condition)
    graph.add_edge("tools", "llm")
    graph.add_edge("llm", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)

chat_graph = build_chat_graph()