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
from rag.search import normalize_url


# ======================================================
# 0. Domain Setup — Toys & Games Only
# ======================================================

ALLOWED_CATEGORIES = [
    "toy", "toys", "games", "game", "board game", "board games",
    "puzzle", "puzzles", "action figure", "action figures",
    "kids toy", "children toy", "plush", "lego"
]


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
    products: List[Dict[str, Any]]  # for UI table


initial_state: State = {
    "query": "",
    "intent": {},
    "constraints": {},
    "plan": {},
    "rag_results": [],
    "web_results": [],
    "final_answer": "",
    "citations": {},
    "products": [],
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
# 3. Router Agent (UPDATED)
# ======================================================

def router_node(state: State):
    query = state["query"].strip()

    # ---------- 0. Hard-coded greeting check (no LLM needed) ----------
    lower_q = query.lower()
    simple_greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]

    if any(lower_q == g or lower_q.startswith(g + ",") for g in simple_greetings):
        state["intent"] = {"intent_type": "greeting"}
        state["final_answer"] = "Hello! What product can I help you find today?"
        state["products"] = []
        print("🔎 Router Output: greeting")
        return state

    system_prompt = """
You are an intent classification agent for an e-commerce shopping assistant.

If the user message is casual (e.g., "hello", "hi", "hey", "what's up", "how are you"),
DO NOT classify a product intent.
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
    except Exception:
        intent = {"error": "JSON parsing failed", "raw": response.content}

    # ---------- 1. Greeting ----------
    if intent.get("intent_type") == "greeting":
        state["intent"] = {"intent_type": "greeting"}
        state["final_answer"] = "Hello! What product can I help you find today?"
        state["products"] = []
        print("🔎 Router Output (LLM greeting):", intent)
        return state

    # ---------- 2. Out-of-domain detection (still a product_query, but not toys/games) ----------
    product_type = (intent.get("product_type") or "").lower()
    is_in_domain = any(keyword in product_type for keyword in ALLOWED_CATEGORIES)

    if product_type and not is_in_domain:
        state["intent"] = {"intent_type": "out_of_domain", "product_type": product_type}
        state["final_answer"] = (
            "Sorry — my product database currently focuses on Toys & Games. "
            "I might not have good recommendations for this category. "
            "Try asking for a toy, puzzle, board game, LEGO set, or kids item."
        )
        state["products"] = []
        print("🔎 Router Output: out_of_domain", intent)
        return state

    # ---------- 3. Normal product query ----------
    state["intent"] = intent
    state["constraints"] = intent.get("constraints", {})

    print("🔎 Router Output:", intent)
    return state


# ======================================================
# 4. Planner Agent (skip for non-product intents)
# ======================================================

def planner_node(state: State):
    intent = state.get("intent", {})
    if intent.get("intent_type") != "product_query":
        # For greeting / out_of_domain, no plan needed
        return state

    constraints = state.get("constraints", {})

    system_prompt = """
You are the Planner agent in a multi-agent e-commerce system using LangGraph.

Your job:
1. Determine which tools to call:
   - "rag.search" → always needed for structured product data.
   - "web.search" → only if user needs real-time price/availability.

2. Produce:
   {
     "tools": ["rag.search", "web.search"],
     "fields_needed": ["price", "rating", "ingredients"],
     "reason": "...",
     "conflict_policy": "web_price_overwrites"
   }

Rules:
- RAG always first.
- Add web.search only if needs_live_price is true.
- Include fields based on constraints (price, material, etc.).

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
    except Exception:
        plan = {"error": "JSON parsing failed", "raw": response.content}

    state["plan"] = plan
    print("🧭 Planner Output:", plan)
    return state


# ======================================================
# 5. Retriever Agent — MCP Tools (UPDATED constraints for RAG)
# ======================================================

def retriever_node(state: State):
    intent = state.get("intent", {})
    if intent.get("intent_type") != "product_query":
        # No retrieval for greeting / out_of_domain
        return state

    plan = state.get("plan", {})
    tools = plan.get("tools", []) or []

    query = state["query"]
    raw_constraints = state.get("constraints", {}) or {}

    # Only forward SAFE constraints to RAG (avoid strict brand/category filters)
    rag_constraints: Dict[str, Any] = {}
    if "budget" in raw_constraints:
        rag_constraints["budget"] = raw_constraints["budget"]

    # ---------- RAG first ----------
    if "rag.search" in tools:
        rag_results = call_rag_tool(
            query=query,
            constraints=rag_constraints,
            max_results=5,
        )
        state["rag_results"] = rag_results
        print("📘 RAG Results:", rag_results)

    # ---------- Optional Web Search ----------
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
# 6. Answerer Agent (respects greeting / out_of_domain)
# ======================================================

def answerer_node(state: State):
    intent = state.get("intent", {})
    intent_type = intent.get("intent_type")

    # ---------- 0. For greeting / out_of_domain, do NOT overwrite router's answer ----------
    if intent_type in ("greeting", "out_of_domain"):
        # Ensure UI table is empty in these cases
        state["products"] = []
        return state

    rag = state.get("rag_results", []) or []
    web = state.get("web_results", []) or []
    constraints = state.get("constraints", {}) or {}

    # ---------- 1. If no RAG results → fallback ----------
    if not rag:
        state["products"] = []
        state["final_answer"] = (
            "Sorry, I couldn't find matching products. "
            "Try adjusting your budget or adding more details."
        )
        return state

    # ---------- 2. Select Top 3 products ----------
    def score(p):
        r = p.get("rating", 0) or 0
        price = p.get("price")
        s = r
        budget = constraints.get("budget")
        if budget and price and price > budget:
            s -= 2
        return s

    sorted_items = sorted(rag, key=score, reverse=True)
    top3 = sorted_items[:3]

    # ---------- 3. Merge Web Pricing when matched by fuzzy title ----------
    import difflib

    def fuzzy(a, b):
        return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

    for p in top3:
        title = p.get("title", "")
        for w in web:
            if fuzzy(title, w.get("title", "")) > 0.55 and w.get("price"):
                p["price"] = w["price"]

    # ---------- 4. Normalize metadata for UI ----------
    normalized: List[Dict[str, Any]] = []
    for p in top3:
        normalized.append({
            "id": p.get("id"),
            "title": p.get("title", "Unnamed Product"),
            "brand": p.get("brand", ""),
            "price": p.get("price"),
            "rating": p.get("rating"),
            "ingredients": p.get("ingredients", ""),
            "features": p.get("features", ""),
            "product_url": normalize_url(p.get("product_url", "")),
            "image_url": normalize_url(p.get("image_url", "")),
            "doc_id": p.get("doc_id")
        })

    state["products"] = normalized

    # ---------- 5. Top Pick → natural language answer ----------
    top_pick = normalized[0]

    system_prompt = f"""
You are an e-commerce shopping assistant.
Generate a SHORT (<15 seconds) spoken answer about the *single Top Pick* product ONLY.

Rules:
- DO NOT mention or compare other products.
- ONLY use actual fields from the Top Pick:
      title
      brand
      rating (ONLY if > 0)
      price (ONLY if > 0)
      features (optional)
- If rating is missing, None, or -1 → do NOT mention rating.
- If price is missing or <= 0 → do NOT mention price.
- Keep the tone friendly, concise, and natural.
- DO NOT guess or invent any facts, numbers, or features.
- DO NOT reference UI buttons or choices.
- End with:
  "I've sent details and sources to your screen. If you'd like a cheaper, premium, or more balanced option, just let me know."

Top Pick (JSON):
{json.dumps(top_pick, indent=2)}

Output ONLY the spoken answer (no JSON, no explanations).
"""

    response = answer_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content="Generate answer.")
    ])

    state["final_answer"] = response.content.strip()

    print("\n🧠 Final Answer:", state["final_answer"])
    print("🛒 Products returned to UI:", normalized)
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
    result = run_pipeline("Recommend an eco-friendly LEGO brick set under $100")
    print("\n=== FINAL ANSWER ===")
    print(result["final_answer"])
    print("\n=== PRODUCTS ===")
    print(result["products"])
