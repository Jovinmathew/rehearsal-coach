from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.feedback import get_feedback
from app.grounding import filter_grounded_feedback
from app.stats import compute_stats
from app.transcribe import transcribe_audio

load_dotenv()

app = FastAPI(title="Rehearsal Coach")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


@app.post("/review")
async def review(
    audio: Optional[UploadFile] = File(None),
    topic: Optional[str] = Form(None),
):
    if not topic or not topic.strip():
        return JSONResponse(status_code=400, content={"error": "topic is required"})

    if audio is None:
        return JSONResponse(status_code=400, content={"error": "audio is required"})

    audio_bytes = await audio.read()
    if not audio_bytes:
        return JSONResponse(status_code=400, content={"error": "audio is required"})

    transcript, duration_sec = transcribe_audio(audio_bytes)
    stats = compute_stats(transcript, duration_sec)

    if not transcript.strip():
        return {"transcript": transcript, "stats": stats, "feedback": []}

    raw_feedback = get_feedback(topic, transcript)
    feedback = filter_grounded_feedback(raw_feedback, transcript)

    return {"transcript": transcript, "stats": stats, "feedback": feedback}
