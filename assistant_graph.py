# assistant_graph.py
# -------------------------------------------------------
# Multi-Agent LangGraph pipeline for product discovery
# Integrated with MCP rag.search + web.search tools
# -------------------------------------------------------

import os
import json
from typing import Dict, Any, List, Optional
from typing import TypedDict

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

# Import MCP client (your custom module)
from mcp_client import call_rag_tool, call_web_tool


# ======================================================
# 1. Shared State Definition
# ======================================================

class State(TypedDict, total=False):
    query: str
    intent: Dict[str, Any]
    constraints: Dict[str, Any]
    plan: Dict[str, Any]
    rag_results: List[Dict[str, Any]]
    web_results: List[Dict[str, Any]]
    final_answer: str
    citations: Dict[str, Any]


initial_state: State = {
    "query": "",
    "intent": {},
    "constraints": {},
    "plan": {},
    "rag_results": [],
    "web_results": [],
    "final_answer": "",
    "citations": {}
}


# ======================================================
# 2. LLM Setup
# ======================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("⚠️ Warning: OPENAI_API_KEY not found in environment variables.")

router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
planner_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
answer_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ======================================================
# 3. Router Agent
# ======================================================

def router_node(state: State):
    query = state["query"]

    system_prompt = """
You are an intent classification agent for an e-commerce product assistant.

Extract the following fields as JSON:
- "product_type": what product is the user looking for
- "constraints": dictionary containing:
    * budget (numeric if possible)
    * brand (string)
    * material (string)
    * category (string)
- "needs_live_price": true/false (true if query contains 'current', 'latest', 'now', 'today')

Output JSON only.
"""

    response = router_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=query)
    ])

    try:
        intent = json.loads(response.content)
    except:
        intent = {"error": "JSON parsing failed", "raw": response.content}

    state["intent"] = intent
    state["constraints"] = intent.get("constraints", {})

    print("🔎 Router Output:", intent)
    return state


# ======================================================
# 4. Planner Agent
# ======================================================

def planner_node(state: State):
    intent = state["intent"]
    constraints = state["constraints"]

    system_prompt = """
You are the Planner agent in a multi-agent e-commerce system using LangGraph.

Your job:
1. Determine which tools to call:
   - "rag.search" → always needed to retrieve structured product data.
   - "web.search" → only if user needs real-time or latest price/availability.

2. Create a clear execution plan:
   {
     "tools": ["rag.search", "web.search"],
     "fields_needed": ["price", "rating", "ingredients"],
     "reason": "Why these tools in this order",
     "conflict_policy": "web_price_overwrites" or "prefer_private_price"
   }

Rules:
- RAG always used first for product grounding.
- If `needs_live_price` is true, add web.search.
- If budget constraints exist, ensure "price" in fields_needed.
- If materials or ingredients are constraints, add "ingredients".

Output JSON only.
"""

    response = planner_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps({
            "intent": intent,
            "constraints": constraints
        }))
    ])

    try:
        plan = json.loads(response.content)
    except:
        plan = {"error": "JSON parsing failed", "raw": response.content}

    state["plan"] = plan
    print("🧭 Planner Output:", plan)
    return state


# ======================================================
# 5. Retriever Agent — MCP Tools
# ======================================================

def retriever_node(state: State):
    """
    Executes the tools specified by the planner using real MCP tools.
    """
    plan = state.get("plan", {})
    tools = plan.get("tools", [])

    query = state["query"]
    constraints = state.get("constraints", {})

    # Run RAG first
    if "rag.search" in tools:
        rag_results = call_rag_tool(
            query=query,
            constraints=constraints,
            max_results=5,
        )
        state["rag_results"] = rag_results
        print("📘 RAG Results:", rag_results)

    # Then optionally Web Search
    if "web.search" in tools:
        web_results = call_web_tool(
            query=query,
            max_results=3,
        )
        state["web_results"] = web_results
        print("🌐 Web Results:", web_results)

    print("🔎 Retriever step completed.\n")
    return state


# ======================================================
# 6. Answerer Agent
# ======================================================

def answerer_node(state: State):
    rag = state.get("rag_results", [])
    web = state.get("web_results", [])

    system_prompt = """
You are the Answerer agent in a multi-agent LangGraph e-commerce system.

Your responsibilities:
1. Combine private-catalog (rag.search) data and optional live web data.
2. Use rag data for product identity, features, brand, ingredients, rating.
3. Use web data for *latest price* if available.
4. Conflict resolution:
   - If both rag and web have price → use web price (live).
5. Generate citations:
   {
     "rag": ["doc_id1", "doc_id2"],
     "web": ["url1"]
   }
6. Output JSON:
{
  "answer": "...",
  "citations": { "rag": [...], "web": [...] }
}
"""

    response = answer_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps({
            "rag": rag,
            "web": web
        }))
    ])

    try:
        result = json.loads(response.content)
    except:
        result = {
            "answer": "Error producing answer.",
            "citations": {}
        }

    state["final_answer"] = result.get("answer", "")
    state["citations"] = result.get("citations", {})

    print("🧠 Final Answer:", state["final_answer"])
    print("📚 Citations:", state["citations"])

    return state


# ======================================================
# 7. Build LangGraph
# ======================================================

graph = StateGraph(State)

graph.add_node("router", router_node)
graph.add_node("planner", planner_node)
graph.add_node("retriever", retriever_node)
graph.add_node("answerer", answerer_node)

graph.set_entry_point("router")

graph.add_edge("router", "planner")
graph.add_edge("planner", "retriever")
graph.add_edge("retriever", "answerer")
graph.add_edge("answerer", END)

app = graph.compile()


# ======================================================
# 8. Public Function
# ======================================================

def run_pipeline(query: str):
    """
    Call this function from your Streamlit UI or CLI.
    """
    state = initial_state.copy()
    state["query"] = query
    return app.invoke(state)


# ======================================================
# 9. Manual Test
# ======================================================

if __name__ == "__main__":
    result = run_pipeline("Recommend an eco-friendly stainless steel cleaner under $15")
    print("\n=== FINAL ANSWER ===")
    print(result["final_answer"])
    print("\n=== CITATIONS ===")
    print(result["citations"])
