import os
import asyncio
import httpx
import threading
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
AI_API_PORT = int(os.environ.get("AI_API_PORT", "8001"))

app = FastAPI(title="AI Engine API")

class IncidentPayload(BaseModel):
    incident_type: str
    severity: str
    risk_score: float
    ai_confidence: float
    camera_id: str
    location_name: str
    latitude: float
    longitude: float
    description: str
    involved_track_ids: List[int] = []
    snapshot_path: Optional[str] = None
    video_path: Optional[str] = None
    metadata: dict = {}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-engine"}

@app.post("/trigger-incident")
async def trigger_incident(payload: IncidentPayload):
    """Called internally by the AI pipeline to forward incidents to the backend."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{BACKEND_URL}/api/ai/incident",
                json=payload.model_dump()
            )
            return {"forwarded": True, "backend_status": resp.status_code}
        except Exception as e:
            return {"forwarded": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AI_API_PORT)
