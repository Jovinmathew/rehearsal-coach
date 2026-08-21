from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.feedback import get_feedback
from app.grounding import filter_grounded_feedback
from app.limits import MAX_AUDIO_BYTES, MAX_DURATION_SEC, MAX_TOPIC_LENGTH
from app.stats import compute_stats
from app.transcribe import AudioTooLongError, InvalidAudioError, transcribe_audio

load_dotenv()

AUDIO_READ_CHUNK = 1024 * 1024


async def _read_audio_bounded(audio: UploadFile) -> Optional[bytes]:
    """Read the upload in chunks, aborting as soon as it exceeds the size cap
    instead of buffering an arbitrarily large body into memory first."""
    total = 0
    chunks = []
    while True:
        chunk = await audio.read(AUDIO_READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_AUDIO_BYTES:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


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

    if len(topic) > MAX_TOPIC_LENGTH:
        return JSONResponse(
            status_code=400,
            content={"error": f"topic must be {MAX_TOPIC_LENGTH} characters or fewer"},
        )

    if audio is None:
        return JSONResponse(status_code=400, content={"error": "audio is required"})

    audio_bytes = await _read_audio_bounded(audio)
    if audio_bytes is None:
        max_mb = MAX_AUDIO_BYTES // (1024 * 1024)
        return JSONResponse(
            status_code=400, content={"error": f"audio file exceeds {max_mb}MB limit"}
        )
    if not audio_bytes:
        return JSONResponse(status_code=400, content={"error": "audio is required"})

    try:
        transcript, duration_sec = transcribe_audio(audio_bytes)
    except AudioTooLongError:
        max_min = MAX_DURATION_SEC // 60
        return JSONResponse(
            status_code=400,
            content={"error": f"recording exceeds {max_min} minute limit"},
        )
    except InvalidAudioError:
        return JSONResponse(
            status_code=400, content={"error": "couldn't process this audio file"}
        )
    stats = compute_stats(transcript, duration_sec)

    if not transcript.strip():
        return {"transcript": transcript, "stats": stats, "feedback": []}

    raw_feedback = get_feedback(topic, transcript)
    feedback = filter_grounded_feedback(raw_feedback, transcript)

    return {"transcript": transcript, "stats": stats, "feedback": feedback}
