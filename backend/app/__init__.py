"""IndoClip Pro Backend Application"""
__version__ = "1.0.0"

# Fix PyAV 19+ compatibility with faster-whisper (metadata_errors argument removed in PyAV 19)
try:
    import av
    _original_av_open = av.open
    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _original_av_open(*args, **kwargs)
    av.open = _safe_av_open
except Exception:
    pass

