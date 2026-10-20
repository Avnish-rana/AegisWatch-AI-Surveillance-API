"""
Base abstract interface for all detection models.
All detectors must implement predict() and draw_detections().
"""
from abc import ABC, abstractmethod
import numpy as np


class BaseDetector(ABC):
    """Abstract base class for object detectors."""

    model_name: str = "BaseDetector"
    hf_model_id: str = ""
    license: str = "Unknown"

    @abstractmethod
    def load_model(self) -> None:
        """Download and load the model into memory."""
        ...

    @abstractmethod
    def predict(self, frame: np.ndarray, confidence_threshold: float = 0.5) -> list:
        """
        Run inference on a single BGR frame.

        Returns list of dicts:
        [
            {
                "class_name": str,
                "confidence": float,
                "bbox": [x1, y1, x2, y2],  # pixel coords
                "cx": int,
                "cy": int,
                "track_id": int,           # 0 if tracker not attached
            },
            ...
        ]
        """
        ...

    def draw_detections(self, frame: np.ndarray, detections: list) -> np.ndarray:
        """Draw bounding boxes on frame. Override for custom rendering."""
        import cv2
        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det.get("bbox", [0, 0, 0, 0])]
            label = f"{det.get('class_name', '?')} #{det.get('track_id', 0)} {det.get('confidence', 0):.0%}"
            color = (0, 255, 0) if det.get("class_name") == "person" else (0, 165, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, max(0, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
        return frame

    @property
    def is_loaded(self) -> bool:
        return False
