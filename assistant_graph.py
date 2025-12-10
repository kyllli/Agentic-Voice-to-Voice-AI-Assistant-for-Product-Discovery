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

from dotenv import load_dotenv
load_dotenv()

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
You are an intent classification agent for an e-commerce shopping assistant.

If the user message is casual (e.g., "hello", "hi", "hey", "what's up", "how are you"),
DO NOT try to classify a product intent.
Instead return:
{
  "intent_type": "greeting"
}

Otherwise extract:
{
  "intent_type": "product_query",
  "product_type": "...",
  "constraints": {
      "budget": number,
      "brand": "...",
      "material": "...",
      "category": "..."
  },
  "needs_live_price": true/false
}

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
    
    if intent.get("intent_type") == "greeting":
        state["final_answer"] = "Hello! What product can I help you find today?"
        return state

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
    constraints = state.get("constraints", {})

    # ✨ Basic cleaning-product filtering to avoid RC boat parts
    CLEAN_KEYWORDS = ["clean", "cleaner", "polish", "spray", "degreaser", "surface", "stainless"]
    def is_relevant(prod):
        title = prod.get("title", "").lower()
        return any(k in title for k in CLEAN_KEYWORDS)

    rag_filtered = [p for p in rag if is_relevant(p)]

    # use first 3 highest-rating products
    def rating_of(p):
        return p.get("rating", 0) or 0
    
    top3 = sorted(rag_filtered, key=rating_of, reverse=True)[:3]

    # Fallback if filtering removed everything
    if not top3:
        top3 = rag[:3]

    # Build price lookup from web search results
    web_price_map = {}
    for w in web:
        title = w.get("title", "").lower()
        price = w.get("price")
        if price:
            web_price_map[title] = price

    # Assign "live" price if title matches (fuzzy match via containment)
    import difflib
    for p in top3:
        title = p.get("title", "").lower()
        best_match = None
        best_score = 0
        for w_title in web_price_map.keys():
            score = difflib.SequenceMatcher(None, title, w_title).ratio()
            if score > best_score and score > 0.5:
                best_match = w_title
                best_score = score
        if best_match:
            p["price"] = web_price_map[best_match]

    # Identify top pick
    top_pick = top3[0] if top3 else None

    # Extract essential fields for LLM
    llm_payload = {
        "top_pick": top_pick,
        "alternatives": top3[1:],
        "constraints": constraints
    }

    system_prompt = """
You are the Answerer agent in a product recommendation system.

Your task:
- Generate a SHORT (<15 seconds), natural, spoken-style answer.
- ALWAYS mention:
   * the top pick's FULL NAME,
   * its AVERAGE RATING (e.g. "4.6 stars"),
   * its PRICE (e.g. "typically around $12.49"),
   * one useful FEATURE (ingredients or eco-friendly property).
- Then say you compared two alternatives.
- Then say “I've sent details and sources to your screen.”
- Then ALWAYS finish with: “Would you like the most affordable or the highest rated?”

Use this JSON structure in your output:
{
  "answer": "...",
  "products": [... top 3 products ...],
  "citations": {
      "rag": [...],
      "web": [...]
  }
}

DO NOT invent prices or ratings. ONLY use numbers provided in the input JSON.
If rating is missing, say "well rated".
If price is missing, say "budget friendly".
"""

    response = answer_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(llm_payload))
    ])

    # Parse safely
    try:
        result = json.loads(response.content)
    except:
        result = {
            "answer": "Here are three options. I've sent details to your screen.",
            "products": top3,
            "citations": {"rag": [], "web": []}
        }

    # Save to state
    state["final_answer"] = result.get("answer", "")
    state["products"] = result.get("products", top3)
    state["citations"] = result.get("citations", {})

    print("🧠 Final Answer:", state["final_answer"])
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
