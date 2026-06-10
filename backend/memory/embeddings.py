import os
# Force offline mode to prevent Hugging Face Hub downloads from hanging in this environment
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

from sentence_transformers import SentenceTransformer


class _EmbedderProxy:
    """Lazy-loading proxy. The heavy SentenceTransformer model is loaded
    on first call to .encode(), not at import time."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def _load(self):
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)

    def encode(self, *args, **kwargs):
        self._load()
        return self._model.encode(*args, **kwargs)


# Module-level singleton — import this from anywhere
embedder = _EmbedderProxy()
