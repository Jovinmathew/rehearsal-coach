from app.grounding import filter_grounded_feedback

TRANSCRIPT = "So today I want to talk about why our onboarding flow is too long."


def _item(quote, **overrides):
    base = {
        "category": "clarity",
        "quote": quote,
        "issue": "some issue",
        "suggestion": "some suggestion",
    }
    base.update(overrides)
    return base


def test_verbatim_quote_is_kept():
    feedback = [_item("onboarding flow is too long")]
    result = filter_grounded_feedback(feedback, TRANSCRIPT)
    assert result == feedback


def test_fabricated_quote_is_dropped():
    feedback = [_item("our onboarding flow is perfect and fast")]
    result = filter_grounded_feedback(feedback, TRANSCRIPT)
    assert result == []


def test_paraphrased_quote_is_dropped():
    # not verbatim — close but not an exact substring
    feedback = [_item("our onboarding process takes too long")]
    result = filter_grounded_feedback(feedback, TRANSCRIPT)
    assert result == []


def test_mixed_batch_keeps_only_grounded_items():
    grounded = _item("talk about why our onboarding flow is too long")
    fabricated = _item("the pacing was excellent throughout")
    result = filter_grounded_feedback([grounded, fabricated], TRANSCRIPT)
    assert result == [grounded]


def test_empty_feedback_list_returns_empty():
    assert filter_grounded_feedback([], TRANSCRIPT) == []
