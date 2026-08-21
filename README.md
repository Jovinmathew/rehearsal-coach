# Rehearsal Coach

Before a podcast appearance or client meeting, you want to rehearse a talk on a
topic and get honest, specific feedback on clarity, pacing, and coverage — not
generic coaching platitudes.

Enter a topic, record yourself talking into the mic, stop, and get back a
transcript, speech stats, and structured feedback — where every piece of
feedback is anchored to something you actually said.

## How it works

Transcription and feedback are two separate API calls, not one bundled
request — so Claude is only ever called on a transcript worth paying for:

1. Enter a topic, click **Record**, talk, click **Stop**.
2. The browser uploads the recorded audio to `POST /transcribe`. This runs
   `faster-whisper` locally (GPU) — no Claude call, no API cost — and returns
   the transcript + speech stats.
3. Once there's a transcript worth reviewing, the frontend calls
   `POST /feedback` with the topic + transcript. This calls the Anthropic API
   for structured feedback, then **validates every quote against the
   transcript before returning anything** — any quote that isn't an exact
   substring of what was actually said is dropped server-side.
4. The frontend shows the transcript, stats, and the surviving feedback.

The grounding validator (`backend/app/grounding.py`) is the core engineering
constraint here: the LLM's output is never trusted blindly, it's checked —
right down to not assuming Claude's tool-call output actually matches its own
schema (a missing/malformed `quote` field is dropped, not trusted, either).

## Stack

- **Backend**: FastAPI, `faster-whisper` (local, GPU) for transcription,
  Anthropic API (Claude Haiku) for feedback. Python 3.12, managed with `uv`.
- **Frontend**: Next.js + TypeScript + Tailwind, browser `MediaRecorder` API.
- **Tests**: pytest, mocking Whisper and Anthropic — the stats calculator and
  grounding validator are tested directly, not LLM output content.

## Running it locally

### Backend

```bash
cd backend
uv sync
cp .env.example .env   # add your ANTHROPIC_API_KEY
uv run uvicorn app.main:app --reload --port 8000
```

Requires an NVIDIA GPU for the `faster-whisper` GPU path; falls back to CPU
automatically if CUDA init fails. First request pays a one-time model
download + load cost.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000. `MediaRecorder` requires HTTPS or `localhost`.

### Tests

```bash
cd backend
uv run pytest
```

## Known limitations (v1)

- **Filler-word detection is crude substring matching**, not linguistic
  analysis — it will false-positive on legitimate uses of words like "like".
- **Feedback runs on Claude Haiku**, chosen for cost/speed. Smaller models are
  more likely to paraphrase instead of quoting verbatim, so more feedback
  items get dropped by the grounding validator than with a larger model —
  a direct, visible trade-off between cost and the *quantity* of feedback
  that survives grounding (not its trustworthiness, which the validator
  guarantees either way).
- **Transcription runs locally** (zero per-call cost, works offline) in
  exchange for needing a GPU and a first-run model download. Feedback runs on
  a hosted API, so it needs a network connection and an API key with credit.
- Browser codec support for `MediaRecorder` varies; tested against Chrome's
  default `audio/webm` output.

## What's next

- **Deployment** — containerize the backend (GPU-enabled host or fall back to
  CPU inference), deploy the frontend to Vercel, wire `NEXT_PUBLIC_API_URL` to
  the deployed backend.
- **Voice-activity detection** — auto-stop on silence instead of manual
  start/stop.
- **Prosody / tone analysis** — real audio ML (pitch, pacing variation,
  pauses) rather than text-only stats.
- **Multi-take history and comparison** — persist takes per topic, show
  improvement over time.
- **Auth** — attach takes to a user account instead of a single-session tool.
