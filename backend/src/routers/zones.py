from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.src.database import get_db
from backend.src.models.zone import Zone
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/zones", tags=["zones"])

class ZoneCreate(BaseModel):
    camera_id: str
    zone_name: str
    zone_type: str
    polygon_json: str
    is_active: bool = True
    loitering_threshold_seconds: int = 300
    color: str = "#FF0000"

@router.get("")
async def get_zones(camera_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(Zone)
    if camera_id:
        query = query.where(Zone.camera_id == camera_id)
    res = await db.execute(query)
    return res.scalars().all()

@router.post("")
async def create_zone(data: ZoneCreate, db: AsyncSession = Depends(get_db)):
    z = Zone(**data.dict())
    db.add(z)
    await db.commit()
    return z

@router.get("/{id}")
async def get_zone(id: str, db: AsyncSession = Depends(get_db)):
    z = await db.get(Zone, id)
    if not z: raise HTTPException(404)
    return z

@router.put("/{id}")
async def update_zone(id: str, data: dict, db: AsyncSession = Depends(get_db)):
    z = await db.get(Zone, id)
    if not z: raise HTTPException(404)
    for k,v in data.items(): setattr(z, k, v)
    await db.commit()
    return z

@router.delete("/{id}")
async def delete_zone(id: str, db: AsyncSession = Depends(get_db)):
    z = await db.get(Zone, id)
    if z:
        await db.delete(z)
        await db.commit()
    return {"status": "deleted"}
