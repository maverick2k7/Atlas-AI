import os
# Force offline mode to prevent Hugging Face Hub downloads from hanging in this environment
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

from sentence_transformers import SentenceTransformer


class _EmbedderProxy:
    """Lazy-loading proxy. The heavy SentenceTransformer model is loaded
    on first call to .encode(), not at import time."""

    def __init__(self, model_folder: str = "all-MiniLM-L6-v2"):
        # Resolve the absolute path to backend/models/<model_folder>
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._model_path = os.path.join(base_dir, "models", model_folder)
        self._model: SentenceTransformer | None = None

    def _load(self):
        if self._model is None:
            if not os.path.exists(self._model_path):
                raise FileNotFoundError(
                    f"Model not found at {self._model_path}. "
                    "Run 'python download_model.py' to download it."
                )
            self._model = SentenceTransformer(self._model_path)

    def encode(self, *args, **kwargs):
        self._load()
        return self._model.encode(*args, **kwargs)


# Module-level singleton — import this from anywhere
embedder = _EmbedderProxy()
