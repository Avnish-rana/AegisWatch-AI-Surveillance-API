import os
import textwrap

BASE_DIR = r"C:\Users\itsav\.gemini\antigravity\scratch\AI-Surveillance-System"

FILES = {
    "backend/__init__.py": "",
    "backend/src/__init__.py": "",
    "backend/src/routers/__init__.py": "",
    "backend/src/services/__init__.py": "",
    "backend/src/models/__init__.py": textwrap.dedent("""\
        from .user import User
        from .camera import Camera
        from .incident import Incident
        from .evidence import Evidence
        from .responder import Responder
        from .assignment import Assignment
        from .zone import Zone
        from .detection_log import DetectionLog
        from .status_history import IncidentStatusHistory
        from .system_settings import SystemSettings
    """),
    
    "backend/src/database.py": textwrap.dedent("""\
        import os
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from sqlalchemy.orm import DeclarativeBase

        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./surveillance.db")
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
        elif DATABASE_URL.startswith("postgresql://"):
            DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(DATABASE_URL, echo=False)
        AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

        class Base(DeclarativeBase):
            pass

        async def get_db():
            async with AsyncSessionLocal() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        async def init_db():
            async with engine.begin() as conn:
                from backend.src.models import (
                    User, Camera, Incident, Evidence, Responder, Assignment, 
                    Zone, DetectionLog, IncidentStatusHistory, SystemSettings
                )
                await conn.run_sync(Base.metadata.create_all)
    """),
    
    "backend/src/models/user.py": textwrap.dedent("""\
        from sqlalchemy import Column, String, Boolean, DateTime
        from sqlalchemy.sql import func
        from backend.src.database import Base
        import uuid

        class User(Base):
            __tablename__ = "users"
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            username = Column(String, unique=True, index=True)
            email = Column(String, unique=True, index=True)
            hashed_password = Column(String)
            role = Column(String, default="OPERATOR") # ADMIN, OPERATOR, RESPONDER
            is_active = Column(Boolean, default=True)
            created_at = Column(DateTime(timezone=True), server_default=func.now())
            updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """),

    "backend/src/models/camera.py": textwrap.dedent("""\
        from sqlalchemy import Column, String, Float, Boolean, Text, DateTime
        from sqlalchemy.sql import func
        from backend.src.database import Base
        import uuid

        class Camera(Base):
            __tablename__ = "cameras"
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            camera_id = Column(String, unique=True, index=True)
            name = Column(String)
            description = Column(String, nullable=True)
            source_type = Column(String) # RTSP, WEBCAM, FILE, DEMO
            source_url = Column(String)
            location_name = Column(String)
            latitude = Column(Float)
            longitude = Column(Float)
            status = Column(String, default="OFFLINE") # ONLINE, OFFLINE, ERROR
            is_enabled = Column(Boolean, default=True)
            config_json = Column(Text, nullable=True)
            created_at = Column(DateTime(timezone=True), server_default=func.now())
            updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """),

    "backend/src/models/incident.py": textwrap.dedent("""\
        from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey
        from sqlalchemy.sql import func
        from backend.src.database import Base
        import uuid

        class Incident(Base):
            __tablename__ = "incidents"
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            incident_id = Column(String, unique=True, index=True)
            incident_type = Column(String)
            severity = Column(String)
            risk_score = Column(Float)
            ai_confidence = Column(Float)
            camera_id = Column(String, ForeignKey("cameras.id"))
            location_name = Column(String)
            latitude = Column(Float)
            longitude = Column(Float)
            description = Column(Text)
            involved_track_ids = Column(Text)
            status = Column(String, default="NEW")
            assigned_responder_id = Column(String, ForeignKey("responders.id"), nullable=True)
            resolution_notes = Column(Text, nullable=True)
            created_at = Column(DateTime(timezone=True), server_default=func.now())
            updated_at = Column(DateTime(timezone=True), onupdate=func.now())
            resolved_at = Column(DateTime(timezone=True), nullable=True)
    """),

    "backend/src/models/evidence.py": textwrap.dedent("""\
        from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
        from sqlalchemy.sql import func
        from backend.src.database import Base
        import uuid

        class Evidence(Base):
            __tablename__ = "evidence"
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            incident_id = Column(String, ForeignKey("incidents.id"))
            evidence_type = Column(String)
            file_path = Column(Text)
            file_name = Column(Text)
            file_size = Column(Integer, nullable=True)
            timestamp = Column(DateTime(timezone=True), default=func.now())
            metadata_json = Column(Text, nullable=True)
            created_at = Column(DateTime(timezone=True), server_default=func.now())
    """),

    "backend/src/models/responder.py": textwrap.dedent("""\
        from sqlalchemy import Column, String, Float, DateTime, ForeignKey
        from sqlalchemy.sql import func
        from backend.src.database import Base
        import uuid

        class Responder(Base):
            __tablename__ = "responders"
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            responder_id = Column(String, unique=True, index=True)
            name = Column(String)
            station = Column(String)
            phone = Column(String, nullable=True)
            email = Column(String, nullable=True)
            latitude = Column(Float)
            longitude = Column(Float)
            availability = Column(String, default="AVAILABLE")
            role = Column(String)
            status = Column(String, default="ON_DUTY")
            user_id = Column(String, ForeignKey("users.id"), nullable=True)
            created_at = Column(DateTime(timezone=True), server_default=func.now())
            updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """),

    "backend/src/models/assignment.py": textwrap.dedent("""\
        from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey
        from sqlalchemy.sql import func
        from backend.src.database import Base
        import uuid

        class Assignment(Base):
            __tablename__ = "assignments"
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            incident_id = Column(String, ForeignKey("incidents.id"))
            responder_id = Column(String, ForeignKey("responders.id"))
            assigned_by = Column(String, ForeignKey("users.id"))
            distance_km = Column(Float)
            assigned_at = Column(DateTime(timezone=True), server_default=func.now())
            accepted_at = Column(DateTime(timezone=True), nullable=True)
            arrived_at = Column(DateTime(timezone=True), nullable=True)
            resolved_at = Column(DateTime(timezone=True), nullable=True)
            status = Column(String, default="PENDING")
            rejection_reason = Column(Text, nullable=True)
            notes = Column(Text, nullable=True)
    """),

    "backend/src/models/zone.py": textwrap.dedent("""\
        from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime, ForeignKey
        from sqlalchemy.sql import func
        from backend.src.database import Base
        import uuid

        class Zone(Base):
            __tablename__ = "zones"
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            camera_id = Column(String, ForeignKey("cameras.id"))
            zone_name = Column(String)
            zone_type = Column(String)
            polygon_json = Column(Text)
            is_active = Column(Boolean, default=True)
            loitering_threshold_seconds = Column(Integer, default=300)
            color = Column(String)
            created_at = Column(DateTime(timezone=True), server_default=func.now())
            updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """),

    "backend/src/models/detection_log.py": textwrap.dedent("""\
        from sqlalchemy import Column, String, Float, Text, Integer, DateTime, ForeignKey
        from sqlalchemy.sql import func
        from backend.src.database import Base
        import uuid

        class DetectionLog(Base):
            __tablename__ = "detection_logs"
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            camera_id = Column(String, ForeignKey("cameras.id"))
            frame_number = Column(Integer)
            track_id = Column(Integer)
            class_name = Column(String)
            confidence = Column(Float)
            bbox_json = Column(Text)
            event_type = Column(String, nullable=True)
            risk_score = Column(Float, nullable=True)
            timestamp = Column(DateTime(timezone=True), default=func.now())
            incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)
    """),

    "backend/src/models/status_history.py": textwrap.dedent("""\
        from sqlalchemy import Column, String, Text, DateTime, ForeignKey
        from sqlalchemy.sql import func
        from backend.src.database import Base
        import uuid

        class IncidentStatusHistory(Base):
            __tablename__ = "incident_status_history"
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            incident_id = Column(String, ForeignKey("incidents.id"))
            from_status = Column(String)
            to_status = Column(String)
            changed_by = Column(String, ForeignKey("users.id"), nullable=True)
            notes = Column(Text, nullable=True)
            changed_at = Column(DateTime(timezone=True), default=func.now())
    """),

    "backend/src/models/system_settings.py": textwrap.dedent("""\
        from sqlalchemy import Column, String, Text, Integer, DateTime
        from sqlalchemy.sql import func
        from backend.src.database import Base

        class SystemSettings(Base):
            __tablename__ = "system_settings"
            id = Column(Integer, primary_key=True, autoincrement=True)
            setting_key = Column(String, unique=True, index=True)
            setting_value = Column(Text)
            description = Column(Text, nullable=True)
            updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    """),

    "backend/src/auth.py": textwrap.dedent("""\
        import os
        from datetime import datetime, timedelta
        from typing import Optional
        from jose import JWTError, jwt
        from passlib.context import CryptContext
        from fastapi import Depends, HTTPException, status
        from fastapi.security import OAuth2PasswordBearer
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.future import select

        from backend.src.database import get_db
        from backend.src.models.user import User

        SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

        def verify_password(plain_password, hashed_password):
            return pwd_context.verify(plain_password, hashed_password)

        def hash_password(password):
            return pwd_context.hash(password)

        def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
            to_encode = data.copy()
            expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
            to_encode.update({"exp": expire})
            return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        def verify_token(token: str):
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                return payload
            except JWTError:
                return None

        async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
            payload = verify_token(token)
            if payload is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalars().first()
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
            return user

        async def get_current_admin(current_user: User = Depends(get_current_user)):
            if current_user.role != "ADMIN":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
            return current_user
    """),

    "backend/src/routers/auth.py": textwrap.dedent("""\
        from fastapi import APIRouter, Depends, HTTPException, status
        from fastapi.security import OAuth2PasswordRequestForm
        from sqlalchemy.ext.asyncio import AsyncSession
        from backend.src.database import get_db
        from backend.src.auth import authenticate_user, create_access_token, get_current_user
        from backend.src.services.auth_service import authenticate_user
        from pydantic import BaseModel

        router = APIRouter(prefix="/api/auth", tags=["auth"])

        class Token(BaseModel):
            access_token: str
            token_type: str
            user: dict

        @router.post("/login", response_model=Token)
        async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
            user = await authenticate_user(db, form_data.username, form_data.password)
            if not user:
                raise HTTPException(status_code=401, detail="Incorrect username or password")
            access_token = create_access_token(data={"sub": user.username})
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {"id": user.id, "username": user.username, "email": user.email, "role": user.role}
            }

        @router.get("/me")
        async def get_me(current_user = Depends(get_current_user)):
            return {"id": current_user.id, "username": current_user.username, "email": current_user.email, "role": current_user.role}

        @router.post("/logout")
        async def logout():
            return {"message": "Successfully logged out"}
    """),

    "backend/src/routers/cameras.py": textwrap.dedent("""\
        from fastapi import APIRouter, Depends, HTTPException
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.future import select
        from backend.src.database import get_db
        from backend.src.models.camera import Camera
        from backend.src.auth import get_current_user, get_current_admin
        from pydantic import BaseModel
        from typing import List, Optional

        router = APIRouter(prefix="/api/cameras", tags=["cameras"])

        class CameraCreate(BaseModel):
            camera_id: str
            name: str
            description: Optional[str] = None
            source_type: str
            source_url: str
            location_name: str
            latitude: float
            longitude: float
            config_json: Optional[str] = None

        @router.get("")
        async def get_cameras(status: Optional[str] = None, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
            query = select(Camera)
            if status:
                query = query.where(Camera.status == status)
            result = await db.execute(query.offset(skip).limit(limit))
            return result.scalars().all()

        @router.post("")
        async def create_camera(camera: CameraCreate, db: AsyncSession = Depends(get_db), admin = Depends(get_current_admin)):
            db_camera = Camera(**camera.dict())
            db.add(db_camera)
            await db.commit()
            await db.refresh(db_camera)
            return db_camera

        @router.get("/{camera_id}")
        async def get_camera(camera_id: str, db: AsyncSession = Depends(get_db)):
            camera = await db.get(Camera, camera_id)
            if not camera:
                raise HTTPException(status_code=404, detail="Camera not found")
            return camera

        @router.put("/{camera_id}")
        async def update_camera(camera_id: str, camera_data: dict, db: AsyncSession = Depends(get_db), admin = Depends(get_current_admin)):
            camera = await db.get(Camera, camera_id)
            if not camera:
                raise HTTPException(status_code=404)
            for k, v in camera_data.items():
                setattr(camera, k, v)
            await db.commit()
            await db.refresh(camera)
            return camera

        @router.delete("/{camera_id}")
        async def delete_camera(camera_id: str, db: AsyncSession = Depends(get_db), admin = Depends(get_current_admin)):
            camera = await db.get(Camera, camera_id)
            if camera:
                camera.is_enabled = False
                await db.commit()
            return {"status": "disabled"}

        @router.get("/{camera_id}/stream-info")
        async def stream_info(camera_id: str, db: AsyncSession = Depends(get_db)):
            camera = await db.get(Camera, camera_id)
            if not camera:
                raise HTTPException(status_code=404)
            return {"stream_url": f"/api/stream/{camera.id}"}

        @router.post("/{camera_id}/toggle")
        async def toggle_camera(camera_id: str, db: AsyncSession = Depends(get_db), admin = Depends(get_current_admin)):
            camera = await db.get(Camera, camera_id)
            if not camera:
                raise HTTPException(status_code=404)
            camera.is_enabled = not camera.is_enabled
            await db.commit()
            return {"is_enabled": camera.is_enabled}
    """),

    "backend/src/routers/incidents.py": textwrap.dedent("""\
        from fastapi import APIRouter, Depends, HTTPException
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.future import select
        from backend.src.database import get_db
        from backend.src.models.incident import Incident
        from backend.src.services.incident_service import create_incident, transition_status, get_incident_with_details
        from backend.src.services.responder_service import assign_nearest_available
        from backend.src.auth import get_current_user
        from pydantic import BaseModel
        from typing import Optional

        router = APIRouter(prefix="/api/incidents", tags=["incidents"])

        @router.get("")
        async def get_incidents(status: Optional[str] = None, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
            query = select(Incident)
            if status:
                query = query.where(Incident.status == status)
            result = await db.execute(query.order_by(Incident.created_at.desc()).offset(skip).limit(limit))
            return result.scalars().all()

        @router.get("/{incident_id}")
        async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
            return await get_incident_with_details(db, incident_id)

        @router.post("")
        async def create_new_incident(incident_data: dict, db: AsyncSession = Depends(get_db)):
            return await create_incident(db, incident_data)

        @router.post("/{incident_id}/verify")
        async def verify_incident(incident_id: str, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
            return await transition_status(db, incident_id, "VERIFIED", user.id, "Verified by operator")

        class RejectReason(BaseModel):
            reason: str

        @router.post("/{incident_id}/reject")
        async def reject_incident(incident_id: str, data: RejectReason, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
            return await transition_status(db, incident_id, "FALSE_POSITIVE", user.id, data.reason)

        class AssignData(BaseModel):
            responder_id: Optional[str] = None

        @router.post("/{incident_id}/assign")
        async def assign_incident(incident_id: str, data: AssignData, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
            if data.responder_id:
                # Manual assign
                return await transition_status(db, incident_id, "ASSIGNED", user.id, f"Assigned to {data.responder_id}")
            else:
                return await assign_nearest_available(db, incident_id, user.id)

        @router.post("/{incident_id}/accept")
        async def accept_incident(incident_id: str, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
            return await transition_status(db, incident_id, "ACCEPTED", user.id, "Responder accepted")

        @router.post("/{incident_id}/responding")
        async def responding_incident(incident_id: str, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
            return await transition_status(db, incident_id, "RESPONDING", user.id, "Responder en route")

        class ResolveData(BaseModel):
            notes: str

        @router.post("/{incident_id}/resolve")
        async def resolve_incident(incident_id: str, data: ResolveData, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
            return await transition_status(db, incident_id, "RESOLVED", user.id, data.notes)

        @router.post("/{incident_id}/cancel")
        async def cancel_incident(incident_id: str, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
            return await transition_status(db, incident_id, "CANCELLED", user.id, "Cancelled manually")

        @router.get("/{incident_id}/evidence")
        async def get_incident_evidence(incident_id: str, db: AsyncSession = Depends(get_db)):
            from backend.src.models.evidence import Evidence
            result = await db.execute(select(Evidence).where(Evidence.incident_id == incident_id))
            return result.scalars().all()

        @router.get("/{incident_id}/history")
        async def get_incident_history(incident_id: str, db: AsyncSession = Depends(get_db)):
            from backend.src.models.status_history import IncidentStatusHistory
            result = await db.execute(select(IncidentStatusHistory).where(IncidentStatusHistory.incident_id == incident_id).order_by(IncidentStatusHistory.changed_at.asc()))
            return result.scalars().all()
    """),

    "backend/src/routers/responders.py": textwrap.dedent("""\
        from fastapi import APIRouter, Depends, HTTPException
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.future import select
        from backend.src.database import get_db
        from backend.src.models.responder import Responder
        from backend.src.models.assignment import Assignment
        from backend.src.auth import get_current_user, get_current_admin
        from backend.src.services.responder_service import find_nearest_responders
        from pydantic import BaseModel

        router = APIRouter(prefix="/api/responders", tags=["responders"])

        @router.get("")
        async def get_responders(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Responder))
            return result.scalars().all()

        class ResponderCreate(BaseModel):
            responder_id: str
            name: str
            station: str
            phone: str = None
            email: str = None
            latitude: float
            longitude: float
            role: str

        @router.post("")
        async def create_responder(data: ResponderCreate, db: AsyncSession = Depends(get_db), admin = Depends(get_current_admin)):
            resp = Responder(**data.dict())
            db.add(resp)
            await db.commit()
            return resp

        @router.get("/nearest")
        async def get_nearest(lat: float, lon: float, db: AsyncSession = Depends(get_db)):
            return await find_nearest_responders(db, lat, lon)

        @router.get("/{id}")
        async def get_responder(id: str, db: AsyncSession = Depends(get_db)):
            r = await db.get(Responder, id)
            if not r: raise HTTPException(404)
            return r

        @router.put("/{id}")
        async def update_responder(id: str, data: dict, db: AsyncSession = Depends(get_db)):
            r = await db.get(Responder, id)
            if not r: raise HTTPException(404)
            for k,v in data.items(): setattr(r, k, v)
            await db.commit()
            return r
        
        class AvailData(BaseModel):
            availability: str

        @router.post("/{id}/availability")
        async def update_availability(id: str, data: AvailData, db: AsyncSession = Depends(get_db)):
            r = await db.get(Responder, id)
            if not r: raise HTTPException(404)
            r.availability = data.availability
            await db.commit()
            return r

        @router.get("/{id}/assignments")
        async def get_assignments(id: str, db: AsyncSession = Depends(get_db)):
            res = await db.execute(select(Assignment).where(Assignment.responder_id == id))
            return res.scalars().all()
    """),

    "backend/src/routers/evidence.py": textwrap.dedent("""\
        from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
        from fastapi.responses import FileResponse
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.future import select
        from backend.src.database import get_db
        from backend.src.models.evidence import Evidence
        import os
        import uuid

        router = APIRouter(prefix="/api/evidence", tags=["evidence"])
        EVIDENCE_DIR = os.path.join(os.getcwd(), "data", "evidence")
        os.makedirs(EVIDENCE_DIR, exist_ok=True)

        @router.get("/{incident_id}")
        async def get_evidence_for_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
            res = await db.execute(select(Evidence).where(Evidence.incident_id == incident_id))
            return res.scalars().all()

        @router.get("/file/{evidence_id}")
        async def serve_file(evidence_id: str, db: AsyncSession = Depends(get_db)):
            ev = await db.get(Evidence, evidence_id)
            if not ev or not os.path.exists(ev.file_path):
                raise HTTPException(404)
            return FileResponse(ev.file_path)

        @router.post("/{incident_id}")
        async def upload_evidence(incident_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
            ext = file.filename.split('.')[-1]
            file_path = os.path.join(EVIDENCE_DIR, f"{uuid.uuid4()}.{ext}")
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            ev = Evidence(
                incident_id=incident_id,
                evidence_type="SNAPSHOT" if ext in ['jpg', 'png', 'jpeg'] else "VIDEO_CLIP",
                file_path=file_path,
                file_name=file.filename,
                file_size=len(content)
            )
            db.add(ev)
            await db.commit()
            return ev
    """),

    "backend/src/routers/analytics.py": textwrap.dedent("""\
        from fastapi import APIRouter, Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.future import select
        from sqlalchemy import func
        from backend.src.database import get_db
        from backend.src.models.incident import Incident
        from backend.src.models.camera import Camera

        router = APIRouter(prefix="/api/analytics", tags=["analytics"])

        @router.get("/summary")
        async def get_summary(db: AsyncSession = Depends(get_db)):
            cameras = await db.execute(select(func.count(Camera.id)))
            online_cameras = await db.execute(select(func.count(Camera.id)).where(Camera.status == "ONLINE"))
            active_incidents = await db.execute(select(func.count(Incident.id)).where(Incident.status.in_(["NEW", "UNDER_REVIEW", "VERIFIED", "ASSIGNED", "ACCEPTED", "RESPONDING"])))
            
            return {
                "total_cameras": cameras.scalar() or 0,
                "online_cameras": online_cameras.scalar() or 0,
                "active_incidents": active_incidents.scalar() or 0,
                "today_incidents": 0,
                "high_risk": 0,
                "resolved_today": 0
            }

        @router.get("/incidents-by-type")
        async def get_incidents_by_type(db: AsyncSession = Depends(get_db)):
            res = await db.execute(select(Incident.incident_type, func.count(Incident.id)).group_by(Incident.incident_type))
            return [{"type": row[0], "count": row[1]} for row in res.all()]

        @router.get("/incidents-by-camera")
        async def get_incidents_by_camera(db: AsyncSession = Depends(get_db)):
            res = await db.execute(select(Incident.camera_id, func.count(Incident.id)).group_by(Incident.camera_id))
            return [{"camera_id": row[0], "count": row[1]} for row in res.all()]

        @router.get("/incidents-by-hour")
        async def get_by_hour():
            return []

        @router.get("/severity-distribution")
        async def get_severity(db: AsyncSession = Depends(get_db)):
            res = await db.execute(select(Incident.severity, func.count(Incident.id)).group_by(Incident.severity))
            return [{"severity": row[0], "count": row[1]} for row in res.all()]

        @router.get("/response-times")
        async def get_resp_times():
            return {"avg_time_minutes": 5.5}
    """),

    "backend/src/routers/zones.py": textwrap.dedent("""\
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
    """),

    "backend/src/routers/stream.py": textwrap.dedent("""\
        from fastapi import APIRouter, Depends, HTTPException
        from fastapi.responses import StreamingResponse, FileResponse
        from sqlalchemy.ext.asyncio import AsyncSession
        from backend.src.database import get_db
        from backend.src.models.camera import Camera
        import os
        import asyncio

        router = APIRouter(prefix="/api/stream", tags=["stream"])

        # Dummy stream generator for demo cameras
        async def video_stream(camera_id: str):
            # In a real app this would yield multipart JPEG frames
            while True:
                yield (b'--frame\\r\\n'
                       b'Content-Type: image/jpeg\\r\\n\\r\\n' + b'dummy_frame_data' + b'\\r\\n')
                await asyncio.sleep(0.1)

        @router.get("/{camera_id}")
        async def stream_video(camera_id: str, db: AsyncSession = Depends(get_db)):
            camera = await db.get(Camera, camera_id)
            if not camera: raise HTTPException(404)
            return StreamingResponse(video_stream(camera_id), media_type="multipart/x-mixed-replace; boundary=frame")

        @router.get("/{camera_id}/snapshot")
        async def get_snapshot(camera_id: str, db: AsyncSession = Depends(get_db)):
            return {"status": "snapshot_url"}
    """),

    "backend/src/services/incident_service.py": textwrap.dedent("""\
        from datetime import datetime
        import uuid
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.future import select
        from backend.src.models.incident import Incident
        from backend.src.models.status_history import IncidentStatusHistory
        from backend.src.models.evidence import Evidence
        from backend.src.services.alert_service import broadcast_incident_alert

        def generate_incident_id():
            now = datetime.now()
            # Simple format: INC-YYYY-UUID
            return f"INC-{now.year}-{str(uuid.uuid4())[:8].upper()}"

        async def create_incident(db: AsyncSession, incident_data: dict) -> Incident:
            incident = Incident(
                incident_id=generate_incident_id(),
                incident_type=incident_data.get("incident_type"),
                severity=incident_data.get("severity", "LOW"),
                risk_score=incident_data.get("risk_score", 0.0),
                ai_confidence=incident_data.get("ai_confidence", 0.0),
                camera_id=incident_data.get("camera_id"),
                location_name=incident_data.get("location_name"),
                latitude=incident_data.get("latitude"),
                longitude=incident_data.get("longitude"),
                description=incident_data.get("description", ""),
                involved_track_ids=incident_data.get("involved_track_ids", "[]")
            )
            db.add(incident)
            await db.flush()
            
            history = IncidentStatusHistory(
                incident_id=incident.id,
                from_status="",
                to_status="NEW",
                notes="Incident created by AI engine"
            )
            db.add(history)
            await db.commit()
            await db.refresh(incident)
            
            # Broadcast to web socket
            await broadcast_incident_alert({"event": "NEW_INCIDENT", "data": {"id": incident.id, "type": incident.incident_type}})
            return incident

        async def transition_status(db: AsyncSession, incident_id: str, new_status: str, user_id: str, notes: str) -> Incident:
            incident = await db.get(Incident, incident_id)
            if not incident: return None
            
            old_status = incident.status
            incident.status = new_status
            if new_status in ["RESOLVED", "FALSE_POSITIVE", "CANCELLED"]:
                incident.resolved_at = datetime.utcnow()
                if new_status == "RESOLVED":
                    incident.resolution_notes = notes
                    
            history = IncidentStatusHistory(
                incident_id=incident.id,
                from_status=old_status,
                to_status=new_status,
                changed_by=user_id,
                notes=notes
            )
            db.add(history)
            await db.commit()
            await db.refresh(incident)
            return incident

        async def get_incident_with_details(db: AsyncSession, incident_id: str) -> dict:
            incident = await db.get(Incident, incident_id)
            if not incident: return None
            
            ev_res = await db.execute(select(Evidence).where(Evidence.incident_id == incident_id))
            evidence = ev_res.scalars().all()
            
            hist_res = await db.execute(select(IncidentStatusHistory).where(IncidentStatusHistory.incident_id == incident_id))
            history = hist_res.scalars().all()
            
            return {
                "incident": incident,
                "evidence": evidence,
                "history": history
            }
    """),

    "backend/src/services/responder_service.py": textwrap.dedent("""\
        from math import radians, cos, sin, asin, sqrt
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.future import select
        from backend.src.models.responder import Responder
        from backend.src.models.assignment import Assignment
        from backend.src.services.incident_service import transition_status

        def haversine_distance(lat1, lon1, lat2, lon2) -> float:
            R = 6371  # Earth radius in kilometers
            phi1, phi2 = radians(lat1), radians(lat2)
            dphi = radians(lat2 - lat1)
            dlambda = radians(lon2 - lon1)
            a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
            c = 2 * asin(sqrt(a))
            return R * c

        async def find_nearest_responders(db: AsyncSession, incident_lat: float, incident_lon: float, limit: int = 5) -> list:
            result = await db.execute(select(Responder).where(Responder.availability == "AVAILABLE", Responder.status == "ON_DUTY"))
            responders = result.scalars().all()
            
            with_dist = []
            for r in responders:
                dist = haversine_distance(incident_lat, incident_lon, r.latitude, r.longitude)
                with_dist.append((dist, r))
                
            with_dist.sort(key=lambda x: x[0])
            return [{"distance_km": d, "responder": r} for d, r in with_dist[:limit]]

        async def assign_nearest_available(db: AsyncSession, incident_id: str, assigned_by_user_id: str):
            from backend.src.models.incident import Incident
            incident = await db.get(Incident, incident_id)
            if not incident: return None
            
            nearest = await find_nearest_responders(db, incident.latitude, incident.longitude, 1)
            if not nearest:
                return None # No available responders
            
            best = nearest[0]
            resp = best["responder"]
            dist = best["distance_km"]
            
            assignment = Assignment(
                incident_id=incident_id,
                responder_id=resp.id,
                assigned_by=assigned_by_user_id,
                distance_km=dist
            )
            db.add(assignment)
            
            resp.availability = "BUSY"
            
            await db.commit()
            await transition_status(db, incident_id, "ASSIGNED", assigned_by_user_id, f"Auto-assigned to {resp.name}")
            return assignment
    """),

    "backend/src/services/auth_service.py": textwrap.dedent("""\
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.future import select
        from backend.src.models.user import User
        from backend.src.auth import verify_password, hash_password

        async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
            result = await db.execute(select(User).where(User.username == username))
            return result.scalars().first()

        async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
            user = await get_user_by_username(db, username)
            if not user:
                return None
            if not verify_password(password, user.hashed_password):
                return None
            return user

        async def create_user(db: AsyncSession, username: str, email: str, password: str, role: str) -> User:
            hashed = hash_password(password)
            user = User(username=username, email=email, hashed_password=hashed, role=role)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user
    """),

    "backend/src/services/alert_service.py": textwrap.dedent("""\
        from fastapi import WebSocket

        class ConnectionManager:
            def __init__(self):
                self.active_connections: list[WebSocket] = []

            async def connect(self, websocket: WebSocket):
                await websocket.accept()
                self.active_connections.append(websocket)

            def disconnect(self, websocket: WebSocket):
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)

            async def broadcast(self, message: dict):
                for connection in self.active_connections:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        pass
                        
            async def send_personal(self, websocket: WebSocket, message: dict):
                await websocket.send_json(message)

        manager = ConnectionManager()

        async def broadcast_incident_alert(incident_data: dict, assignment=None):
            await manager.broadcast({
                "type": "INCIDENT_ALERT",
                "incident": incident_data,
                "assignment": assignment
            })
    """),

    "backend/src/main.py": textwrap.dedent("""\
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
        from fastapi.middleware.cors import CORSMiddleware
        from contextlib import asynccontextmanager
        import os

        from backend.src.database import init_db, get_db
        from backend.src.routers import auth, cameras, incidents, responders, evidence, analytics, zones, stream
        from backend.src.services.alert_service import manager
        from backend.src.services.incident_service import create_incident

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await init_db()
            yield

        app = FastAPI(title="AI Surveillance System API", lifespan=lifespan)

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        app.include_router(auth.router)
        app.include_router(cameras.router)
        app.include_router(incidents.router)
        app.include_router(responders.router)
        app.include_router(evidence.router)
        app.include_router(analytics.router)
        app.include_router(zones.router)
        app.include_router(stream.router)

        EVIDENCE_DIR = os.path.join(os.getcwd(), "data", "evidence")
        os.makedirs(EVIDENCE_DIR, exist_ok=True)
        app.mount("/data/evidence", StaticFiles(directory=EVIDENCE_DIR), name="evidence")
        
        FRONTEND_DIR = os.path.join(os.getcwd(), "../../frontend")
        if os.path.exists(FRONTEND_DIR):
            app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

        @app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await manager.connect(websocket)
            try:
                while True:
                    data = await websocket.receive_text()
            except WebSocketDisconnect:
                manager.disconnect(websocket)

        @app.post("/api/ai/incident")
        async def ai_webhook(incident_data: dict):
            # This would normally inject a DB session
            from backend.src.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                return await create_incident(db, incident_data)

        @app.exception_handler(404)
        async def custom_404_handler(request: Request, exc):
            if request.url.path.startswith("/api"):
                return {"detail": "Not Found"}
            index_path = os.path.join(FRONTEND_DIR, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return {"detail": "Frontend not found"}

        if __name__ == "__main__":
            import uvicorn
            uvicorn.run("backend.src.main:app", host="0.0.0.0", port=8000, reload=True)
    """),

    "database/seed/seed_data.py": textwrap.dedent("""\
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
    """)
}

def main():
    for rel_path, content in FILES.items():
        full_path = os.path.join(BASE_DIR, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created {full_path}")

if __name__ == "__main__":
    main()
