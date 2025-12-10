# # main.py
# import os
# import pathlib
# from fastapi import (
#     FastAPI,
#     HTTPException,
#     UploadFile,
#     File,
#     BackgroundTasks,
# )
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import FileResponse
# from pydantic import BaseModel

# from dotenv import load_dotenv
# load_dotenv()  # Load variables from .env (OPENAI_API_KEY, MCP_BASE_URL, etc.)

# from assistant_graph import run_pipeline
# from audio_handler import AudioHandler

# # ==============================
# # Path Configuration
# # ==============================
# BASE_DIR = pathlib.Path(__file__).parent
# DIST_DIR = BASE_DIR / "dist"   # Frontend build output (React/Vite/etc.)

# app = FastAPI(title="GenAI Final Project API")
# audio_handler = AudioHandler()

# # ==============================
# # CORS Settings (allow frontend to call backend)
# # ==============================
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],        # Replace with specific domains in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ==============================
# # Request/Response Models
# # ==============================
# class ASRResponse(BaseModel):
#     text: str

# class TTSRequest(BaseModel):
#     text: str

# # ==============================
# # Voice → (ASR → Agent → TTS) → Audio
# # ==============================
# @app.post("/api/voice")
# async def voice_interaction(
#     file: UploadFile = File(...),
#     background_tasks: BackgroundTasks = None,
# ):
#     """
#     End-to-end voice interaction:
#     1) Audio -> Text (ASR / Whisper)
#     2) Text -> Answer (LangGraph + MCP via run_pipeline)
#     3) Answer -> Audio (TTS)
#     Returns an MP3 file with the spoken answer.
#     """
#     try:
#         # 1) Read uploaded audio
#         audio_bytes = await file.read()
#         print("----- VOICE REQUEST RECEIVED -----")
#         print("Uploaded file:", file.filename, "size:", len(audio_bytes), "bytes")

#         # 2) ASR: audio -> transcript
#         transcript = audio_handler.transcribe_audio(audio_bytes)
#         print("ASR transcript:", transcript)

#         if isinstance(transcript, str) and transcript.startswith("Error in transcription:"):
#             raise HTTPException(status_code=500, detail=transcript)

#         # 3) Run multi-agent pipeline with transcript as query
#         try:
#             result = run_pipeline(transcript)
#         except Exception as e:
#             print("Error in run_pipeline:", e)
#             raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")

#         # Try to be robust about where the final answer is stored
#         answer = (
#             result.get("final_answer")
#             or result.get("answer")
#             or str(result)
#         )

#         print("Pipeline answer:", answer)

#         if not answer:
#             raise HTTPException(status_code=500, detail="Empty answer from pipeline.")

#         # 4) TTS: answer text -> audio file
#         audio_path = audio_handler.text_to_speech(answer)
#         print("Generated TTS file:", audio_path)

#         if audio_path is None or not os.path.exists(audio_path):
#             raise HTTPException(status_code=500, detail="TTS generation failed.")

#         # Schedule deletion of the temp file after the response is sent
#         if background_tasks is not None:
#             background_tasks.add_task(os.remove, audio_path)

#         print("Voice interaction completed successfully.")
#         print("----------------------------------")

#         return FileResponse(
#             audio_path,
#             media_type="audio/mpeg",
#             filename="response.mp3",
#         )

#     except HTTPException:
#         # Let FastAPI handle HTTPException normally
#         raise
#     except Exception as e:
#         print("Unexpected error in /api/voice:", e)
#         raise HTTPException(status_code=500, detail=f"Voice pipeline failed: {str(e)}")


# # ==============================
# # Serve Frontend Static Files
# # ==============================
# if DIST_DIR.exists():
#     # Mount frontend as the root path. Routes such as /, /chat, /settings
#     # will be handled by the frontend.
#     app.mount(
#         "/",
#         StaticFiles(directory=str(DIST_DIR), html=True),
#         name="static",
#     )

#     @app.get("/")
#     async def index():
#         """Return the main index.html file."""
#         return FileResponse(DIST_DIR / "index.html")

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

# ==============================
# Path Configuration
# ==============================
BASE_DIR = pathlib.Path(__file__).parent
DIST_DIR = BASE_DIR / "dist"

app = FastAPI(title="GenAI Final Project API")
audio_handler = AudioHandler()

# ==============================
# CORS
# ==============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# Models
# ==============================
class ASRResponse(BaseModel):
    text: str

class TTSRequest(BaseModel):
    text: str

class VoiceResponse(BaseModel):
    transcript: str
    answer: str
    products: list
    citations: dict
    audio_base64: str


# ==============================
# Voice → (ASR → Agent → TTS) → JSON + base64 audio
# ==============================
@app.post("/api/voice", response_model=VoiceResponse)
async def voice_interaction(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    """
    End-to-end voice interaction:
    1) Audio -> Text (ASR / Whisper)
    2) Text -> Answer (LangGraph + MCP via run_pipeline)
    3) Answer -> Audio (TTS)
    Returns JSON with transcript, answer, and base64-encoded MP3 audio.
    """
    try:
        # 1) Read uploaded audio
        audio_bytes = await file.read()
        print("----- VOICE REQUEST RECEIVED -----")
        print("Uploaded file:", file.filename, "size:", len(audio_bytes), "bytes")

        # 2) ASR: audio -> transcript
        transcript = audio_handler.transcribe_audio(audio_bytes)
        print("ASR transcript:", transcript)

        if isinstance(transcript, str) and transcript.startswith("Error in transcription:"):
            raise HTTPException(status_code=500, detail=transcript)

        # 3) Run multi-agent pipeline with transcript as query
        try:
            result = run_pipeline(transcript)
        except Exception as e:
            print("Error in run_pipeline:", e)
            raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")

        # Extract final answer
        answer = (
            result.get("final_answer")
            or result.get("answer")
            or str(result)
        )
        products = result.get("products", [])
        citations = result.get("citations", {})

        print("Pipeline answer:", answer)

        if not answer:
            raise HTTPException(status_code=500, detail="Empty answer from pipeline.")

        # 4) TTS: answer text -> audio file
        audio_path = audio_handler.text_to_speech(answer)
        print("Generated TTS file:", audio_path)

        if audio_path is None or not os.path.exists(audio_path):
            raise HTTPException(status_code=500, detail="TTS generation failed.")

        # Read audio file and encode as base64
        with open(audio_path, "rb") as f:
            audio_bytes_out = f.read()
        audio_b64 = base64.b64encode(audio_bytes_out).decode("utf-8")

        # Delete temp file after response (optional, but clean)
        if background_tasks is not None:
            background_tasks.add_task(os.remove, audio_path)

        print("Voice interaction completed successfully.")
        print("----------------------------------")

        return VoiceResponse(
            transcript=transcript,
            answer=answer,
            products=products,
            citations=citations,
            audio_base64=audio_b64,
        )

    except HTTPException:
        raise
    except Exception as e:
        print("Unexpected error in /api/voice:", e)
        raise HTTPException(status_code=500, detail=f"Voice pipeline failed: {str(e)}")


# ==============================
# Serve Frontend Static Files
# ==============================
if DIST_DIR.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(DIST_DIR), html=True),
        name="static",
    )

    @app.get("/")
    async def index():
        """Return the main index.html file."""
        return FileResponse(DIST_DIR / "index.html")
