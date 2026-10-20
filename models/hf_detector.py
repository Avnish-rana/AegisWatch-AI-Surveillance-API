"""
Hugging Face DETR Object Detector — Secondary/fallback detector.

Model: facebook/detr-resnet-50
Hugging Face: https://huggingface.co/facebook/detr-resnet-50
License: Apache 2.0 ✅ (fully compatible with academic projects)
Size: ~166 MB
Hardware: CPU compatible (slower than YOLOv8 but fully functional)
Input: PIL Image or BGR numpy array
Output: Standard detection list matching BaseDetector contract

Why selected:
- Apache 2.0 license — no usage restrictions
- Well-maintained by Meta/HuggingFace
- Demonstrates real HuggingFace transformers integration
- Detects COCO classes (person, bag, etc.) — suitable for CCTV
- Can run on CPU (slower but feasible for video analysis)
"""
import logging
import numpy as np
from models.base_model import BaseDetector

logger = logging.getLogger(__name__)

HF_MODEL_ID = "facebook/detr-resnet-50"

# COCO classes mapped by DETR — stored as normalised labels (lower, spaces→_)
# DETR pipeline returns e.g. "cell phone", which we normalise to "cell_phone"
CCTV_CLASSES_NORM = {
    "person", "bicycle", "car", "motorcycle", "bus", "truck",
    "backpack", "handbag", "suitcase", "umbrella",
    "laptop", "cell_phone", "knife", "scissors",
}


class HFDETRDetector(BaseDetector):
    """
    DEtection TRansformer (DETR) from facebook/detr-resnet-50.
    Uses Hugging Face Transformers pipeline.
    License: Apache 2.0
    """

    model_name = "facebook/detr-resnet-50"
    hf_model_id = "facebook/detr-resnet-50"
    license = "Apache 2.0"

    def __init__(self, cache_dir: str = None):
        self._processor = None
        self._model = None
        self._pipeline = None
        self._cache_dir = cache_dir
        self._loaded = False

    def load_model(self) -> None:
        """Download and load DETR from Hugging Face (cached locally)."""
        # Pre-flight: check both required libraries with clear messages
        try:
            import transformers  # noqa
        except ImportError:
            raise ImportError(
                "transformers is required for DETR. Install with: pip install transformers"
            )
        try:
            import timm  # noqa
        except ImportError:
            raise ImportError(
                "timm is required by transformers>=5.x for the DETR ResNet-50 backbone. "
                "Install with: pip install timm"
            )

        try:
            from transformers import pipeline
            logger.info(
                f"Loading {HF_MODEL_ID} from Hugging Face "
                f"(first run downloads ~166 MB, then cached locally)..."
            )
            self._pipeline = pipeline(
                "object-detection",
                model=HF_MODEL_ID,
                cache_dir=self._cache_dir,
                device=-1,   # CPU — works on any Windows laptop
            )
            self._loaded = True
            logger.info(f"✅ {HF_MODEL_ID} loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load {HF_MODEL_ID}: {e}")
            raise

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def predict(self, frame: np.ndarray, confidence_threshold: float = 0.5) -> list:
        """
        Run DETR inference on a BGR frame.
        Returns detections in the standard format (same contract as YOLOv8Detector).
        """
        if not self._loaded or self._pipeline is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        try:
            from PIL import Image
            # Convert BGR (OpenCV) → RGB (PIL)
            rgb = frame[:, :, ::-1]
            pil_img = Image.fromarray(rgb)

            raw = self._pipeline(pil_img, threshold=confidence_threshold)

            h, w = frame.shape[:2]
            detections = []
            for idx, item in enumerate(raw):
                # Normalise: lower-case + spaces → underscores  ("cell phone" → "cell_phone")
                raw_label = item.get("label", "")
                label = raw_label.lower().replace(" ", "_")
                score = item.get("score", 0.0)
                box = item.get("box", {})

                # Filter to CCTV-relevant classes only
                if label not in CCTV_CLASSES_NORM:
                    continue

                x1 = int(box.get("xmin", 0))
                y1 = int(box.get("ymin", 0))
                x2 = int(box.get("xmax", w))
                y2 = int(box.get("ymax", h))

                detections.append({
                    "class_name": label,
                    "confidence": round(score, 3),
                    "bbox": [x1, y1, x2, y2],
                    "cx": (x1 + x2) // 2,
                    "cy": (y1 + y2) // 2,
                    "track_id": idx,  # DETR doesn't track — use index as placeholder
                    "width": x2 - x1,
                    "height": y2 - y1,
                })
            return detections

        except Exception as e:
            logger.error(f"DETR inference error: {e}")
            return []

    def predict_simple(self, frame: np.ndarray, confidence_threshold: float = 0.5) -> list:
        """Alias for predict() — DETR has no separate tracking mode."""
        return self.predict(frame, confidence_threshold)
