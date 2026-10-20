import argparse
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from ai_engine.pipeline_extended import ExtendedSurveillancePipeline
except ModuleNotFoundError:
    import importlib.util
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("pipeline_extended", os.path.join(base_dir, "ai-engine", "pipeline_extended.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ExtendedSurveillancePipeline = mod.ExtendedSurveillancePipeline

def main():
    parser = argparse.ArgumentParser(description="Run AI Surveillance Demo")
    parser.add_argument("--camera", default="data/videos/demo/normal.mp4", help="Camera index or video file")
    parser.add_argument("--config", default="config/default_config.yaml", help="Path to config file")
    parser.add_argument("--camera-id", default="CAM-DEMO", help="Camera ID")
    args = parser.parse_argument()
    
    pipeline = ExtendedSurveillancePipeline(
        config_path=args.config,
        camera_id=args.camera_id,
        camera_location="Demo Area"
    )
    
    if hasattr(pipeline, "config") and hasattr(pipeline.config, "video_source"):
        pipeline.config.video_source = args.camera
    
    print(f"Starting pipeline with camera {args.camera_id} on {args.camera}...")
    try:
        pipeline.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping pipeline...")
        pipeline.stop()

if __name__ == "__main__":
    main()
