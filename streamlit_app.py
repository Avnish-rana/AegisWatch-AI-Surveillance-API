"""
AegisWatch — AI Smart Surveillance & Incident Response System
Streamlit Cloud & Local Deployment Application
"""
import os
import time
import math
import uuid
import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

import streamlit as st
import numpy as np
import pandas as pd
from PIL import Image
import cv2

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AegisWatch — AI Surveillance",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

ROOT_DIR = Path(__file__).parent.resolve()
DB_PATH = ROOT_DIR / "surveillance.db"
MODEL_PATH = ROOT_DIR / "yolov8n.pt"
DEMO_VIDEOS_DIR = ROOT_DIR / "data" / "videos" / "demo"
EVIDENCE_DIR = ROOT_DIR / "data" / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# ── Custom CSS for Cyber-Surveillance Theme ──────────────────────────────────
st.markdown("""
<style>
    /* Global styles */
    .stApp {
        background: radial-gradient(circle at 15% 15%, #0f172a 0%, #080d1a 100%);
        color: #e2e8f0;
    }
    
    /* Headers & Branding */
    .aegis-header {
        background: linear-gradient(90deg, rgba(14, 165, 233, 0.15) 0%, rgba(99, 102, 241, 0.05) 100%);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .aegis-title {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .aegis-subtitle {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-top: 4px;
    }

    /* Metric Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
        backdrop-filter: blur(8px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.4);
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-lbl {
        font-size: 0.82rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }

    /* Threat Badges */
    .badge-critical {
        background-color: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.4);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    .badge-high {
        background-color: rgba(249, 115, 22, 0.2);
        color: #fb923c;
        border: 1px solid rgba(249, 115, 22, 0.4);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    .badge-medium {
        background-color: rgba(234, 179, 8, 0.2);
        color: #facc15;
        border: 1px solid rgba(234, 179, 8, 0.4);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    .badge-low {
        background-color: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.4);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    .badge-resolved {
        background-color: rgba(34, 197, 94, 0.2);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.4);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.78rem;
    }

    /* Live Feed Container */
    .stream-box {
        border: 2px solid #38bdf8;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.25);
    }
</style>
""", unsafe_allow_html=True)


# ── Database Layer ────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_database_if_needed():
    """Ensure database tables and base seed data exist for Streamlit Cloud."""
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS cameras (
        id TEXT PRIMARY KEY,
        camera_id TEXT UNIQUE,
        name TEXT,
        description TEXT,
        source_type TEXT DEFAULT 'webcam',
        source_url TEXT,
        location_name TEXT,
        latitude REAL,
        longitude REAL,
        status TEXT DEFAULT 'online',
        is_enabled INTEGER DEFAULT 1,
        config_json TEXT DEFAULT '{}',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS incidents (
        id TEXT PRIMARY KEY,
        incident_id TEXT UNIQUE,
        incident_type TEXT,
        severity TEXT,
        risk_score REAL,
        ai_confidence REAL,
        camera_id TEXT,
        location_name TEXT,
        latitude REAL,
        longitude REAL,
        description TEXT,
        involved_track_ids TEXT,
        status TEXT DEFAULT 'NEW',
        assigned_responder_id TEXT,
        resolution_notes TEXT,
        source_type TEXT DEFAULT 'live',
        video_name TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT,
        resolved_at TEXT
    );

    CREATE TABLE IF NOT EXISTS responders (
        id TEXT PRIMARY KEY,
        responder_id TEXT UNIQUE,
        name TEXT,
        station TEXT,
        phone TEXT,
        email TEXT,
        latitude REAL,
        longitude REAL,
        availability TEXT DEFAULT 'AVAILABLE',
        role TEXT DEFAULT 'GUARD',
        status TEXT DEFAULT 'ACTIVE',
        user_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT
    );
    """)
    conn.commit()

    # Seed initial cameras if empty
    res = c.execute("SELECT COUNT(*) FROM cameras").fetchone()[0]
    if res == 0:
        c.executemany("""
        INSERT INTO cameras (id, camera_id, name, location_name, latitude, longitude, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (str(uuid.uuid4()), "CAM-001", "Main Campus Gate", "Gate 1 - North", 28.6139, 77.2090, "online"),
            (str(uuid.uuid4()), "CAM-002", "Faculty Parking Lot", "Parking B3", 28.6145, 77.2098, "online"),
            (str(uuid.uuid4()), "CAM-003", "Central Library Corridor", "Library Fl 1", 28.6132, 77.2082, "online"),
            (str(uuid.uuid4()), "CAM-004", "Science Block Quadrangle", "Science Courtyard", 28.6151, 77.2105, "online"),
            (str(uuid.uuid4()), "CAM-005", "Server Room Perimeter", "Block A Secure Wing", 28.6128, 77.2075, "online"),
        ])
        conn.commit()

    # Seed initial responders if empty
    resp_cnt = c.execute("SELECT COUNT(*) FROM responders").fetchone()[0]
    if resp_cnt == 0:
        c.executemany("""
        INSERT INTO responders (id, responder_id, name, station, phone, latitude, longitude, availability, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (str(uuid.uuid4()), "RESP-001", "Patrol Alpha (Officer Rajesh)", "Main Gate Post", "+91 98765 43210", 28.6140, 77.2091, "AVAILABLE", "PATROL"),
            (str(uuid.uuid4()), "RESP-002", "Quick Response Unit 1", "Central Security Hub", "+91 98765 43211", 28.6135, 77.2085, "AVAILABLE", "QRT"),
            (str(uuid.uuid4()), "RESP-003", "Patrol Beta (Guard Vikram)", "East Perimeter", "+91 98765 43212", 28.6150, 77.2100, "ON_DUTY", "PATROL"),
            (str(uuid.uuid4()), "RESP-004", "Medical Response Team", "Campus Health Center", "+91 98765 43213", 28.6125, 77.2070, "AVAILABLE", "MEDICAL"),
        ])
        conn.commit()

    # Seed sample incidents if empty
    inc_cnt = c.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    if inc_cnt == 0:
        c.executemany("""
        INSERT INTO incidents (id, incident_id, incident_type, severity, risk_score, ai_confidence, camera_id, location_name, latitude, longitude, description, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (str(uuid.uuid4()), f"INC-{int(time.time())-4000}", "Unattended Baggage", "MEDIUM", 65.0, 0.88, "CAM-003", "Central Library Corridor", 28.6132, 77.2082, "Backpack left unattended for > 3 minutes near Study Bay 4.", "NEW"),
            (str(uuid.uuid4()), f"INC-{int(time.time())-2000}", "Loitering / Suspicious Lingering", "LOW", 45.0, 0.92, "CAM-002", "Faculty Parking Lot", 28.6145, 77.2098, "Individual loitering between vehicles without entry authorization.", "VERIFIED"),
            (str(uuid.uuid4()), f"INC-{int(time.time())-800}", "Perimeter Intrusion", "HIGH", 85.0, 0.94, "CAM-005", "Server Room Perimeter", 28.6128, 77.2075, "Movement detected in restricted zone outside permitted operational hours.", "ASSIGNED"),
        ])
        conn.commit()

    conn.close()

init_database_if_needed()


# ── AI Model Loader (YOLOv8) ──────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading YOLOv8n Computer Vision Engine...")
def load_ai_model():
    """Load YOLOv8 model instance cached for Streamlit."""
    try:
        from ultralytics import YOLO
        if MODEL_PATH.exists():
            model = YOLO(str(MODEL_PATH))
        else:
            model = YOLO("yolov8n.pt")  # Ultralytics will auto-fetch if missing
        return model, "YOLOv8n (Ultralytics)", "ok"
    except Exception as e:
        return None, "Unavailable", str(e)

model, model_name, model_status = load_ai_model()

# Class mappings & cyber color palette
CCTV_CLASSES = {
    "person": (255, 240, 0),        # Cyan/Blue
    "bicycle": (0, 255, 255),       # Yellow
    "car": (0, 255, 255),           # Yellow
    "motorcycle": (0, 255, 255),
    "bus": (0, 200, 255),
    "truck": (0, 200, 255),
    "backpack": (255, 0, 255),      # Magenta
    "handbag": (255, 0, 255),
    "suitcase": (255, 0, 255),
    "knife": (0, 0, 255),           # Red (Weapon)
    "scissors": (0, 0, 255),
    "cell phone": (180, 180, 180),
    "laptop": (180, 180, 180)
}

def analyze_frame(
    frame_bgr: np.ndarray,
    conf_thresh: float = 0.35,
    selected_classes: list = None
) -> Tuple[np.ndarray, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Run YOLO inference and evaluate surveillance anomaly heuristics.
    Returns: (annotated_bgr_frame, detections_list, anomaly_alerts)
    """
    if model is None:
        return frame_bgr, [], [{"type": "Engine Error", "severity": "HIGH", "desc": "Model not loaded"}]

    results = model(frame_bgr, conf=conf_thresh, verbose=False)
    detections = []
    annotated = frame_bgr.copy()
    h, w = frame_bgr.shape[:2]

    persons = []
    baggage = []
    weapons = []

    if results and len(results) > 0 and results[0].boxes is not None:
        boxes = results[0].boxes
        for box in boxes:
            cls_id = int(box.cls[0])
            name = model.names.get(cls_id, str(cls_id))
            conf = float(box.conf[0])

            if selected_classes and name not in selected_classes:
                continue

            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            det = {
                "class": name,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
                "centroid": (cx, cy)
            }
            detections.append(det)

            # Categorize for anomaly reasoning
            if name == "person":
                persons.append(det)
            elif name in ("backpack", "handbag", "suitcase"):
                baggage.append(det)
            elif name in ("knife", "scissors"):
                weapons.append(det)

            # Draw sleek bounding box
            color = CCTV_CLASSES.get(name, (0, 255, 0))
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Header tag
            label = f"{name.upper()} {int(conf * 100)}%"
            t_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.rectangle(annotated, (x1, y1 - 20), (x1 + t_size[0] + 8, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 4, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (10, 10, 20), 1, cv2.LINE_AA)

    # ── Surveillance Anomaly Heuristics ───────────────────────────────────────
    anomalies = []

    # 1. Weapon Detection
    if len(weapons) > 0:
        anomalies.append({
            "type": "Weapon / Dangerous Item Detected",
            "severity": "CRITICAL",
            "score": 98.0,
            "desc": f"Identified {len(weapons)} restricted weapon/edged item(s) in CCTV field."
        })

    # 2. Crowd Surge / Congestion
    if len(persons) >= 4:
        anomalies.append({
            "type": "High Density / Crowd Congestion",
            "severity": "HIGH",
            "score": 82.0,
            "desc": f"Surge of {len(persons)} persons detected in monitoring zone."
        })

    # 3. Abandoned / Unattended Object Check
    for bag in baggage:
        bx, by = bag["centroid"]
        min_dist = float("inf")
        for p in persons:
            px, py = p["centroid"]
            dist = math.hypot(bx - px, by - py)
            if dist < min_dist:
                min_dist = dist
        # If nearest person is far away (> 160 px), flag as unattended
        if min_dist > 160:
            anomalies.append({
                "type": "Unattended / Abandoned Baggage",
                "severity": "MEDIUM",
                "score": 68.0,
                "desc": f"Unattended {bag['class']} detected with no person in immediate proximity (distance {int(min_dist)}px)."
            })

    # HUD Overlay (Timestamp + Aegis Edge Watermark)
    ts_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    cv2.putText(annotated, f"AEGIS-WATCH | {ts_str}", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (56, 189, 248), 2, cv2.LINE_AA)

    return annotated, detections, anomalies


# ── Distance Calculation Helper (Haversine) ───────────────────────────────────
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two lat/lon coordinates."""
    R = 6371000  # meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ── Navigation & Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ AegisWatch")
    st.markdown("*Autonomous CCTV Surveillance & Incident Response*")
    st.divider()

    nav_selection = st.radio(
        "Navigation",
        [
            "📡 Live AI Camera",
            "🎬 Video Surveillance Analyzer",
            "🖼️ Image Threat Scanner",
            "🚨 Incident Command Center",
            "🗺️ CCTV Camera Network",
            "👮 Responder Dispatch",
            "📊 Analytics & Insights",
            "⚙️ Deployment & System Diagnostics"
        ],
        index=0
    )

    st.divider()
    st.markdown("### 🖥️ Edge AI Status")
    if model_status == "ok":
        st.success(f"● **AI Engine:** {model_name}")
    else:
        st.warning(f"▲ **AI Status:** {model_status}")

    st.caption("Deployment: Streamlit Cloud Ready")
    st.caption("Framework: YOLOv8 + OpenCV + SQLite")


# ── Header Banner ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="aegis-header">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h1 class="aegis-title">🛡️ AegisWatch — AI Smart Surveillance</h1>
            <p class="aegis-subtitle">Real-time Anomaly Detection, Behaviour Heuristics & Emergency Dispatch Command</p>
        </div>
        <div style="text-align:right;">
            <span style="background:rgba(34,197,94,0.15); border:1px solid rgba(34,197,94,0.4); color:#4ade80; padding:6px 12px; border-radius:8px; font-weight:600; font-size:0.85rem;">
                ● SYSTEM OPERATIONAL
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. LIVE AI CAMERA
# ═══════════════════════════════════════════════════════════════════════════════
if nav_selection == "📡 Live AI Camera":
    st.subheader("📡 Live AI Camera Surveillance")
    st.markdown("Capture a frame from your webcam or connected security stream to perform real-time AI anomaly detection.")

    col_cam, col_ctrl = st.columns([2, 1])

    with col_ctrl:
        st.markdown("#### ⚙️ Camera Controls")
        assigned_camera = st.selectbox("Assign to Camera Feed", ["CAM-001 (Main Gate)", "CAM-002 (Parking)", "CAM-003 (Library)"])
        cam_code = assigned_camera.split()[0]
        conf_slider = st.slider("AI Confidence Threshold", 0.15, 0.90, 0.35, 0.05)
        
        st.markdown("#### 🎯 Active Surveillance Classes")
        filter_person = st.checkbox("Persons / Pedestrians", value=True)
        filter_vehicles = st.checkbox("Vehicles (Cars/Bikes/Buses)", value=True)
        filter_bags = st.checkbox("Baggage (Backpacks/Suitcases)", value=True)
        filter_weapons = st.checkbox("Weapons (Knives/Blades)", value=True)

        selected_cls = []
        if filter_person: selected_cls.append("person")
        if filter_vehicles: selected_cls.extend(["car", "motorcycle", "bus", "truck", "bicycle"])
        if filter_bags: selected_cls.extend(["backpack", "handbag", "suitcase"])
        if filter_weapons: selected_cls.extend(["knife", "scissors"])

    with col_cam:
        cam_snapshot = st.camera_input("Capture Security Frame")

    if cam_snapshot is not None:
        bytes_data = cam_snapshot.getvalue()
        cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

        annotated, detections, alerts = analyze_frame(cv_img, conf_thresh=conf_slider, selected_classes=selected_cls)
        annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)

        st.markdown("### 🔍 AI Analysis Output")
        st.image(annotated_rgb, caption="Annotated Surveillance Feed", use_container_width=True)

        # Alerts Bar
        if alerts:
            for alt in alerts:
                sev = alt["severity"]
                cls_badge = "badge-critical" if sev == "CRITICAL" else ("badge-high" if sev == "HIGH" else "badge-medium")
                st.markdown(f"""
                <div style="background:rgba(239, 68, 68, 0.1); border-left:4px solid #ef4444; padding:12px 16px; border-radius:6px; margin-bottom:10px;">
                    <span class="{cls_badge}">{sev}</span>
                    <strong style="margin-left:8px; color:#f87171;">{alt['type']}</strong>
                    <p style="margin:4px 0 0 0; color:#cbd5e1; font-size:0.9rem;">{alt['desc']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No suspicious anomalies or prohibited behavior detected in frame.")

        # Detections Breakdown
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        c_counts = {}
        for d in detections:
            c_counts[d["class"]] = c_counts.get(d["class"], 0) + 1

        with col_m1:
            st.metric("Total Objects", len(detections))
        with col_m2:
            st.metric("Persons", c_counts.get("person", 0))
        with col_m3:
            st.metric("Vehicles", sum(c_counts.get(k, 0) for k in ["car", "motorcycle", "bus", "truck", "bicycle"]))
        with col_m4:
            st.metric("Baggage Items", sum(c_counts.get(k, 0) for k in ["backpack", "handbag", "suitcase"]))

        # Action: Quick Log Incident
        st.divider()
        col_act1, col_act2 = st.columns([1, 2])
        with col_act1:
            if st.button("🚨 Log Frame as Incident", type="primary"):
                inc_id = f"INC-{int(time.time())}"
                primary_alt = alerts[0] if alerts else {"type": "Manual Operator Flag", "severity": "MEDIUM", "score": 50.0, "desc": "Logged by surveillance operator"}
                conn = get_db()
                conn.execute("""
                INSERT INTO incidents (id, incident_id, incident_type, severity, risk_score, ai_confidence, camera_id, location_name, latitude, longitude, description, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()), inc_id, primary_alt["type"], primary_alt["severity"],
                    primary_alt.get("score", 60.0), conf_slider, cam_code,
                    f"Assigned to {cam_code}", 28.6139, 77.2090, primary_alt["desc"], "NEW"
                ))
                conn.commit()
                conn.close()
                st.success(f"Incident {inc_id} recorded in Incident Command Database!")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. VIDEO SURVEILLANCE ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════
elif nav_selection == "🎬 Video Surveillance Analyzer":
    st.subheader("🎬 Recorded Video Surveillance Analyzer")
    st.markdown("Upload CCTV video files or select from pre-loaded demonstration test footage to execute batch AI surveillance processing.")

    col_src, col_opts = st.columns([2, 1])

    demo_files = list(DEMO_VIDEOS_DIR.glob("*.mp4")) if DEMO_VIDEOS_DIR.exists() else []
    demo_file_names = [f.name for f in demo_files]

    with col_src:
        source_mode = st.radio("Video Source", ["Use Pre-loaded Demo Video", "Upload Video File (MP4/AVI/MOV)"], horizontal=True)
        video_path = None

        if source_mode == "Use Pre-loaded Demo Video":
            if demo_file_names:
                selected_demo = st.selectbox("Select Test Video", demo_file_names)
                video_path = str(DEMO_VIDEOS_DIR / selected_demo)
                st.info(f"📁 Selected: `{selected_demo}`")
            else:
                st.warning("No pre-generated demo videos found in data/videos/demo.")
        else:
            uploaded_video = st.file_uploader("Upload Video File", type=["mp4", "avi", "mov"])
            if uploaded_video:
                temp_path = ROOT_DIR / "data" / "uploads" / uploaded_video.name
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_video.read())
                video_path = str(temp_path)

    with col_opts:
        st.markdown("#### ⚙️ Processing Parameters")
        frame_skip = st.slider("Frame Skip Interval", 1, 10, 3, help="Process 1 out of every N frames for speed")
        v_conf = st.slider("Confidence", 0.20, 0.80, 0.35, 0.05)
        max_frames_to_process = st.number_input("Max Frames to Scan", 30, 600, 150, 30)

    if video_path and os.path.exists(video_path):
        st.video(video_path)

        if st.button("🚀 Run AI Video Surveillance Pipeline", type="primary"):
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

            st.markdown("#### ⚡ Live Frame Analysis Stream")
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            frame_placeholder = st.empty()

            frame_idx = 0
            processed_count = 0
            incident_log = []
            start_t = time.time()

            while cap.isOpened() and processed_count < max_frames_to_process:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_skip == 0:
                    ann, dets, anoms = analyze_frame(frame, conf_thresh=v_conf)
                    processed_count += 1

                    # Log any anomalies detected
                    if anoms:
                        for a in anoms:
                            incident_log.append({
                                "frame": frame_idx,
                                "timestamp": round(frame_idx / fps, 1),
                                "anomaly": a["type"],
                                "severity": a["severity"],
                                "desc": a["desc"]
                            })

                    # Update UI preview every few frames
                    if processed_count % 2 == 0 or anoms:
                        preview_rgb = cv2.cvtColor(ann, cv2.COLOR_BGR2RGB)
                        frame_placeholder.image(preview_rgb, caption=f"Frame {frame_idx} | Detected: {len(dets)} objects", use_container_width=True)

                    pct = min(1.0, processed_count / max_frames_to_process)
                    progress_bar.progress(pct)
                    status_text.text(f"Scanning frame {frame_idx}/{min(total_frames, max_frames_to_process)}... ({len(incident_log)} threat alerts)")

                frame_idx += 1

            cap.release()
            duration = round(time.time() - start_t, 2)
            calc_fps = round(processed_count / max(0.1, duration), 1)

            st.success(f"Processing Complete: Analyzed {processed_count} frames in {duration}s ({calc_fps} FPS)")

            # Results Summary
            st.markdown("### 📋 Video Surveillance Threat Log")
            if incident_log:
                df_log = pd.DataFrame(incident_log)
                st.dataframe(df_log, use_container_width=True)
            else:
                st.info("No security anomalies or threats detected throughout the scanned video segment.")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. IMAGE THREAT SCANNER
# ═══════════════════════════════════════════════════════════════════════════════
elif nav_selection == "🖼️ Image Threat Scanner":
    st.subheader("🖼️ High-Resolution CCTV Image Scanner")
    st.markdown("Upload static surveillance captures to perform high-fidelity object detection, threat categorization, and perimeter audits.")

    img_file = st.file_uploader("Upload Surveillance Image", type=["jpg", "jpeg", "png"])

    c_conf, c_classes = st.columns([1, 2])
    with c_conf:
        img_conf = st.slider("Confidence Threshold", 0.1, 0.9, 0.35, 0.05)
    with c_classes:
        filter_opts = st.multiselect(
            "Target Object Filters",
            ["person", "car", "motorcycle", "bus", "truck", "backpack", "handbag", "suitcase", "knife", "cell phone"],
            default=["person", "car", "backpack", "suitcase", "knife"]
        )

    if img_file:
        pil_img = Image.open(img_file)
        np_img = np.array(pil_img)
        # Convert RGB to BGR for OpenCV processing
        bgr_img = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)

        annotated_bgr, detections, alerts = analyze_frame(bgr_img, conf_thresh=img_conf, selected_classes=filter_opts)
        annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)

        col_orig, col_ann = st.columns(2)
        with col_orig:
            st.image(pil_img, caption="Original CCTV Frame", use_container_width=True)
        with col_ann:
            st.image(annotated_rgb, caption=f"AI Annotated ({len(detections)} Detections)", use_container_width=True)

        if alerts:
            st.markdown("#### 🚨 Detected Threats & Heuristics")
            for alt in alerts:
                sev = alt["severity"]
                cls_badge = "badge-critical" if sev == "CRITICAL" else "badge-high"
                st.markdown(f"<span class='{cls_badge}'>{sev}</span> <strong>{alt['type']}</strong> — {alt['desc']}", unsafe_allow_html=True)

        if detections:
            st.markdown("#### 📊 Detections Manifest")
            dets_table = [{
                "Class": d["class"].capitalize(),
                "Confidence": f"{int(d['confidence'] * 100)}%",
                "Centroid (X, Y)": f"({d['centroid'][0]}, {d['centroid'][1]})",
                "Bounding Box [x1, y1, x2, y2]": str(d["bbox"])
            } for d in detections]
            st.dataframe(pd.DataFrame(dets_table), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. INCIDENT COMMAND CENTER
# ═══════════════════════════════════════════════════════════════════════════════
elif nav_selection == "🚨 Incident Command Center":
    st.subheader("🚨 Incident Command Center & Live Database")
    st.markdown("Real-time lifecycle management for all automated AI alarms and security operator verifications.")

    conn = get_db()
    c = conn.cursor()

    # Filter Bar
    f_status, f_sev, f_search = st.columns([1, 1, 2])
    with f_status:
        stat_filter = st.selectbox("Status Filter", ["ALL", "NEW", "VERIFIED", "ASSIGNED", "RESPONDING", "RESOLVED"])
    with f_sev:
        sev_filter = st.selectbox("Severity Filter", ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
    with f_search:
        search_query = st.text_input("Search Incidents (Camera, Location, Type)", "")

    # Query
    query = "SELECT * FROM incidents WHERE 1=1"
    params = []
    if stat_filter != "ALL":
        query += " AND status = ?"
        params.append(stat_filter)
    if sev_filter != "ALL":
        query += " AND severity = ?"
        params.append(sev_filter)
    if search_query:
        query += " AND (incident_type LIKE ? OR location_name LIKE ? OR camera_id LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term])

    query += " ORDER BY created_at DESC"
    incidents = c.execute(query, params).fetchall()

    st.markdown(f"**Found {len(incidents)} Incidents**")

    for inc in incidents:
        sev = inc["severity"]
        status = inc["status"]
        badge_cls = "badge-critical" if sev == "CRITICAL" else ("badge-high" if sev == "HIGH" else "badge-medium")
        stat_badge = "badge-resolved" if status == "RESOLVED" else "badge-low"

        with st.expander(f"🚨 {inc['incident_id']} — {inc['incident_type']} ({inc['location_name']})", expanded=(status == "NEW")):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(f"""
                <div style="margin-bottom:8px;">
                    <span class="{badge_cls}">{sev}</span>
                    <span class="{stat_badge}" style="margin-left:6px;">{status}</span>
                    <span style="color:#94a3b8; font-size:0.85rem; margin-left:12px;">🕒 {inc['created_at']}</span>
                </div>
                """, unsafe_allow_html=True)
                st.write(f"**Description:** {inc['description']}")
                st.write(f"**Camera Source:** `{inc['camera_id']}` | **Coordinates:** `{inc['latitude']}, {inc['longitude']}`")
                st.write(f"**AI Risk Score:** `{inc['risk_score']}` | **Confidence:** `{int((inc['ai_confidence'] or 0.8) * 100)}%`")
                if inc["assigned_responder_id"]:
                    st.write(f"**Assigned Responder:** `{inc['assigned_responder_id']}`")

            with c2:
                st.markdown("#### ⚡ Incident Actions")
                new_status = st.selectbox(
                    "Update Status",
                    ["NEW", "VERIFIED", "ASSIGNED", "RESPONDING", "RESOLVED"],
                    index=["NEW", "VERIFIED", "ASSIGNED", "RESPONDING", "RESOLVED"].index(status),
                    key=f"stat_{inc['id']}"
                )
                if st.button("Apply Status Change", key=f"btn_{inc['id']}"):
                    c.execute("UPDATE incidents SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, inc["id"]))
                    conn.commit()
                    st.success(f"Status updated to {new_status}!")
                    st.rerun()

    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CCTV CAMERA NETWORK
# ═══════════════════════════════════════════════════════════════════════════════
elif nav_selection == "🗺️ CCTV Camera Network":
    st.subheader("🗺️ Smart CCTV Camera Network Topology")
    st.markdown("Geographic distribution, sensor telemetry, and coverage zones across campus perimeter.")

    conn = get_db()
    c = conn.cursor()
    cams = c.execute("SELECT * FROM cameras").fetchall()
    conn.close()

    cam_data = []
    for cam in cams:
        cam_data.append({
            "Camera ID": cam["camera_id"],
            "Name": cam["name"],
            "Location": cam["location_name"],
            "Latitude": cam["latitude"],
            "Longitude": cam["longitude"],
            "Status": cam["status"].upper(),
            "Stream": cam["source_type"]
        })
    df_cams = pd.DataFrame(cam_data)

    # Map Visual
    st.markdown("#### 📍 Real-Time Sensor Map")
    map_df = df_cams[["Latitude", "Longitude"]].rename(columns={"Latitude": "lat", "Longitude": "lon"})
    st.map(map_df, zoom=15)

    st.markdown("#### 📋 Camera Feeds & Hardware Registry")
    st.dataframe(df_cams, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. RESPONDER DISPATCH
# ═══════════════════════════════════════════════════════════════════════════════
elif nav_selection == "👮 Responder Dispatch":
    st.subheader("👮 Emergency Responder Dispatch Matrix")
    st.markdown("Compute the nearest security patrols, quick response teams (QRT), and medical units using Haversine edge routing.")

    conn = get_db()
    c = conn.cursor()
    responders = c.execute("SELECT * FROM responders").fetchall()
    incidents = c.execute("SELECT * FROM incidents WHERE status != 'RESOLVED'").fetchall()

    col_target, col_resp = st.columns([1, 1])

    with col_target:
        st.markdown("#### 1. Select Incident Target")
        if incidents:
            inc_opts = {f"{i['incident_id']} - {i['incident_type']} ({i['location_name']})": i for i in incidents}
            chosen_label = st.selectbox("Active Incidents", list(inc_opts.keys()))
            chosen_inc = inc_opts[chosen_label]

            t_lat = chosen_inc["latitude"]
            t_lon = chosen_inc["longitude"]
            st.info(f"Target Coordinates: `{t_lat}, {t_lon}` ({chosen_inc['location_name']})")
        else:
            st.info("No unresolved incidents. Test with manual coordinates:")
            t_lat = st.number_input("Target Latitude", value=28.6139, format="%.5f")
            t_lon = st.number_input("Target Longitude", value=77.2090, format="%.5f")
            chosen_inc = None

    with col_resp:
        st.markdown("#### 2. Nearest Responders (Ranked by Proximity)")
        calc_list = []
        for r in responders:
            dist_m = haversine(t_lat, t_lon, r["latitude"], r["longitude"])
            eta_mins = round(dist_m / (4.5 * 1000 / 60), 1) # ~4.5 km/h patrol walking speed
            calc_list.append({
                "ID": r["responder_id"],
                "Name": r["name"],
                "Station": r["station"],
                "Role": r["role"],
                "Distance (m)": int(dist_m),
                "Estimated ETA": f"{eta_mins} mins",
                "Availability": r["availability"],
                "_raw_id": r["id"]
            })

        calc_list.sort(key=lambda x: x["Distance (m)"])
        st.dataframe(pd.DataFrame(calc_list).drop(columns=["_raw_id"]), use_container_width=True)

        if chosen_inc and calc_list:
            top_resp = calc_list[0]
            if st.button(f"🚨 Dispatch {top_resp['Name']} to {chosen_inc['incident_id']}", type="primary"):
                c.execute("""
                UPDATE incidents SET status = 'ASSIGNED', assigned_responder_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """, (top_resp["ID"], chosen_inc["id"]))
                conn.commit()
                st.success(f"Dispatched {top_resp['Name']} to {chosen_inc['incident_id']}!")
                st.rerun()

    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ANALYTICS & INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════════
elif nav_selection == "📊 Analytics & Insights":
    st.subheader("📊 Surveillance Operations & Threat Analytics")
    st.markdown("Executive metrics, incident distributions, and situational threat intelligence.")

    conn = get_db()
    c = conn.cursor()
    total_inc = c.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    crit_inc = c.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'CRITICAL'").fetchone()[0]
    high_inc = c.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'HIGH'").fetchone()[0]
    res_inc = c.execute("SELECT COUNT(*) FROM incidents WHERE status = 'RESOLVED'").fetchone()[0]
    cams_cnt = c.execute("SELECT COUNT(*) FROM cameras").fetchone()[0]

    # Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f"""<div class="metric-card"><div class="metric-val">{total_inc}</div><div class="metric-lbl">Total Incidents</div></div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="metric-card"><div class="metric-val" style="color:#ef4444;">{crit_inc}</div><div class="metric-lbl">Critical Alarms</div></div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""<div class="metric-card"><div class="metric-val" style="color:#f59e0b;">{high_inc}</div><div class="metric-lbl">High Risk</div></div>""", unsafe_allow_html=True)
    with m4:
        st.markdown(f"""<div class="metric-card"><div class="metric-val" style="color:#10b981;">{res_inc}</div><div class="metric-lbl">Resolved Cases</div></div>""", unsafe_allow_html=True)
    with m5:
        st.markdown(f"""<div class="metric-card"><div class="metric-val" style="color:#38bdf8;">{cams_cnt}</div><div class="metric-lbl">Active Cameras</div></div>""", unsafe_allow_html=True)

    st.markdown("---")

    col_ch1, col_ch2 = st.columns(2)

    with col_ch1:
        st.markdown("#### 🚨 Incidents by Severity")
        sev_counts = c.execute("SELECT severity, COUNT(*) as cnt FROM incidents GROUP BY severity").fetchall()
        if sev_counts:
            df_sev = pd.DataFrame([dict(r) for r in sev_counts])
            st.bar_chart(df_sev.set_index("severity")["cnt"])

    with col_ch2:
        st.markdown("#### 📹 Incidents by Camera Feed")
        cam_counts = c.execute("SELECT camera_id, COUNT(*) as cnt FROM incidents GROUP BY camera_id").fetchall()
        if cam_counts:
            df_cam = pd.DataFrame([dict(r) for r in cam_counts])
            st.bar_chart(df_cam.set_index("camera_id")["cnt"])

    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 8. DEPLOYMENT & SYSTEM DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════
elif nav_selection == "⚙️ Deployment & System Diagnostics":
    st.subheader("⚙️ Deployment Guide & System Diagnostics")

    tab_cloud, tab_diag = st.tabs(["🚀 Deploy to Streamlit Community Cloud", "💻 Local Diagnostics & Hardware"])

    with tab_cloud:
        st.markdown("""
        ### How to Deploy this Project on Streamlit Community Cloud:
        
        Streamlit Community Cloud hosts your application directly from your GitHub repository for free:
        
        1. **Push your code to GitHub**:
           ```bash
           git add .
           git commit -m "Deploy AegisWatch on Streamlit Cloud"
           git push origin main
           ```
        
        2. **Log into Streamlit Community Cloud**:
           - Go to [share.streamlit.io](https://share.streamlit.io) and sign in with your GitHub account.
        
        3. **Deploy the App**:
           - Click **New App**
           - Select your GitHub repository: `Rishichamp/AegisEdge-SmartSurveillance` (or your current repo)
           - Set **Branch**: `main`
           - Set **Main file path**: `streamlit_app.py`
           - Click **Deploy!**
        
        4. **Automatic Dependency Resolution**:
           - Streamlit Cloud will read `requirements.txt` (which contains `streamlit`, `pandas`, `ultralytics`, `torch`, `opencv-python`, etc.).
           - Streamlit Cloud will read `packages.txt` (`libgl1`, `libglib2.0-0`) for headless OpenCV graphic libraries.
           - `yolov8n.pt` will automatically load from your repository!
        """)

    with tab_diag:
        import sys, platform
        try:
            import torch
            torch_dev = "CUDA" if torch.cuda.is_available() else "CPU"
            torch_ver = torch.__version__
        except Exception:
            torch_dev = "Unavailable"
            torch_ver = "Not installed"

        diag_data = {
            "Component": [
                "Streamlit Version",
                "Python Runtime",
                "Operating System",
                "AI Model",
                "Inference Engine",
                "PyTorch Device",
                "PyTorch Version",
                "Database Engine",
                "Database Path"
            ],
            "Details": [
                st.__version__,
                sys.version.split()[0],
                platform.platform(),
                model_name,
                "Ultralytics YOLOv8",
                torch_dev,
                torch_ver,
                "SQLite (Embedded Self-Seeding)",
                str(DB_PATH)
            ]
        }
        st.table(pd.DataFrame(diag_data))
