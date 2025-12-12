# 🚀 VoiceShop — Voice-to-Voice Multimodal RAG Assistant
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/Frontend-React-61DAFB.svg)](https://react.dev/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![MCP](https://img.shields.io/badge/Protocol-MCP-black.svg)](https://modelcontextprotocol.io/)
[![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-green.svg)](https://docs.trychroma.com/)

VoiceShop is a multimodal, voice-driven shopping assistant that retrieves grounded product recommendations from a curated Amazon dataset and optionally refreshes results with live web information.  
The system integrates **LangGraph multi-agent orchestration**, **MCP tools**, **private RAG**, **Whisper ASR**, **TTS**, and a **React UI** to support an end-to-end voice-to-voice product search experience.

---

## ✨ Features
- 🎤 **Voice Input & Voice Output** (Whisper ASR + TTS)
- 🤖 **Multi-Agent Pipeline**: Router → Planner → Retriever → Reconciler → Answerer  
- 🧠 **Private RAG Retrieval** (Amazon Toys & Games slice, 6,662 products)
- 🌐 **Optional Live Web Comparison** for prices/availability
- 📚 **Full Prompt Disclosure** included in `/prompts`
- 🖥️ **React UI** with mic input, transcripts, agent logs, and product panel

---

## 📂 Repository Structure

- assistant_graph.py — LangGraph multi-agent workflow (Router → Planner → Retriever → Answerer)
- audio_handler.py — Whisper ASR + TTS processing
- main.py — Backend orchestrator connecting ASR, agents, MCP tools, and TTS
- mcp_client.py — Helper for calling MCP tools from the backend

- mcp_server/ — MCP server exposing rag.search and web.search
- prompts/ — All agent + system prompts (Prompt Disclosure)
- rag/ — Private RAG pipeline: cleaning, embedding, and vector index search

- src/ — React UI (mic input, transcripts, agent logs, product panel)
- data/ — Cleaned dataset and generated Chroma index (local only)

- .env.example — Environment template
- .gitignore
- requirements.txt
- README.md

---

## 📊 Dataset Summary

We curated the **Amazon 2020 Toys & Games** category, producing a clean subset of **6,662 products**.  
The dataset lacks **brand** and **rating**, but we preserve these schema fields for compatibility with Amazon’s structure and future extensions.

Each product is embedded using a sentence-transformer model and stored in a ChromaDB index for hybrid semantic + metadata retrieval.

---

## 🧩 Multi-Agent System (LangGraph)

We use four specialized agents to ensure structured reasoning and grounded tool-use:

- **Router** — interprets user intent, constraints, and signals such as “needs live price.”
- **Planner** — selects tools (rag.search, web.search) and formulates an execution plan.
- **Retriever** — calls the MCP tools and gathers evidence.
- **Reconciler / Answerer** — merges private + live data and generates the grounded final response.

This design provides a deterministic, transparent pipeline where each agent has a clear role.

---

## 🔌 MCP Tools

### **rag.search**
Retrieves structured product data from the private ChromaDB index.  
Used for all primary recommendations.

### **web.search**
Fetches live price or availability when users ask for *“latest price,” “current,” “under \$X,”* etc.  
Used selectively to reduce latency.

Together, these tools provide grounded, reproducible, and up-to-date product information.

---

## 📁 Prompt Disclosure

All system and agent prompts required for grading are included in prompts folder
- system.txt
- router.txt
- planner.txt
- answerer.txt


These define the behaviors of all agents in the LangGraph pipeline.

---

## 🧑‍💻 Acknowledgements

Developed for the University of Chicago **Applied Generative AI** course.  
Built with LangGraph, MCP, Whisper, and ChromaDB.

