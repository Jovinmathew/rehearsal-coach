import io

from fastapi.testclient import TestClient

from app.limits import MAX_AUDIO_BYTES
from app.main import app
from app.transcribe import AudioTooLongError, InvalidAudioError

client = TestClient(app)


def _audio_file(content: bytes = b"fake-webm-bytes"):
    return {"audio": ("clip.webm", io.BytesIO(content), "audio/webm")}


def test_missing_audio_returns_400():
    response = client.post("/transcribe", data={})
    assert response.status_code == 400
    assert "error" in response.json()


def test_audio_over_max_size_returns_400():
    oversized = b"x" * (MAX_AUDIO_BYTES + 1)
    response = client.post("/transcribe", files=_audio_file(oversized))
    assert response.status_code == 400
    assert "error" in response.json()


def test_audio_over_duration_limit_returns_400(mocker):
    mocker.patch("app.main.transcribe_audio", side_effect=AudioTooLongError(999.0))

    response = client.post("/transcribe", files=_audio_file())

    assert response.status_code == 400
    assert "error" in response.json()


def test_undecodable_audio_returns_400_not_500(mocker):
    mocker.patch("app.main.transcribe_audio", side_effect=InvalidAudioError())

    response = client.post("/transcribe", files=_audio_file())

    assert response.status_code == 400
    assert "error" in response.json()


def test_silent_audio_returns_empty_transcript_no_crash(mocker):
    mocker.patch("app.main.transcribe_audio", return_value=("", 3.0))

    response = client.post("/transcribe", files=_audio_file())

    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == ""
    assert body["stats"]["word_count"] == 0


def test_happy_path_returns_transcript_and_stats(mocker):
    transcript = "This is a short rehearsal about public speaking."
    mocker.patch("app.main.transcribe_audio", return_value=(transcript, 4.0))

    response = client.post("/transcribe", files=_audio_file())

    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == transcript
    assert body["stats"]["word_count"] == 8
    assert body["stats"]["duration_sec"] == 4.0
