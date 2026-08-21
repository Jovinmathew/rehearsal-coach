import pytest

from app.limits import MAX_DURATION_SEC
from app.transcribe import AudioTooLongError, InvalidAudioError, transcribe_audio


class _FakeInfo:
    def __init__(self, duration):
        self.duration = duration


class _FakeModel:
    def __init__(self, duration, segments=()):
        self._duration = duration
        self._segments = segments

    def transcribe(self, path):
        return iter(self._segments), _FakeInfo(self._duration)


class _UndecodableModel:
    def transcribe(self, path):
        raise RuntimeError("Invalid data found when processing input")


def test_audio_over_duration_limit_raises_before_transcribing(mocker, tmp_path):
    fake_model = _FakeModel(duration=MAX_DURATION_SEC + 1)
    mocker.patch("app.transcribe._get_model", return_value=fake_model)

    with pytest.raises(AudioTooLongError):
        transcribe_audio(b"fake-bytes")


def test_audio_within_duration_limit_transcribes_normally(mocker):
    segment = mocker.Mock(text=" hello world ")
    fake_model = _FakeModel(duration=MAX_DURATION_SEC - 1, segments=[segment])
    mocker.patch("app.transcribe._get_model", return_value=fake_model)

    transcript, duration_sec = transcribe_audio(b"fake-bytes")

    assert transcript == "hello world"
    assert duration_sec == MAX_DURATION_SEC - 1


def test_undecodable_audio_raises_invalid_audio_error(mocker):
    mocker.patch("app.transcribe._get_model", return_value=_UndecodableModel())

    with pytest.raises(InvalidAudioError):
        transcribe_audio(b"not-actually-audio")
