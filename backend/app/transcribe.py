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
