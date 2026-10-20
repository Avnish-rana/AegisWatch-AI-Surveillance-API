import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.database import engine, AsyncSessionLocal, init_db
from backend.src.models.user import User
from backend.src.models.camera import Camera
from backend.src.models.responder import Responder
from backend.src.models.zone import Zone
from backend.src.models.incident import Incident
from backend.src.models.system_settings import SystemSettings
from backend.src.auth import hash_password

async def seed():
    print("Initializing DB schema...")
    await init_db()
    
    async with AsyncSessionLocal() as db:
        # 1. Users
        print("Seeding Users...")
        admin = User(username="admin", email="admin@test.com", hashed_password=hash_password("admin123"), role="ADMIN")
        operator = User(username="operator", email="operator@test.com", hashed_password=hash_password("operator123"), role="OPERATOR")
        responder1 = User(username="responder1", email="responder1@test.com", hashed_password=hash_password("resp123"), role="RESPONDER")
        db.add_all([admin, operator, responder1])
        await db.commit()
        
        # 2. Cameras
        print("Seeding Cameras...")
        c1 = Camera(camera_id="CAM-001", name="Main Gate", latitude=28.6139, longitude=77.2090, source_type="DEMO", location_name="Gate 1")
        c2 = Camera(camera_id="CAM-002", name="Parking Area", latitude=28.6140, longitude=77.2095, source_type="DEMO", location_name="Parking")
        c3 = Camera(camera_id="CAM-003", name="Lobby", latitude=28.6135, longitude=77.2085, source_type="DEMO", location_name="Lobby")
        c4 = Camera(camera_id="CAM-004", name="Market Street", latitude=28.6145, longitude=77.2100, source_type="DEMO", location_name="Market")
        c5 = Camera(camera_id="CAM-005", name="Back Exit", latitude=28.6130, longitude=77.2080, source_type="DEMO", location_name="Exit")
        db.add_all([c1, c2, c3, c4, c5])
        await db.commit()
        await db.refresh(c2)
        
        # 3. Responders
        print("Seeding Responders...")
        r1 = Responder(responder_id="R-001", name="Officer Sharma", station="North Station", latitude=28.6150, longitude=77.2110, availability="AVAILABLE", role="PATROL_OFFICER")
        r2 = Responder(responder_id="R-002", name="Officer Patel", station="South Station", latitude=28.6120, longitude=77.2070, availability="AVAILABLE", role="PATROL_OFFICER")
        r3 = Responder(responder_id="R-003", name="Officer Singh", station="East Station", latitude=28.6160, longitude=77.2120, availability="AVAILABLE", role="PATROL_OFFICER")
        r4 = Responder(responder_id="R-004", name="Officer Kumar", station="West Station", latitude=28.6110, longitude=77.2060, availability="OFFLINE", status="OFF_DUTY", role="PATROL_OFFICER")
        r5 = Responder(responder_id="R-005", name="Supervisor Rao", station="HQ", latitude=28.6155, longitude=77.2115, availability="AVAILABLE", role="SUPERVISOR")
        db.add_all([r1, r2, r3, r4, r5])
        
        # 4. Zones
        print("Seeding Zones...")
        z1 = Zone(camera_id=c2.id, zone_name="Restricted Parking Area", zone_type="RESTRICTED", polygon_json="[]", color="#FF0000")
        z2 = Zone(camera_id=c2.id, zone_name="Main Monitoring Zone", zone_type="MONITORING", polygon_json="[]", color="#00FF00")
        db.add_all([z1, z2])
        
        # 5. Incidents
        print("Seeding Incidents...")
        inc1 = Incident(incident_id="INC-2026-00001", incident_type="INTRUSION", severity="HIGH", risk_score=85.0, ai_confidence=92.0, camera_id=c2.id, location_name="Parking", latitude=c2.latitude, longitude=c2.longitude, description="Person in restricted parking", status="NEW")
        db.add(inc1)
        
        # 6. System Settings
        print("Seeding Settings...")
        s1 = SystemSettings(setting_key="confidence_threshold", setting_value="0.6", description="Min AI confidence")
        s2 = SystemSettings(setting_key="cooldown_seconds", setting_value="30", description="Alert cooldown")
        db.add_all([s1, s2])
        
        await db.commit()
        print("Seed complete!")

if __name__ == "__main__":
    asyncio.run(seed())
