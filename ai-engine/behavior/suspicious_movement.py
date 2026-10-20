import time
import math
from dataclasses import dataclass
from typing import Dict, List, Deque, Tuple
from collections import deque
import numpy as np

@dataclass
class SuspiciousMovementEvent:
    track_id: int
    event_subtype: str  # RUNNING, SUDDEN_DIRECTION_CHANGE, ERRATIC
    speed_score: float
    direction_change_score: float
    confidence: float
    bbox: np.ndarray

class SuspiciousMovementDetector:
    def __init__(self, speed_threshold: float = 25.0, history_frames: int = 20, direction_change_threshold: float = 90.0):
        self.speed_threshold = speed_threshold
        self.history_frames = history_frames
        self.direction_change_threshold = direction_change_threshold
        self._history: Dict[int, Deque] = {}  # track_id -> deque of (timestamp, centroid)
    
    def _centroid(self, bbox: np.ndarray) -> Tuple[float, float]:
        return ((bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2)
    
    def _angle_between(self, v1, v2) -> float:
        """Angle in degrees between two 2D direction vectors."""
        if v1 == (0,0) or v2 == (0,0):
            return 0.0
        dot = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
        if mag1 == 0 or mag2 == 0:
            return 0.0
        cos_a = max(-1, min(1, dot / (mag1 * mag2)))
        return math.degrees(math.acos(cos_a))
    
    def analyze(self, detections) -> List[SuspiciousMovementEvent]:
        events = []
        current_time = time.time()
        
        persons = [d for d in detections if d.class_name == "person" and d.track_id is not None]
        current_ids = set(p.track_id for p in persons)
        
        # Remove stale histories
        for stale_id in list(self._history.keys()):
            if stale_id not in current_ids:
                del self._history[stale_id]
        
        for person in persons:
            tid = person.track_id
            centroid = self._centroid(person.bbox)
            
            if tid not in self._history:
                self._history[tid] = deque(maxlen=self.history_frames)
            
            self._history[tid].append((current_time, centroid))
            hist = self._history[tid]
            
            if len(hist) < 5:
                continue
            
            hist_list = list(hist)
            
            # Calculate speeds (pixels per second)
            speeds = []
            for i in range(1, len(hist_list)):
                dt = hist_list[i][0] - hist_list[i-1][0]
                if dt <= 0:
                    continue
                dx = hist_list[i][1][0] - hist_list[i-1][1][0]
                dy = hist_list[i][1][1] - hist_list[i-1][1][1]
                speed = math.sqrt(dx**2 + dy**2) / dt
                speeds.append(speed)
            
            if not speeds:
                continue
            
            max_speed = max(speeds)
            avg_speed = sum(speeds) / len(speeds)
            speed_score = min(100, (max_speed / self.speed_threshold) * 100)
            
            # Direction change analysis
            direction_change_score = 0.0
            if len(hist_list) >= 6:
                # Compare direction in first half vs second half
                mid = len(hist_list) // 2
                early = hist_list[:mid]
                late = hist_list[mid:]
                
                def avg_direction(segment):
                    dxs, dys = [], []
                    for i in range(1, len(segment)):
                        dxs.append(segment[i][1][0] - segment[i-1][1][0])
                        dys.append(segment[i][1][1] - segment[i-1][1][1])
                    if not dxs:
                        return (0, 0)
                    return (sum(dxs)/len(dxs), sum(dys)/len(dys))
                
                dir1 = avg_direction(early)
                dir2 = avg_direction(late)
                angle = self._angle_between(dir1, dir2)
                direction_change_score = min(100, (angle / 180) * 100)
            
            # Determine event subtype
            subtype = None
            if max_speed > self.speed_threshold * 1.5:
                subtype = "RUNNING"
            elif direction_change_score > self.direction_change_threshold:
                subtype = "SUDDEN_DIRECTION_CHANGE"
            elif speed_score > 70 and direction_change_score > 50:
                subtype = "ERRATIC"
            
            if subtype:
                confidence = (speed_score * 0.5 + direction_change_score * 0.5)
                events.append(SuspiciousMovementEvent(
                    track_id=tid,
                    event_subtype=subtype,
                    speed_score=speed_score,
                    direction_change_score=direction_change_score,
                    confidence=confidence,
                    bbox=person.bbox
                ))
        
        return events
    
    def clear_track(self, track_id: int):
        self._history.pop(track_id, None)
