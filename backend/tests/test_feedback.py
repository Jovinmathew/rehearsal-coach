from app.feedback import FEEDBACK_TOOL, get_feedback


def test_schema_requires_overall_quality_gate_before_feedback():
    props = FEEDBACK_TOOL["input_schema"]["properties"]
    required = FEEDBACK_TOOL["input_schema"]["required"]

    assert "overall_quality" in props
    assert "overall_quality" in required
    assert "feedback" in required
    # The gate field must be filled before the array — schema property order
    # is the only channel for this under forced tool_choice (no preceding
    # natural-language reasoning is possible).
    assert list(props.keys()).index("overall_quality") < list(props.keys()).index(
        "feedback"
    )


def test_overall_quality_enum_has_graded_range_not_binary():
    enum = FEEDBACK_TOOL["input_schema"]["properties"]["overall_quality"]["enum"]
    assert len(enum) >= 4


def _fake_message(mocker, tool_input):
    block = mocker.Mock()
    block.type = "tool_use"
    block.name = "submit_feedback"
    block.input = tool_input
    message = mocker.Mock()
    message.content = [block]
    return message


def test_get_feedback_returns_only_the_feedback_array(mocker):
    message = _fake_message(
        mocker,
        {
            "overall_quality": "exceptional",
            "feedback": [],
        },
    )
    client = mocker.Mock()
    client.messages.create.return_value = message
    mocker.patch("app.feedback._get_client", return_value=client)

    result = get_feedback("public speaking", "a clear, well-paced take")

    assert result == []


def test_get_feedback_passes_through_populated_items(mocker):
    items = [
        {
            "category": "clarity",
            "quote": "some quote",
            "issue": "an issue",
            "suggestion": "a suggestion",
        }
    ]
    message = _fake_message(
        mocker, {"overall_quality": "needs_some_work", "feedback": items}
    )
    client = mocker.Mock()
    client.messages.create.return_value = message
    mocker.patch("app.feedback._get_client", return_value=client)

    result = get_feedback("public speaking", "a rougher take")

    assert result == items
