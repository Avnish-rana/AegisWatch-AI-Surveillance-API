"""
Risk Scoring Engine
===================
Combines multiple AI detection signals into a single normalized risk score (0-100)
and maps to severity levels: LOW, MEDIUM, HIGH, CRITICAL

Each incident type has a base risk weight. Individual signals (proximity, 
temporal confidence, object disappearance, motion magnitude) scale the score.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IncidentType(str, Enum):
    FIGHT = "FIGHT"
    THEFT = "THEFT"
    INTRUSION = "INTRUSION"
    LOITERING = "LOITERING"
    ABANDONED_OBJECT = "ABANDONED_OBJECT"
    SUSPICIOUS_MOVEMENT = "SUSPICIOUS_MOVEMENT"
    WEAPON_DETECTED = "WEAPON_DETECTED"

@dataclass
class RiskSignal:
    name: str
    score: float  # 0-100
    weight: float  # relative weight
    description: str = ""

@dataclass
class RiskResult:
    incident_type: IncidentType
    risk_score: float  # 0-100
    severity: Severity
    ai_confidence: float  # 0-100
    signals: List[RiskSignal] = field(default_factory=list)
    description: str = ""

class RiskScorer:
    # Base risk scores by incident type (if confidence = 100%)
    BASE_RISK = {
        IncidentType.FIGHT: 85,
        IncidentType.THEFT: 75,
        IncidentType.INTRUSION: 80,
        IncidentType.LOITERING: 50,
        IncidentType.ABANDONED_OBJECT: 70,
        IncidentType.SUSPICIOUS_MOVEMENT: 55,
        IncidentType.WEAPON_DETECTED: 95,
    }
    
    # Severity thresholds
    SEVERITY_THRESHOLDS = {
        Severity.CRITICAL: 80,
        Severity.HIGH: 60,
        Severity.MEDIUM: 40,
        Severity.LOW: 0,
    }
    
    def score_fight(self, ai_confidence: float, proximity_score: float, motion_score: float, lstm_score: float, num_persons: int) -> RiskResult:
        signals = [
            RiskSignal("Fight Probability", ai_confidence, 0.35, "LSTM fight classifier output"),
            RiskSignal("Person Proximity", proximity_score, 0.25, "How close persons are to each other"),
            RiskSignal("Motion Magnitude", motion_score, 0.25, "Optical flow motion energy"),
            RiskSignal("LSTM Score", lstm_score, 0.15, "Temporal sequence anomaly"),
        ]
        risk = self._weighted_score(signals)
        if num_persons >= 3:
            risk = min(100, risk * 1.1)
        return RiskResult(IncidentType.FIGHT, risk, self._severity(risk), ai_confidence, signals)
    
    def score_theft(self, ai_confidence: float, proximity_score: float, disappearance_score: float, movement_score: float, temporal_score: float) -> RiskResult:
        signals = [
            RiskSignal("Theft Probability", ai_confidence, 0.30),
            RiskSignal("Object Disappearance", disappearance_score, 0.30),
            RiskSignal("Person Proximity", proximity_score, 0.20),
            RiskSignal("Movement Anomaly", movement_score, 0.10),
            RiskSignal("Temporal Confirmation", temporal_score, 0.10),
        ]
        risk = self._weighted_score(signals)
        return RiskResult(IncidentType.THEFT, risk, self._severity(risk), ai_confidence, signals)
    
    def score_intrusion(self, ai_confidence: float, zone_type: str, dwell_time: float) -> RiskResult:
        zone_factor = 1.0 if zone_type == "restricted" else 0.7
        time_factor = min(100, 50 + dwell_time * 2)
        signals = [
            RiskSignal("Intrusion Confidence", ai_confidence, 0.50),
            RiskSignal("Zone Severity", zone_factor * 100, 0.30),
            RiskSignal("Dwell Time", time_factor, 0.20),
        ]
        risk = self._weighted_score(signals)
        return RiskResult(IncidentType.INTRUSION, risk, self._severity(risk), ai_confidence, signals)
    
    def score_loitering(self, duration_seconds: float, zone_type: str, threshold_seconds: float) -> RiskResult:
        ratio = min(1.0, duration_seconds / max(threshold_seconds, 1))
        base = 40 + ratio * 40
        zone_factor = 1.2 if zone_type == "restricted" else 1.0
        risk = min(100, base * zone_factor)
        confidence = 60 + ratio * 30
        signals = [
            RiskSignal("Loitering Duration", ratio * 100, 0.60),
            RiskSignal("Zone Risk", zone_factor * 70, 0.40),
        ]
        return RiskResult(IncidentType.LOITERING, risk, self._severity(risk), confidence, signals)
    
    def score_abandoned_object(self, duration_seconds: float, threshold_seconds: float, owner_distance: float) -> RiskResult:
        time_ratio = min(1.0, duration_seconds / max(threshold_seconds, 1))
        distance_score = min(100, owner_distance * 5)
        risk = time_ratio * 60 + distance_score * 0.40
        confidence = 50 + time_ratio * 40
        signals = [
            RiskSignal("Unattended Duration", time_ratio * 100, 0.60),
            RiskSignal("Owner Distance", distance_score, 0.40),
        ]
        return RiskResult(IncidentType.ABANDONED_OBJECT, risk, self._severity(risk), confidence, signals)
    
    def score_suspicious_movement(self, speed_score: float, direction_change_score: float, ai_confidence: float) -> RiskResult:
        signals = [
            RiskSignal("Movement Speed", speed_score, 0.40),
            RiskSignal("Direction Change", direction_change_score, 0.35),
            RiskSignal("Detection Confidence", ai_confidence, 0.25),
        ]
        risk = self._weighted_score(signals)
        return RiskResult(IncidentType.SUSPICIOUS_MOVEMENT, risk, self._severity(risk), ai_confidence, signals)
    
    def _weighted_score(self, signals: List[RiskSignal]) -> float:
        total_weight = sum(s.weight for s in signals)
        if total_weight == 0:
            return 0
        weighted_sum = sum(s.score * s.weight for s in signals)
        return round(min(100, max(0, weighted_sum / total_weight)), 1)
    
    def _severity(self, risk: float) -> Severity:
        if risk >= self.SEVERITY_THRESHOLDS[Severity.CRITICAL]:
            return Severity.CRITICAL
        elif risk >= self.SEVERITY_THRESHOLDS[Severity.HIGH]:
            return Severity.HIGH
        elif risk >= self.SEVERITY_THRESHOLDS[Severity.MEDIUM]:
            return Severity.MEDIUM
        return Severity.LOW

# Global singleton
risk_scorer = RiskScorer()
