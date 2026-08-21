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
            "overall_quality": {
                "type": "string",
                "enum": [
                    "needs_significant_work",
                    "needs_some_work",
                    "solid",
                    "strong",
                    "exceptional",
                ],
                "description": (
                    "Honest holistic judgment, made before listing feedback. "
                    "Judge this take on its own merits, not against any fixed "
                    "reference. Use the full range — most good takes should "
                    "land on 'solid' or 'strong'. Reserve 'exceptional' for a "
                    "take with no meaningful issues at all; it should be "
                    "rare, not a default top score."
                ),
            },
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
        "required": ["overall_quality", "feedback"],
    },
}

# Quote grounding is enforced server-side by app.grounding regardless of how
# well the model follows this instruction — this prompt just reduces how much
# feedback gets thrown away.
#
# overall_quality is a forced-tool_choice workaround: Anthropic's own docs
# confirm a forced tool call blocks any reasoning before it, so a schema
# field filled before `feedback` is the only place left for the model to
# commit to a quality judgment ahead of generating items. feedback should
# scale with it — sparse/empty at "exceptional", substantive as quality
# drops — rather than always populating a fixed number of items regardless
# of how strong the take already is.
SYSTEM_PROMPT = (
    "You are a rehearsal coach reviewing a spoken take on a topic. Give "
    "specific, honest feedback grounded in what the speaker actually said. "
    "Every 'quote' field MUST be an exact verbatim substring copied "
    "character-for-character from the transcript — never paraphrase, "
    "summarize, or lightly edit it. If you can't find a good verbatim quote "
    "for a point, drop that feedback item entirely.\n\n"
    "First judge overall_quality honestly and independently — do not "
    "anchor on any fixed standard, just this take on its own merits. Then "
    "let the feedback list scale with that judgment: an 'exceptional' take "
    "should typically get an empty or near-empty feedback list — do not "
    "manufacture issues just to have something to say. A "
    "'needs_significant_work' take should get substantive, specific "
    "feedback. It is normal and expected for feedback to be empty."
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
