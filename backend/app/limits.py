MAX_TOPIC_LENGTH = 300
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB — generous for a few minutes of webm/opus
MAX_DURATION_SEC = 300  # 5 minutes — plenty for a rehearsal take

# /feedback takes a transcript directly from the client rather than deriving
# it from audio server-side, so it needs its own bound — MAX_DURATION_SEC no
# longer implicitly caps what reaches Claude. ~180wpm * 5min * ~6 chars/word
# (incl. space) is ~5400 chars for a legitimately long take; rounded up with
# headroom.
MAX_TRANSCRIPT_LENGTH = 8000
