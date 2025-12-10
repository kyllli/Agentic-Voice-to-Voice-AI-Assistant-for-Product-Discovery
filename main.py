# main.py
import os
import pathlib
import base64
from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from dotenv import load_dotenv
load_dotenv()

from assistant_graph import run_pipeline
from audio_handler import AudioHandler

# ======================================================
# PATH CONFIG
# ======================================================
BASE_DIR = pathlib.Path(__file__).parent
DIST_DIR = BASE_DIR / "dist"

app = FastAPI(title="VoiceShop AI Assistant")
audio_handler = AudioHandler()

# ======================================================
# CORS
# ======================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# RESPONSE MODEL
# ======================================================
class VoiceResponse(BaseModel):
    transcript: str
    answer: str
    message: str | None = None
    products: list
    top3: list | None = None
    recommendations: list | None = None
    citations: dict
    audio: str
    audio_base64: str | None = None
    audioUrl: str | None = None


# ======================================================
# VOICE → ASR → PIPELINE → TTS
# ======================================================
@app.post("/api/voice", response_model=VoiceResponse)
async def voice_interaction(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    try:
        audio_bytes = await file.read()
        print("\n===== VOICE REQUEST RECEIVED =====")
        print(f"Uploaded file: {file.filename}, {len(audio_bytes)} bytes")

        # 1) ASR
        transcript = audio_handler.transcribe_audio(audio_bytes)
        print("ASR Transcript:", transcript)

        if not transcript or "Error" in transcript:
            raise HTTPException(status_code=500, detail="ASR failed")

        # 2) LangGraph Pipeline
        result = run_pipeline(transcript)
        print("Pipeline Result:", result)

        answer = result.get("final_answer", "Sorry, I couldn't process that.")
        products = result.get("products", [])
        citations = result.get("citations", {})

        # 3) TTS
        audio_path = audio_handler.text_to_speech(answer)
        if not audio_path or not os.path.exists(audio_path):
            raise HTTPException(status_code=500, detail="TTS generation failed")

        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        if background_tasks:
            background_tasks.add_task(os.remove, audio_path)

        print("===== PIPELINE COMPLETE =====\n")

        # 4) RETURN JSON TO UI
        return {
            "transcript": transcript,
            "answer": answer,
            "message": answer,            # UI also reads this
            "products": products,         # UI table uses this!!
            "top3": products,             # fallback for other UI versions
            "recommendations": products,  # fallback name
            "citations": citations,
            "audio": audio_b64,
            "audio_base64": audio_b64,
            "audioUrl": None,
        }

    except Exception as e:
        print("❌ ERROR in /api/voice:", e)
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================
# STATIC FILES (FRONTEND UI)
# ======================================================
if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="static")

    @app.get("/")
    async def index():
        return FileResponse(DIST_DIR / "index.html")
