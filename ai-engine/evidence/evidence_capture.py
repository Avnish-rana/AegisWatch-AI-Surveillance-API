import os
import cv2
import json
import time
import threading
from collections import deque
from datetime import datetime
from typing import Optional
import numpy as np

EVIDENCE_BASE_DIR = os.environ.get("EVIDENCE_DIR", "data/evidence")

class FrameBuffer:
    """Thread-safe rolling frame buffer for video clip capture."""
    def __init__(self, max_seconds: float = 15.0, fps: float = 10.0):
        maxlen = int(max_seconds * fps)
        self._buffer: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()
    
    def add_frame(self, frame: np.ndarray):
        with self._lock:
            self._buffer.append((time.time(), frame.copy()))
    
    def get_frames(self, last_seconds: float = 10.0):
        cutoff = time.time() - last_seconds
        with self._lock:
            return [(t, f) for t, f in self._buffer if t >= cutoff]

class EvidenceCapture:
    def __init__(self, camera_id: str, frame_buffer: Optional[FrameBuffer] = None):
        self.camera_id = camera_id
        self.frame_buffer = frame_buffer or FrameBuffer()
    
    def capture_incident(self, incident_id: str, current_frame: np.ndarray, 
                          incident_type: str, camera_location: str,
                          track_ids: list, metadata: dict = None) -> dict:
        """Capture snapshot + video clip for an incident. Returns paths dict."""
        incident_dir = os.path.join(EVIDENCE_BASE_DIR, incident_id)
        os.makedirs(incident_dir, exist_ok=True)
        
        result = {"incident_id": incident_id, "directory": incident_dir}
        
        # 1. Save snapshot
        snapshot_path = os.path.join(incident_dir, "snapshot.jpg")
        # Draw incident label on snapshot
        labeled = current_frame.copy()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(labeled, f"[AI DETECTED] {incident_type}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(labeled, f"Camera: {self.camera_id} | {ts}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        cv2.putText(labeled, "AI-GENERATED DETECTION - REQUIRES VERIFICATION", (10, labeled.shape[0]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
        cv2.imwrite(snapshot_path, labeled)
        result["snapshot"] = snapshot_path
        
        # 2. Save video clip
        clip_path = os.path.join(incident_dir, "incident.mp4")
        frames = self.frame_buffer.get_frames(last_seconds=10.0)
        if frames:
            h, w = frames[0][1].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(clip_path, fourcc, 10.0, (w, h))
            for _, f in frames:
                writer.write(f)
            writer.release()
            result["video_clip"] = clip_path
        
        # 3. Write metadata.json
        meta = {
            "incident_id": incident_id,
            "incident_type": incident_type,
            "camera_id": self.camera_id,
            "camera_location": camera_location,
            "track_ids": track_ids,
            "timestamp": datetime.now().isoformat(),
            "disclaimer": "AI-generated detection. Requires authorized human verification.",
        }
        if metadata:
            meta.update(metadata)
        meta_path = os.path.join(incident_dir, "metadata.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2, default=str)
        result["metadata"] = meta_path
        
        return result
