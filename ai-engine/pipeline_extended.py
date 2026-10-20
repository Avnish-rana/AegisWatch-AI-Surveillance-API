"""
Extended Surveillance Pipeline
==============================
Extends the AegisEdge SurveillancePipeline with additional detection modules,
risk scoring, evidence capture, and backend integration.

Attribution: Based on AegisEdge-SmartSurveillance by Rishichamp (MIT License)
https://github.com/Rishichamp/AegisEdge-SmartSurveillance
"""

import os
import sys
import time
import threading
import traceback
import httpx
import json
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import SurveillancePipeline
# We use ai-engine instead of ai_engine based on folder structure
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from ai_engine.behavior.abandoned_object import AbandonedObjectDetector
    from ai_engine.behavior.suspicious_movement import SuspiciousMovementDetector
    from ai_engine.risk_engine.risk_scorer import risk_scorer, IncidentType
    from ai_engine.evidence.evidence_capture import EvidenceCapture, FrameBuffer
except ModuleNotFoundError:
    # Handle the hypen in the directory name fallback
    import importlib.util
    import sys
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    spec = importlib.util.spec_from_file_location("abandoned_object", os.path.join(base_dir, "behavior", "abandoned_object.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    AbandonedObjectDetector = mod.AbandonedObjectDetector
    
    spec = importlib.util.spec_from_file_location("suspicious_movement", os.path.join(base_dir, "behavior", "suspicious_movement.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    SuspiciousMovementDetector = mod.SuspiciousMovementDetector
    
    spec = importlib.util.spec_from_file_location("risk_scorer", os.path.join(base_dir, "risk_engine", "risk_scorer.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    risk_scorer = mod.risk_scorer
    IncidentType = mod.IncidentType
    
    spec = importlib.util.spec_from_file_location("evidence_capture", os.path.join(base_dir, "evidence", "evidence_capture.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    EvidenceCapture = mod.EvidenceCapture
    FrameBuffer = mod.FrameBuffer

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

class ExtendedSurveillancePipeline(SurveillancePipeline):
    def __init__(self, config_path: str = "config/default_config.yaml",
                 camera_id: str = "CAM-001",
                 camera_location: str = "Main Area",
                 camera_lat: float = 28.6139,
                 camera_lon: float = 77.2090):
        super().__init__(config_path)
        self.camera_id = camera_id
        self.camera_location = camera_location
        self.camera_lat = camera_lat
        self.camera_lon = camera_lon
        
        # Additional detectors
        self.abandoned_detector = AbandonedObjectDetector(threshold_seconds=30.0)
        self.movement_detector = SuspiciousMovementDetector(speed_threshold=25.0)
        
        # Evidence capture
        self.frame_buffer = FrameBuffer(max_seconds=15.0, fps=10.0)
        self.evidence_capture = EvidenceCapture(camera_id=camera_id, frame_buffer=self.frame_buffer)
        
        # Incident counter for ID generation
        self._incident_counter = int(time.time()) % 100000
        self._incident_lock = threading.Lock()
        
        print(f"[EXTENDED PIPELINE] Camera: {camera_id} @ {camera_location}")
    
    def _generate_incident_id(self) -> str:
        with self._incident_lock:
            self._incident_counter += 1
            year = datetime.now().year
            return f"INC-{year}-{self._incident_counter:05d}"
    
    def _send_incident_to_backend(self, incident_data: dict, snapshot_path: str = None, video_path: str = None):
        """Async-friendly incident forwarding via thread."""
        def _post():
            try:
                payload = {
                    **incident_data,
                    "snapshot_path": snapshot_path,
                    "video_path": video_path,
                }
                import requests
                resp = requests.post(
                    f"{BACKEND_URL}/api/ai/incident",
                    json=payload,
                    timeout=5
                )
                if resp.status_code == 200:
                    print(f"[EXTENDED PIPELINE] Incident forwarded to backend: {incident_data.get('incident_type')}")
                else:
                    print(f"[EXTENDED PIPELINE] Backend returned {resp.status_code}")
            except Exception as e:
                print(f"[EXTENDED PIPELINE] Failed to send incident to backend: {e}")
        
        t = threading.Thread(target=_post, daemon=True)
        t.start()
    
    def _process_loop(self):
        """Override process loop to add extended detectors."""
        frame_idx = 0
        last_time = time.time()
        active_alerts_cache = []
        last_active_tracks = set()
        
        while self.running:
            try:
                frame = self.video_stream.read()
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                frame_idx += 1
                
                # Add to evidence buffer
                self.frame_buffer.add_frame(frame)
                
                frame_skip = getattr(self.config.performance, 'frame_skip', 1)
                if frame_idx % frame_skip != 0:
                    continue
                
                tracker_config = getattr(self.config.tracking, 'tracker', "bytetrack.yaml")
                persist_state = getattr(self.config.tracking, 'persist', True)
                detections = self.detector.detect_and_track(frame, tracker=tracker_config, persist=persist_state)
                
                current_active_tracks = {d.track_id for d in detections if d.track_id is not None}
                lost_tracks = last_active_tracks - current_active_tracks
                for tid in lost_tracks:
                    self.temporal_predictor.clear_track(tid)
                    self.zone_monitor.clear_track(tid)
                    self.movement_detector.clear_track(tid)
                    self.abandoned_detector.clear_track(tid)
                last_active_tracks = current_active_tracks
                
                person_detections = [d for d in detections if d.class_name == "person"]
                
                lstm_predictions = {}
                for person in person_detections:
                    if person.track_id is None:
                        continue
                    features = self.feature_extractor.extract_from_frame(frame, person.bbox)
                    if features is not None:
                        prediction = self.temporal_predictor.add_features(person.track_id, features)
                        if prediction is not None:
                            lstm_predictions[person.track_id] = prediction
                
                frame_triggered_alerts = []
                involved_tracks = []
                
                # A. Fight Detection (from parent)
                fight_detected = False
                fight_conf = 0.0
                if getattr(self.config.anomaly.fight_detection, 'enabled', True):
                    fight_detected, fight_conf, involved_tracks = self.fight_detector.analyze(
                        frame, person_detections, lstm_predictions)
                    if fight_detected:
                        risk_result = risk_scorer.score_fight(
                            ai_confidence=fight_conf*100,
                            proximity_score=min(100, fight_conf*120),
                            motion_score=min(100, fight_conf*110),
                            lstm_score=min(100, fight_conf*100),
                            num_persons=len(involved_tracks)
                        )
                        incident_id = self._generate_incident_id()
                        ev_paths = self.evidence_capture.capture_incident(
                            incident_id, frame, "FIGHT", self.camera_location, involved_tracks)
                        
                        alert = self.alert_engine.trigger(
                            event_type="FIGHT_DETECTED", severity=risk_result.severity.value,
                            confidence=fight_conf,
                            description=f"Physical altercation detected. Tracking IDs: {involved_tracks}",
                            metadata={"involved_tracks": involved_tracks}
                        )
                        if alert:
                            self.dashboard_server.send_alert(alert)
                            frame_triggered_alerts.append(alert)
                            self._send_incident_to_backend({
                                "incident_type": "FIGHT",
                                "severity": risk_result.severity.value,
                                "risk_score": risk_result.risk_score,
                                "ai_confidence": fight_conf * 100,
                                "camera_id": self.camera_id,
                                "location_name": self.camera_location,
                                "latitude": self.camera_lat,
                                "longitude": self.camera_lon,
                                "description": f"Physical altercation detected involving {len(involved_tracks)} person(s).",
                                "involved_track_ids": list(involved_tracks),
                                "metadata": {"risk_signals": [(s.name, s.score) for s in risk_result.signals]}
                            }, ev_paths.get("snapshot"), ev_paths.get("video_clip"))
                
                # B. Zone Intrusion (from parent)
                if getattr(self.config.anomaly.intrusion_detection, 'enabled', True):
                    intrusion_events = self.zone_monitor.check_intrusions(person_detections)
                    for event in intrusion_events:
                        if event["event_type"] == "entry":
                            zone_type = event.get("type", "monitoring")
                            risk_result = risk_scorer.score_intrusion(
                                ai_confidence=85, zone_type=zone_type, dwell_time=0)
                            incident_id = self._generate_incident_id()
                            ev_paths = self.evidence_capture.capture_incident(
                                incident_id, frame, "INTRUSION", self.camera_location,
                                [event["track_id"]])
                            alert = self.alert_engine.trigger(
                                event_type="ZONE_INTRUSION",
                                severity=risk_result.severity.value,
                                confidence=0.85,
                                description=f"Unauthorized entry in '{event['zone_name']}' by Person #{event['track_id']}",
                                metadata=event
                            )
                            if alert:
                                self.dashboard_server.send_alert(alert)
                                frame_triggered_alerts.append(alert)
                                self._send_incident_to_backend({
                                    "incident_type": "INTRUSION",
                                    "severity": risk_result.severity.value,
                                    "risk_score": risk_result.risk_score,
                                    "ai_confidence": 85,
                                    "camera_id": self.camera_id,
                                    "location_name": self.camera_location,
                                    "latitude": self.camera_lat,
                                    "longitude": self.camera_lon,
                                    "description": f"Unauthorized zone intrusion detected in {event['zone_name']}.",
                                    "involved_track_ids": [event["track_id"]],
                                }, ev_paths.get("snapshot"), ev_paths.get("video_clip"))
                
                # C. Theft Detection (from parent, extended)
                if getattr(self.config.anomaly.theft_detection, 'enabled', True):
                    theft_events = self.theft_detector.analyze(detections, frame_idx)
                    for event in theft_events:
                        risk_result = risk_scorer.score_theft(
                            ai_confidence=event["confidence"]*100,
                            proximity_score=min(100, event["confidence"]*120),
                            disappearance_score=90,
                            movement_score=70,
                            temporal_score=80
                        )
                        incident_id = self._generate_incident_id()
                        track_ids = [event["thief_track_id"]] if event.get("thief_track_id") else []
                        ev_paths = self.evidence_capture.capture_incident(
                            incident_id, frame, "THEFT", self.camera_location, track_ids)
                        alert = self.alert_engine.trigger(
                            event_type="THEFT_DETECTED",
                            severity=risk_result.severity.value,
                            confidence=event["confidence"],
                            description=f"Possible theft of '{event['item_class']}'.",
                            metadata=event
                        )
                        if alert:
                            self.dashboard_server.send_alert(alert)
                            frame_triggered_alerts.append(alert)
                            self._send_incident_to_backend({
                                "incident_type": "THEFT",
                                "severity": risk_result.severity.value,
                                "risk_score": risk_result.risk_score,
                                "ai_confidence": event["confidence"] * 100,
                                "camera_id": self.camera_id,
                                "location_name": self.camera_location,
                                "latitude": self.camera_lat,
                                "longitude": self.camera_lon,
                                "description": f"Possible theft detected: '{event['item_class']}' disappeared.",
                                "involved_track_ids": track_ids,
                            }, ev_paths.get("snapshot"), ev_paths.get("video_clip"))
                
                # D. Abandoned Object Detection (NEW)
                abandoned_events = self.abandoned_detector.analyze(detections, frame_idx)
                for event in abandoned_events:
                    risk_result = risk_scorer.score_abandoned_object(
                        duration_seconds=event.duration_seconds,
                        threshold_seconds=30.0,
                        owner_distance=100.0
                    )
                    incident_id = self._generate_incident_id()
                    ev_paths = self.evidence_capture.capture_incident(
                        incident_id, frame, "ABANDONED_OBJECT", self.camera_location,
                        [event.object_track_id])
                    alert = self.alert_engine.trigger(
                        event_type="ABANDONED_OBJECT",
                        severity=risk_result.severity.value,
                        confidence=event.confidence / 100,
                        description=f"Unattended '{event.object_class}' for {event.duration_seconds:.0f}s.",
                        metadata={"object_class": event.object_class, "duration": event.duration_seconds}
                    )
                    if alert:
                        self.dashboard_server.send_alert(alert)
                        frame_triggered_alerts.append(alert)
                        self._send_incident_to_backend({
                            "incident_type": "ABANDONED_OBJECT",
                            "severity": risk_result.severity.value,
                            "risk_score": risk_result.risk_score,
                            "ai_confidence": event.confidence,
                            "camera_id": self.camera_id,
                            "location_name": self.camera_location,
                            "latitude": self.camera_lat,
                            "longitude": self.camera_lon,
                            "description": f"Abandoned {event.object_class} detected, unattended for {event.duration_seconds:.0f} seconds.",
                            "involved_track_ids": [event.object_track_id],
                        }, ev_paths.get("snapshot"), ev_paths.get("video_clip"))
                
                # E. Suspicious Movement Detection (NEW)
                movement_events = self.movement_detector.analyze(detections)
                for event in movement_events:
                    risk_result = risk_scorer.score_suspicious_movement(
                        speed_score=event.speed_score,
                        direction_change_score=event.direction_change_score,
                        ai_confidence=event.confidence
                    )
                    incident_id = self._generate_incident_id()
                    ev_paths = self.evidence_capture.capture_incident(
                        incident_id, frame, "SUSPICIOUS_MOVEMENT", self.camera_location,
                        [event.track_id])
                    alert = self.alert_engine.trigger(
                        event_type="SUSPICIOUS_MOVEMENT",
                        severity=risk_result.severity.value,
                        confidence=event.confidence / 100,
                        description=f"Suspicious movement: {event.event_subtype} by Person #{event.track_id}.",
                        metadata={"subtype": event.event_subtype, "track_id": event.track_id}
                    )
                    if alert:
                        self.dashboard_server.send_alert(alert)
                        frame_triggered_alerts.append(alert)
                        self._send_incident_to_backend({
                            "incident_type": "SUSPICIOUS_MOVEMENT",
                            "severity": risk_result.severity.value,
                            "risk_score": risk_result.risk_score,
                            "ai_confidence": event.confidence,
                            "camera_id": self.camera_id,
                            "location_name": self.camera_location,
                            "latitude": self.camera_lat,
                            "longitude": self.camera_lon,
                            "description": f"Suspicious movement pattern ({event.event_subtype}) detected.",
                            "involved_track_ids": [event.track_id],
                        }, ev_paths.get("snapshot"), ev_paths.get("video_clip"))
                
                # Update caches + FPS
                current_time = time.time()
                if frame_triggered_alerts:
                    active_alerts_cache.extend(frame_triggered_alerts)
                active_alerts_cache = [a for a in active_alerts_cache
                                        if current_time - a["timestamp_unix"] < 3.0]
                
                elapsed = current_time - last_time
                last_time = current_time
                fps_instant = 1.0 / elapsed if elapsed > 0 else 30.0
                self._fps_actual = 0.9 * self._fps_actual + 0.1 * fps_instant if self._fps_actual > 0 else fps_instant
                
                annotated_frame = self.annotator.annotate_frame(
                    frame=frame.copy(),
                    detections=detections,
                    active_alerts=active_alerts_cache,
                    lstm_predictions=lstm_predictions,
                    involved_tracks=involved_tracks,
                    fps=self._fps_actual
                )
                self.dashboard_server.update_frame(annotated_frame)
                
                if frame_idx % 5 == 0:
                    try:
                        import psutil
                        cpu_val = psutil.cpu_percent()
                    except ImportError:
                        cpu_val = 20.0
                    self.dashboard_server.send_metrics(
                        fps=self._fps_actual,
                        tracks=len(current_active_tracks),
                        cpu_percent=cpu_val,
                        camera_source=self.camera_id
                    )
                
                time.sleep(0.005)
            except Exception as e:
                print(f"[EXTENDED PIPELINE] Error: {e}")
                traceback.print_exc()
                time.sleep(0.5)
