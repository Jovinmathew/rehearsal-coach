def filter_grounded_feedback(feedback: list[dict], transcript: str) -> list[dict]:
    """Drop any feedback item whose quote is not a verbatim substring of the
    transcript. This is the trust boundary between the LLM's output and what
    the user actually sees — an ungrounded quote never reaches the response."""
    return [item for item in feedback if item["quote"] in transcript]
