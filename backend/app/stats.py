import re

# v1 limitation: crude case-insensitive substring matching, not linguistic
# analysis — "you know" catches phrase usage, "like" will false-positive on
# legitimate uses (e.g. "I like this"). Not fixing this in v1 per the PRD.
FILLER_WORDS = ["um", "uh", "like", "you know", "so", "actually", "basically"]


def compute_stats(transcript: str, duration_sec: float) -> dict:
    words = transcript.split()
    word_count = len(words)
    wpm = (word_count / (duration_sec / 60)) if duration_sec > 0 else 0.0

    lower = transcript.lower()
    filler_examples = [f for f in FILLER_WORDS if f in lower]
    filler_count = sum(lower.count(f) for f in filler_examples)

    return {
        "word_count": word_count,
        "duration_sec": duration_sec,
        "wpm": wpm,
        "filler_count": filler_count,
        "filler_examples": filler_examples,
    }
