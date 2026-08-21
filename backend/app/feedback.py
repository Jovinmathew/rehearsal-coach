from anthropic import Anthropic

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic()
    return _client


FEEDBACK_TOOL = {
    "name": "submit_feedback",
    "description": "Submit structured rehearsal feedback items.",
    "input_schema": {
        "type": "object",
        "properties": {
            "feedback": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["clarity", "structure", "pacing", "coverage"],
                        },
                        "quote": {
                            "type": "string",
                            "description": (
                                "A verbatim substring copied exactly, character for "
                                "character, from the transcript. Never paraphrase."
                            ),
                        },
                        "issue": {"type": "string"},
                        "suggestion": {"type": "string"},
                    },
                    "required": ["category", "quote", "issue", "suggestion"],
                },
            }
        },
        "required": ["feedback"],
    },
}

# Quote grounding is enforced server-side by app.grounding regardless of how
# well the model follows this instruction — this prompt just reduces how much
# feedback gets thrown away.
SYSTEM_PROMPT = (
    "You are a rehearsal coach reviewing a spoken take on a topic. Give "
    "specific, honest feedback grounded in what the speaker actually said. "
    "Every 'quote' field MUST be an exact verbatim substring copied "
    "character-for-character from the transcript — never paraphrase, "
    "summarize, or lightly edit it. If you can't find a good verbatim quote "
    "for a point, drop that feedback item entirely."
)


def get_feedback(topic: str, transcript: str) -> list[dict]:
    client = _get_client()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        tools=[FEEDBACK_TOOL],
        tool_choice={"type": "tool", "name": "submit_feedback"},
        messages=[
            {
                "role": "user",
                "content": f"Topic: {topic}\n\nTranscript:\n{transcript}",
            }
        ],
    )
    for block in message.content:
        if block.type == "tool_use" and block.name == "submit_feedback":
            return block.input.get("feedback", [])
    return []
