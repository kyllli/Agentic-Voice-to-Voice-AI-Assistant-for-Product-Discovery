# server.py — Unified UI + MCP API + Voice Pipeline

import os
import pathlib
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from dotenv import load_dotenv
load_dotenv()

# Debug: confirm correct file is loading
print("🟩 Loaded server.py from:", __file__)

# Import our modules
from assistant_graph import run_pipeline
from audio_handler import AudioHandler

# Import MCP endpoints
from mcp_server.server import app as mcp_app


# ======================================================
# CONFIG
# ======================================================
BASE_DIR = pathlib.Path(__file__).parent
DIST_DIR = BASE_DIR / "dist"
audio_handler = AudioHandler()

root_app = FastAPI(title="Unified VoiceShop AI Assistant")

# CORS (UI requires this)
root_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================
# MOUNT MCP SERVER
# ======================================================
root_app.mount("/mcp", mcp_app)


# ======================================================
# RESPONSE MODEL FOR /api/voice
# ======================================================
class VoiceResponse(BaseModel):
    transcript: str
    answer: str
    message: str | None = None
    products: list
    citations: dict
    audio: str
    audio_base64: str | None = None
    audioUrl: str | None = None


# ======================================================
# FULL VOICE PIPELINE (ASR → LangGraph → TTS)
# ======================================================
@root_app.post("/api/voice", response_model=VoiceResponse)
async def voice_interaction(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    try:
        audio_bytes = await file.read()
        print("\n===== VOICE REQUEST RECEIVED =====")
        print(f"Uploaded file: {file.filename}, {len(audio_bytes)} bytes")

        # (1) ASR
        transcript = audio_handler.transcribe_audio(audio_bytes)
        print("ASR Transcript:", transcript)

        if not transcript or "Error" in transcript:
            raise HTTPException(status_code=500, detail="ASR failed")

        # (2) LangGraph pipeline
        result = run_pipeline(transcript)
        print("Pipeline Result:", result)

        answer = result.get("final_answer", "Sorry, I couldn't process that.")
        products = result.get("rag_results", [])
        citations = result.get("citations", {})

        clean_products = [
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "price": p.get("price"),
                "rating": p.get("rating"),
                "brand": p.get("brand"),
                "product_url": p.get("product_url"),
                "image_url": p.get("image_url"),
            }
            for p in products
        ]

        # (3) TTS
        audio_path = audio_handler.text_to_speech(answer)

        if not audio_path or not os.path.exists(audio_path):
            raise HTTPException(status_code=500, detail="TTS generation failed")

        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        if background_tasks:
            background_tasks.add_task(os.remove, audio_path)

        print("===== PIPELINE COMPLETE =====\n")

        return {
            "transcript": transcript,
            "answer": answer,
            "message": answer,
            "products": clean_products,
            "citations": citations,
            "audio": audio_b64,
            "audio_base64": audio_b64,
            "audioUrl": None,
        }

    except Exception as e:
        print("❌ ERROR in /api/voice:", e)
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================
# SERVE FRONTEND UI
# ======================================================
if DIST_DIR.exists():
    root_app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="static")

    @root_app.get("/")
    async def index():
        return FileResponse(DIST_DIR / "index.html")
