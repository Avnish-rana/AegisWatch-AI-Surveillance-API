"""
ModelManager — central hub for loading, caching, and switching AI models.

Supports:
  - yolov8  → YOLOv8n (primary, local file, AGPL-3.0)
  - detr    → facebook/detr-resnet-50 (HuggingFace, Apache 2.0)
  - auto    → tries yolov8 first, falls back to detr

Models are loaded once and cached as module-level singletons.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global model cache
_loaded_models: dict = {}
_active_model_name: str = "none"
_load_error: Optional[str] = None

AVAILABLE_MODELS = {
    "yolov8": {
        "class": "models.object_detector.YOLOv8Detector",
        "name": "YOLOv8n",
        "hf_id": "Ultralytics/assets (yolov8n.pt)",
        "license": "AGPL-3.0",
        "size_mb": 6.5,
        "description": "Fast, accurate object detection with built-in ByteTrack tracking",
    },
    "detr": {
        "class": "models.hf_detector.HFDETRDetector",
        "name": "facebook/detr-resnet-50",
        "hf_id": "facebook/detr-resnet-50",
        "license": "Apache 2.0",
        "size_mb": 166,
        "description": "DETR transformer-based detector from HuggingFace — Apache 2.0 licensed",
    },
}


def _import_class(dotted_path: str):
    parts = dotted_path.rsplit(".", 1)
    mod = __import__(parts[0], fromlist=[parts[1]])
    return getattr(mod, parts[1])


def load_model(model_name: str = "auto", cache_dir: str = None):
    """
    Load and return the specified detector.
    model_name: 'yolov8' | 'detr' | 'auto'
    Returns the loaded detector instance or None on failure.
    """
    global _loaded_models, _active_model_name, _load_error

    # Resolve auto
    if model_name == "auto":
        for candidate in ["yolov8", "detr"]:
            result = load_model(candidate, cache_dir)
            if result is not None:
                return result
        return None

    if model_name not in AVAILABLE_MODELS:
        logger.error(f"Unknown model: {model_name}. Available: {list(AVAILABLE_MODELS.keys())}")
        return None

    # Return cached
    if model_name in _loaded_models:
        logger.info(f"Returning cached model: {model_name}")
        return _loaded_models[model_name]

    info = AVAILABLE_MODELS[model_name]
    logger.info(f"Loading model [{model_name}] — {info['name']} (License: {info['license']})")

    try:
        klass = _import_class(info["class"])
        if model_name == "detr" and cache_dir:
            instance = klass(cache_dir=cache_dir)
        else:
            instance = klass()

        instance.load_model()
        _loaded_models[model_name] = instance
        _active_model_name = model_name
        logger.info(f"✅ Model [{model_name}] loaded successfully")
        return instance

    except Exception as e:
        _load_error = str(e)
        logger.warning(f"⚠️  Could not load model [{model_name}]: {e}")
        return None


def get_active_model():
    """Return the currently loaded (and active) model instance."""
    if _active_model_name in _loaded_models:
        return _loaded_models[_active_model_name]
    return None


def get_model_info() -> dict:
    """Return info about the active model for the health endpoint."""
    if _active_model_name == "none" or _active_model_name not in _loaded_models:
        return {
            "status": "unavailable",
            "model": None,
            "error": _load_error,
        }
    info = AVAILABLE_MODELS.get(_active_model_name, {})
    return {
        "status": "ok",
        "model": _active_model_name,
        "model_name": info.get("name"),
        "hf_id": info.get("hf_id"),
        "license": info.get("license"),
        "size_mb": info.get("size_mb"),
    }


def list_models() -> list:
    return [
        {**v, "key": k, "loaded": k in _loaded_models}
        for k, v in AVAILABLE_MODELS.items()
    ]
