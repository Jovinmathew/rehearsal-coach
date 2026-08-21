def filter_grounded_feedback(feedback: list[dict], transcript: str) -> list[dict]:
    """Drop any feedback item whose quote is not a verbatim substring of the
    transcript. This is the trust boundary between the LLM's output and what
    the user actually sees — an ungrounded quote never reaches the response.
    A tool schema's "required" fields aren't a hard guarantee on what a model
    actually returns, so a missing/non-string quote is treated the same as an
    ungrounded one: dropped, not trusted."""
    return [
        item
        for item in feedback
        if isinstance(item.get("quote"), str) and item["quote"] in transcript
    ]
