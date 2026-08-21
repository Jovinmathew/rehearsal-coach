import ctypes
import glob
import os
import sys
import tempfile


def _preload_cuda_libs() -> None:
    """faster-whisper's CUDA backend dlopen()s libcublas/libcudnn at inference
    time. pip-installed nvidia-*-cu12 wheels don't register on the system
    linker path, and mutating LD_LIBRARY_PATH from within an already-running
    process doesn't help (glibc only consults it at process start). So load
    the .so files directly by absolute path with RTLD_GLOBAL before
    ctranslate2 (imported below) ever needs them — once loaded this way, its
    own dlopen-by-soname calls resolve against what's already in the process.
    Load order isn't guaranteed by the glob, so two passes: the first loads
    everything with no unmet deps, the second picks up what depended on those."""
    py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    nvidia_dir = os.path.join(sys.prefix, "lib", py_ver, "site-packages", "nvidia")
    lib_paths = sorted(
        glob.glob(os.path.join(nvidia_dir, "cublas", "lib", "*.so*"))
        + glob.glob(os.path.join(nvidia_dir, "cudnn", "lib", "*.so*"))
    )
    for _ in range(2):
        still_failing = []
        for path in lib_paths:
            try:
                ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
            except OSError:
                still_failing.append(path)
        if not still_failing:
            break
        lib_paths = still_failing


_preload_cuda_libs()

from faster_whisper import WhisperModel

from app.limits import MAX_DURATION_SEC

_model: WhisperModel | None = None


class AudioTooLongError(Exception):
    def __init__(self, duration_sec: float):
        self.duration_sec = duration_sec
        super().__init__(
            f"audio duration {duration_sec:.1f}s exceeds {MAX_DURATION_SEC}s limit"
        )


class InvalidAudioError(Exception):
    """Raised when the upload can't be decoded as audio at all — wrong
    format, truncated, or not actually audio data."""


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        try:
            _model = WhisperModel("small", device="cuda", compute_type="float16")
        except Exception:
            _model = WhisperModel("small", device="cpu", compute_type="int8")
    return _model


def transcribe_audio(audio_bytes: bytes) -> tuple[str, float]:
    model = _get_model()
    with tempfile.NamedTemporaryFile(suffix=".webm") as f:
        f.write(audio_bytes)
        f.flush()
        # info.duration is known as soon as the audio is decoded, before the
        # (expensive) per-segment inference the `segments` generator lazily
        # runs — checking here skips that work entirely for oversized audio.
        try:
            segments, info = model.transcribe(f.name)
        except Exception as e:
            raise InvalidAudioError() from e
        if info.duration > MAX_DURATION_SEC:
            raise AudioTooLongError(info.duration)
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
    return transcript, info.duration
