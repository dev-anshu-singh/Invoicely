import operator
from typing import Annotated
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage

from app.prompts.templates import CHAT_SYSTEM_PROMPT
from app.llm import get_chat_llm
from app.services.tools.vector_search import search_invoices_vector
from app.services.tools.sql_search import search_invoices_sql

tools = [search_invoices_vector, search_invoices_sql]


# 1. Define custom state with a steps counter
class AgentState(MessagesState):
    # Annotated with operator.add means every time a node returns {"steps": 1},
    # LangGraph will add 1 to the existing total, rather than overwriting it.
    steps: Annotated[int, operator.add]


def build_chat_graph():
    llm = get_chat_llm()
    llm_with_tools = llm.bind_tools(tools)

    def call_llm(state: AgentState):
        messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        # Always increment the step counter when the LLM is called
        return {"messages": [response], "steps": 1}

    def fallback_node(state: AgentState):
        # 4. The Fallback Node: Explains the failure and forces a vector-only answer
        fallback_prompt = SystemMessage(
            content="SYSTEM OVERRIDE: The maximum number of database tool attempts (3) has been reached. You cannot use the SQL database tool anymore for this query. Apologize to the user that you couldn't perform the exact numerical database search due to technical constraints. Provide the best possible answer using ONLY semantic/conceptual information you might have gathered from the vector search or general context. Do NOT attempt to call any more tools."
        )
        messages = state["messages"] + [fallback_prompt]

        # Call the raw LLM (no tools bound) to ensure it just generates text and ends
        final_response = llm.invoke(messages)
        return {"messages": [final_response]}

    # 2. Custom Router logic
    def route_after_llm(state: AgentState):
        # 3. The Circuit Breaker: Enforce the strict 3-iteration limit
        if state.get("steps", 0) >= 3:
            return "fallback"

        last_message = state["messages"][-1]

        # If the LLM output tool calls, route to the tools node
        if last_message.tool_calls:
            return "tools"

        # If no tool calls, it's a normal final text response
        return END

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("llm", call_llm)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("fallback", fallback_node)

    # Add edges
    graph.add_edge(START, "llm")

    # Use our custom router instead of the default tools_condition
    graph.add_conditional_edges("llm", route_after_llm, {
        "tools": "tools",
        "fallback": "fallback",
        END: END
    })

    graph.add_edge("tools", "llm")
    graph.add_edge("fallback", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


chat_graph = build_chat_graph()