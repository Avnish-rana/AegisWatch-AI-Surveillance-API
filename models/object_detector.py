"""
YOLOv8 Object Detector — Primary detector.

Model: YOLOv8n (nano variant)
Source: Ultralytics / automatically downloaded by the ultralytics library.
  The yolov8n.pt file is stored locally in the project root.
License: AGPL-3.0 (Ultralytics YOLOv8)
  For academic/educational use this is acceptable.
  Note: Commercial redistribution requires a commercial license.
Size: ~6.5 MB
Hardware: CPU only is fine for real-time inference at low resolutions.
Input: BGR frame (numpy array, any size — auto-resized internally)
Output: Detections with track IDs when persist=True
"""
import os
import logging
import numpy as np
from models.base_model import BaseDetector

logger = logging.getLogger(__name__)

# COCO classes relevant for CCTV surveillance
CCTV_CLASSES = {
    "person", "bicycle", "car", "motorcycle", "bus", "truck",
    "backpack", "handbag", "suitcase", "umbrella",
    "laptop", "cell phone", "knife", "scissors",
    "bottle", "chair", "bench",
}


class YOLOv8Detector(BaseDetector):
    """YOLOv8n object detector with ByteTrack-based tracking via Ultralytics."""

    model_name = "YOLOv8n"
    hf_model_id = "Ultralytics/assets (yolov8n.pt)"
    license = "AGPL-3.0"

    def __init__(self, model_path: str = None):
        self._model = None
        self._model_path = model_path or self._find_model()

    def _find_model(self) -> str:
        """Try to locate yolov8n.pt in common locations."""
        candidates = [
            "yolov8n.pt",
            os.path.join(os.path.dirname(__file__), "..", "yolov8n.pt"),
            os.path.join(os.path.expanduser("~"), ".cache", "ultralytics", "yolov8n.pt"),
        ]
        for p in candidates:
            if os.path.exists(p):
                return os.path.abspath(p)
        return "yolov8n.pt"  # Let ultralytics auto-download

    def load_model(self) -> None:
        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLOv8n from: {self._model_path}")
            self._model = YOLO(self._model_path)
            logger.info("✅ YOLOv8n loaded successfully")
        except ImportError:
            logger.error("ultralytics not installed. Run: pip install ultralytics")
            raise
        except Exception as e:
            logger.error(f"Failed to load YOLOv8n: {e}")
            raise

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def predict(self, frame: np.ndarray, confidence_threshold: float = 0.4) -> list:
        """Run YOLOv8 with built-in ByteTrack tracking."""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        results = self._model.track(
            frame,
            persist=True,
            verbose=False,
            conf=confidence_threshold,
            iou=0.5,
            tracker="bytetrack.yaml",
        )

        detections = []
        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = self._model.names.get(cls_id, str(cls_id))
                if cls_name not in CCTV_CLASSES:
                    continue
                conf = float(box.conf[0])
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                track_id = int(box.id[0]) if box.id is not None else 0
                detections.append({
                    "class_name": cls_name,
                    "confidence": round(conf, 3),
                    "bbox": [round(x1), round(y1), round(x2), round(y2)],
                    "cx": round((x1 + x2) / 2),
                    "cy": round((y1 + y2) / 2),
                    "track_id": track_id,
                    "width": round(x2 - x1),
                    "height": round(y2 - y1),
                })
        return detections

    def predict_simple(self, frame: np.ndarray, confidence_threshold: float = 0.4) -> list:
        """Detect without tracking — for single-frame analysis."""
        if self._model is None:
            raise RuntimeError("Model not loaded.")
        results = self._model(frame, verbose=False, conf=confidence_threshold)
        detections = []
        if results and results[0].boxes is not None:
            for i, box in enumerate(results[0].boxes):
                cls_id = int(box.cls[0])
                cls_name = self._model.names.get(cls_id, str(cls_id))
                if cls_name not in CCTV_CLASSES:
                    continue
                conf = float(box.conf[0])
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                detections.append({
                    "class_name": cls_name,
                    "confidence": round(conf, 3),
                    "bbox": [round(x1), round(y1), round(x2), round(y2)],
                    "cx": round((x1 + x2) / 2),
                    "cy": round((y1 + y2) / 2),
                    "track_id": i,
                    "width": round(x2 - x1),
                    "height": round(y2 - y1),
                })
        return detections
