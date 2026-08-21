import os
import sys
import tempfile


def _ensure_cuda_libs_on_path() -> None:
    """faster-whisper's CUDA backend dlopen()s libcublas/libcudnn at inference
    time. pip-installed nvidia-*-cu12 wheels don't register on the system
    linker path, and glibc's dynamic linker only consults LD_LIBRARY_PATH at
    process start — mutating os.environ after that point has no effect. So if
    the libs aren't already on the path, re-exec this same process once with
    them added, before ctranslate2 (imported below) ever needs them."""
    py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    nvidia_dir = os.path.join(sys.prefix, "lib", py_ver, "site-packages", "nvidia")
    lib_dirs = [
        os.path.join(nvidia_dir, "cublas", "lib"),
        os.path.join(nvidia_dir, "cudnn", "lib"),
    ]
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    missing = [d for d in lib_dirs if os.path.isdir(d) and d not in existing]
    if missing:
        os.environ["LD_LIBRARY_PATH"] = ":".join(missing + ([existing] if existing else []))
        os.execv(sys.executable, [sys.executable] + sys.argv)


_ensure_cuda_libs_on_path()

from faster_whisper import WhisperModel

_model: WhisperModel | None = None


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
        segments, info = model.transcribe(f.name)
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        duration_sec = info.duration
    return transcript, duration_sec
