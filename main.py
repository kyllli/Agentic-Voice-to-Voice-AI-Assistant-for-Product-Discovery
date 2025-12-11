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

        # 3) TTS
        audio_path = audio_handler.text_to_speech(answer)
        if not audio_path or not os.path.exists(audio_path):
            raise HTTPException(status_code=500, detail="TTS generation failed")

        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        if background_tasks:
            background_tasks.add_task(os.remove, audio_path)

        print("===== PIPELINE COMPLETE =====\n")
        print(f"top3: {clean_products}")

        # 4) RETURN JSON TO UI
        return {
            "transcript": transcript,
            "answer": answer,
            "message": answer,            # UI also reads this
            "products": clean_products,         # UI table uses this!!
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

# Pipeline Result: {
#     'query': 'Recommend a eco-friendly cleaner under $15.', 
#     'intent': {'intent_type': 'product_query', 'product_type': 'cleaner', 'constraints': {'budget': 15, 'brand': None, 'material': 'eco-friendly', 'category': 'cleaning supplies'}, 'needs_live_price': True}, 
#     'constraints': {'budget': 15, 'brand': None, 'material': 'eco-friendly', 'category': 'cleaning supplies'}, 
#     'plan': {'tools': ['rag.search', 'web.search'], 'fields_needed': ['price', 'ingredients'], 'reason': 'RAG is used first to retrieve structured product data about eco-friendly cleaners, and web.search is needed to get the latest price due to the budget constraint.', 'conflict_policy': 'web_price_overwrites'}, 
#     'rag_results': [{'id': 'e7a8c164491f89ca4bdff2b6dc436f8f', 'title': 'Stephen Joseph Recycled Bag Sets', 'price': 9.99, 'rating': -1.0, 'brand': '', 'subcategory': "Clothing, Shoes & Jewelry | Luggage & Travel Gear | Backpacks | Kids' Backpacks", 'category': 'Clothing, Shoes & Jewelry', 'features': '', 'ingredients': '', 'product_url': 'https://www.amazon.com/Stephen-Joseph-Girls-Recycled-Rainbow/dp/B07G4S9F19', 'image_url': 'https://images-na.ssl-images-amazon.com/images/I/51oQ5Hr-1mL.jpg', 'doc_id': 'products_clothing::e7a8c164491f89ca4bdff2b6dc436f8f'}, {'id': 'c4b902bba12acfccf3b8b4c6f569a73d', 'title': "Little Blue House By Hatley Kids' Big 3D Mug, Mouse, 14 oz", 'price': 8.5, 'rating': -1.0, 'brand': '', 'subcategory': "Clothing, Shoes & Jewelry | Luggage & Travel Gear | Backpacks | Kids' Backpacks", 'category': 'Clothing, Shoes & Jewelry', 'features': '', 'ingredients': '', 'product_url': 'https://www.amazon.com/Little-Blue-House-Hatley-Mouse/dp/B07Q7CYHSR', 'image_url': 'https://images-na.ssl-images-amazon.com/images/I/410rcNTLiJL.jpg', 'doc_id': 'products_clothing::c4b902bba12acfccf3b8b4c6f569a73d'}, {'id': '7371f7d4dd18c3dd9ddd091417c10603', 'title': 'Amscan Cop Recruit Infants Costume', 'price': -1.0, 'rating': -1.0, 'brand': '', 'subcategory': 'Clothing, Shoes & Jewelry | Costumes & Accessories | Kids & Baby | Baby | Baby Boys', 'category': 'Clothing, Shoes & Jewelry', 'features': '', 'ingredients': '', 'product_url': 'https://www.amazon.com/Cop-Recruit-Baby-Infant-Costume/dp/B01GNLX8YE', 'image_url': 'https://images-na.ssl-images-amazon.com/images/I/41zFsyfhG6L.jpg', 'doc_id': 'products_clothing::7371f7d4dd18c3dd9ddd091417c10603'}, {'id': '88b83cd879fb9a81cf165a2ab80d615d', 'title': "Underwraps Kid's Padded Muscle Shirt", 'price': -1.0, 'rating': -1.0, 'brand': '', 'subcategory': 'Clothing, Shoes & Jewelry | Costumes & Accessories | Kids & Baby | Boys | Costumes', 'category': 'Clothing, Shoes & Jewelry', 'features': '', 'ingredients': '', 'product_url': 'https://www.amazon.com/Underwraps-Kids-Padded-Muscle-Shirt/dp/B00OA5B6HW', 'image_url': 'https://images-na.ssl-images-amazon.com/images/I/41YuIPj63kL.jpg', 'doc_id': 'products_clothing::88b83cd879fb9a81cf165a2ab80d615d'}, {'id': 'bc7841d8067f94d592d8bdc111566f7d', 'title': "Stephen Joseph Boys' Big Recycled Gift Bags", 'price': 4.23, 'rating': -1.0, 'brand': '', 'subcategory': "Clothing, Shoes & Jewelry | Luggage & Travel Gear | Backpacks | Kids' Backpacks", 'category': 'Clothing, Shoes & Jewelry', 'features': '', 'ingredients': '', 'product_url': 'https://www.amazon.com/Stephen-Joseph-Girls-Recycled-Llama/dp/B07G4JHGVZ', 'image_url': 'https://images-na.ssl-images-amazon.com/images/I/4177taAK7YL.jpg', 'doc_id': 'products_clothing::bc7841d8067f94d592d8bdc111566f7d'}], 'web_results': [{'title': '14 Best Eco Friendly Cleaning Products Under $20 Reviews', 'url': 'https://homehatch.liveblog365.com/14-best-eco-friendly-cleaning-products-under-20-reviews-safe-non-toxic-sustainable-options-for-a-healthier-home/', 'snippet': 'The Gear Hugger Car Wash Soap is an eco-conscious, biodegradable car cleaner designed to provide a safe and effective wash for all vehicle ...', 'price': None, 'availability': None}, {'title': '10 Best Natural And Nontoxic Cleaning Products (2025)', 'url': 'https://www.thegoodtrade.com/features/natural-nontoxic-cleaning-products/', 'snippet': "... review). Find affordable eco-friendly brands like Seventh Generation, Truce, and Dr. Bronner's here — without the carbon footprint! You can ...", 'price': None, 'availability': None}, {'title': 'EcoGeek Cleaning Products | 100% of Profit to Charity - Good Store', 'url': 'https://good.store/collections/ecogeek-eco-friendly-cleaning-products?srsltid=AfmBOopYKkvTHZ-9xT6-2IUKWDKrNkMn3a-e_iLD7lTY9zZjiRix8Pyk', 'snippet': 'Shop eco-friendly, non-toxic laundry, dish, and cleaning products. 100% of profits support coral reef restoration through the Coral Reef Alliance.', 'price': None, 'availability': None}], 
#     'final_answer': "Check out the Stephen Joseph Recycled Bag Sets for just $9.99! They're perfect for eco-friendly shopping. I've sent details and sources to your screen. Would you like the most affordable or the highest rated?", 
#     'citations': {}}