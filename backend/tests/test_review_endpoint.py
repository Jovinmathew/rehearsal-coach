import io

from fastapi.testclient import TestClient

from app.limits import MAX_AUDIO_BYTES, MAX_TOPIC_LENGTH
from app.main import app
from app.transcribe import AudioTooLongError, InvalidAudioError

client = TestClient(app)


def _audio_file(content: bytes = b"fake-webm-bytes"):
    return {"audio": ("clip.webm", io.BytesIO(content), "audio/webm")}


def test_missing_topic_returns_400():
    response = client.post("/review", files=_audio_file(), data={"topic": ""})
    assert response.status_code == 400
    assert "error" in response.json()


def test_missing_audio_returns_400():
    response = client.post("/review", data={"topic": "public speaking"})
    assert response.status_code == 400
    assert "error" in response.json()


def test_topic_over_max_length_returns_400():
    response = client.post(
        "/review", files=_audio_file(), data={"topic": "x" * (MAX_TOPIC_LENGTH + 1)}
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_audio_over_max_size_returns_400():
    oversized = b"x" * (MAX_AUDIO_BYTES + 1)
    response = client.post(
        "/review", files=_audio_file(oversized), data={"topic": "public speaking"}
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_audio_over_duration_limit_returns_400(mocker):
    mocker.patch("app.main.transcribe_audio", side_effect=AudioTooLongError(999.0))

    response = client.post(
        "/review", files=_audio_file(), data={"topic": "public speaking"}
    )

    assert response.status_code == 400
    assert "error" in response.json()


def test_undecodable_audio_returns_400_not_500(mocker):
    mocker.patch("app.main.transcribe_audio", side_effect=InvalidAudioError())

    response = client.post(
        "/review", files=_audio_file(), data={"topic": "public speaking"}
    )

    assert response.status_code == 400
    assert "error" in response.json()


def test_silent_audio_returns_empty_transcript_and_feedback(mocker):
    mocker.patch("app.main.transcribe_audio", return_value=("", 3.0))
    get_feedback = mocker.patch("app.main.get_feedback")

    response = client.post(
        "/review", files=_audio_file(), data={"topic": "public speaking"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == ""
    assert body["feedback"] == []
    get_feedback.assert_not_called()


def test_happy_path_returns_stats_and_grounded_feedback(mocker):
    transcript = "This is a short rehearsal about public speaking."
    mocker.patch("app.main.transcribe_audio", return_value=(transcript, 4.0))
    mocker.patch(
        "app.main.get_feedback",
        return_value=[
            {
                "category": "clarity",
                "quote": "a short rehearsal about public speaking",
                "issue": "too brief",
                "suggestion": "add more detail",
            },
            {
                "category": "pacing",
                "quote": "this sentence was never said",
                "issue": "fabricated",
                "suggestion": "n/a",
            },
        ],
    )

    response = client.post(
        "/review", files=_audio_file(), data={"topic": "public speaking"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == transcript
    assert body["stats"]["word_count"] == 8
    assert len(body["feedback"]) == 1
    assert body["feedback"][0]["quote"] == "a short rehearsal about public speaking"
