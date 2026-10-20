#!/usr/bin/env python3
"""
AegisWatch — Quick Start Script
Automates: dependency install → seed → generate videos → start backend
Run: python start.py
"""
import subprocess
import sys
import os
import time
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

def run(cmd, cwd=None, check=True, capture=False):
    """Run a shell command."""
    print(f"\n  ▶ {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd or ROOT,
        capture_output=capture, text=True
    )
    if check and result.returncode != 0:
        print(f"  ✗ Command failed: {cmd}")
        if capture:
            print(result.stderr)
        sys.exit(result.returncode)
    return result

def check_python():
    v = sys.version_info
    if v.major < 3 or v.minor < 9:
        print(f"✗ Python 3.9+ required. You have {v.major}.{v.minor}")
        sys.exit(1)
    print(f"  ✓ Python {v.major}.{v.minor}.{v.micro}")

def pip_install():
    print("\n📦 Installing dependencies...")
    run(f"{sys.executable} -m pip install -r requirements.txt --quiet")
    print("  ✓ Dependencies installed")

def seed_database():
    print("\n🗄️  Seeding database...")
    result = run(
        f"{sys.executable} database/seed/seed_data.py",
        check=False
    )
    if result.returncode == 0:
        print("  ✓ Database seeded (default users/cameras/responders created)")
    else:
        print("  ⚠ Seed may have already run or encountered an error (continuing...)")

def generate_demo_videos():
    print("\n🎬 Generating demo videos...")
    demo_dir = ROOT / "data" / "videos" / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    
    result = run(f"{sys.executable} scripts/generate_demo_videos.py", check=False)
    if result.returncode == 0:
        print("  ✓ Demo videos generated")
    else:
        print("  ⚠ Video generation failed (will use live webcam or RTSP sources)")

def create_env_file():
    env_path = ROOT / ".env"
    if not env_path.exists():
        env_path.write_text(
            "DATABASE_URL=sqlite+aiosqlite:///./surveillance.db\n"
            "SECRET_KEY=aegiswatch-dev-secret-key-change-in-production\n"
            "DEBUG=true\n"
        )
        print("  ✓ .env file created")
    else:
        print("  ✓ .env file already exists")

def start_server():
    print("\n🚀 Starting AegisWatch backend server...")
    print("  URL: http://localhost:8000")
    print("  Dashboard: http://localhost:8000/frontend/index.html")
    print("  API Docs: http://localhost:8000/docs")
    print("\n  Press Ctrl+C to stop\n")
    print("─" * 60)
    os.execv(
        sys.executable,
        [sys.executable, "-m", "uvicorn", "backend.src.main:app",
         "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "backend"]
    )

def main():
    print("=" * 60)
    print("  🛡️  AegisWatch — AI Surveillance System")
    print("  AI-Powered Smart Public Surveillance & Incident Response")
    print("=" * 60)

    print("\n🔍 Pre-flight checks...")
    check_python()

    print("\n📋 Step 1/5: Environment setup")
    create_env_file()

    print("\n📦 Step 2/5: Installing dependencies...")
    pip_install()

    print("\n🗄️  Step 3/5: Database setup")
    seed_database()

    print("\n🎬 Step 4/5: Demo content")
    generate_demo_videos()

    print("\n🚀 Step 5/5: Launching server")
    start_server()

if __name__ == '__main__':
    main()
