from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.database import get_db
from backend.src.models.camera import Camera
import asyncio

router = APIRouter(prefix="/api/stream", tags=["stream"])

async def video_stream(camera_id: str):
    while True:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + b'dummy_frame_data' + b'\r\n')
        await asyncio.sleep(0.1)

@router.get("/{camera_id}")
async def stream_video(camera_id: str, db: AsyncSession = Depends(get_db)):
    camera = await db.get(Camera, camera_id)
    if not camera: raise HTTPException(404)
    return StreamingResponse(video_stream(camera_id), media_type="multipart/x-mixed-replace; boundary=frame")

@router.get("/{camera_id}/snapshot")
async def get_snapshot(camera_id: str, db: AsyncSession = Depends(get_db)):
    return {"status": "snapshot_url"}
