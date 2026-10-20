import os
import cv2
import numpy as np

def generate_video(filename, scene_type):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    width, height = 640, 480
    fps = 15
    duration = 30
    frames = fps * duration
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    
    # State variables for animation
    p1_x, p1_y = 100, 240
    p2_x, p2_y = 500, 240
    obj_x, obj_y = 320, 300
    obj_visible = True
    
    for i in range(frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        if scene_type == "normal":
            p1_x = (100 + i * 2) % width
            p2_x = (500 - i * 2) % width
            cv2.rectangle(frame, (p1_x, p1_y-20), (p1_x+20, p1_y+40), (0, 255, 0), -1)
            cv2.rectangle(frame, (p2_x, p2_y-20), (p2_x+20, p2_y+40), (255, 0, 0), -1)
            
        elif scene_type == "theft":
            p1_x = 100 + i * 3
            if p1_x > 300 and p1_x < 340:
                obj_visible = False # picked up
            if obj_visible:
                cv2.rectangle(frame, (obj_x, obj_y), (obj_x+30, obj_y+30), (0, 255, 255), -1)
            cv2.rectangle(frame, (p1_x, p1_y-20), (p1_x+20, p1_y+40), (0, 255, 0), -1)
            
        elif scene_type == "fight":
            p1_x = 300 + int(20 * np.sin(i * 0.5))
            p2_x = 340 + int(20 * np.cos(i * 0.5))
            cv2.rectangle(frame, (p1_x, p1_y-20), (p1_x+20, p1_y+40), (0, 0, 255), -1)
            cv2.rectangle(frame, (p2_x, p2_y-20), (p2_x+20, p2_y+40), (255, 0, 255), -1)
            
        elif scene_type == "intrusion":
            # Draw zone
            cv2.rectangle(frame, (400, 100), (600, 400), (0, 0, 100), 2)
            p1_x = 100 + i * 2
            cv2.rectangle(frame, (p1_x, p1_y-20), (p1_x+20, p1_y+40), (0, 255, 0), -1)
            
        elif scene_type == "abandoned":
            p1_x = 100 + i * 2
            if p1_x == 300:
                obj_x, obj_y = p1_x, p1_y + 20
                obj_visible = True
            elif p1_x < 300:
                obj_visible = False
            
            if obj_visible:
                cv2.rectangle(frame, (obj_x, obj_y), (obj_x+30, obj_y+30), (0, 255, 255), -1)
            cv2.rectangle(frame, (p1_x, p1_y-20), (p1_x+20, p1_y+40), (0, 255, 0), -1)
            
        cv2.putText(frame, f"Scene: {scene_type.upper()}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        out.write(frame)
        
    out.release()
    print(f"Generated {filename}")

if __name__ == "__main__":
    base_dir = "data/videos/demo"
    scenes = ["normal", "theft", "fight", "intrusion", "abandoned"]
    for scene in scenes:
        generate_video(os.path.join(base_dir, f"{scene}.mp4"), scene)
