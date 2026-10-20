import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List
import numpy as np

@dataclass
class AbandonedObjectEvent:
    object_track_id: int
    object_class: str
    last_seen_person_id: Optional[int]
    duration_seconds: float
    bbox: np.ndarray
    confidence: float

class AbandonedObjectDetector:
    OBJECT_CLASSES = {"backpack", "handbag", "suitcase", "umbrella", "bag"}
    
    def __init__(self, threshold_seconds: float = 30.0, proximity_threshold: float = 100.0):
        self.threshold = threshold_seconds
        self.proximity_threshold = proximity_threshold
        self._object_states: Dict[int, dict] = {}  # track_id -> state dict
    
    def _centroid(self, bbox: np.ndarray) -> Tuple[float, float]:
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    
    def _distance(self, c1, c2) -> float:
        return ((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2) ** 0.5
    
    def analyze(self, detections, frame_idx: int) -> List[AbandonedObjectEvent]:
        # Separate persons from objects
        persons = [d for d in detections if d.class_name == "person" and d.track_id is not None]
        objects = [d for d in detections if d.class_name in self.OBJECT_CLASSES and d.track_id is not None]
        
        current_time = time.time()
        current_object_ids = set()
        events = []
        
        for obj in objects:
            tid = obj.track_id
            current_object_ids.add(tid)
            obj_centroid = self._centroid(obj.bbox)
            
            # Find nearest person
            nearest_person_id = None
            min_dist = float("inf")
            for person in persons:
                pc = self._centroid(person.bbox)
                d = self._distance(obj_centroid, pc)
                if d < min_dist:
                    min_dist = d
                    nearest_person_id = person.track_id
            
            if tid not in self._object_states:
                self._object_states[tid] = {
                    "first_seen": current_time,
                    "last_centroid": obj_centroid,
                    "last_owner": nearest_person_id,
                    "unattended_since": None,
                    "class": obj.class_name,
                }
            
            state = self._object_states[tid]
            state["last_centroid"] = obj_centroid
            state["class"] = obj.class_name
            
            has_owner_nearby = min_dist < self.proximity_threshold
            
            if has_owner_nearby:
                state["last_owner"] = nearest_person_id
                state["unattended_since"] = None
            else:
                if state["unattended_since"] is None:
                    state["unattended_since"] = current_time
                unattended_duration = current_time - state["unattended_since"]
                if unattended_duration >= self.threshold:
                    confidence = min(95, 50 + unattended_duration * 1.5)
                    events.append(AbandonedObjectEvent(
                        object_track_id=tid,
                        object_class=state["class"],
                        last_seen_person_id=state["last_owner"],
                        duration_seconds=unattended_duration,
                        bbox=obj.bbox,
                        confidence=confidence
                    ))
        
        # Remove stale object states
        for stale_id in list(self._object_states.keys()):
            if stale_id not in current_object_ids:
                del self._object_states[stale_id]
        
        return events
    
    def clear_track(self, track_id: int):
        self._object_states.pop(track_id, None)
