import os
from PIL import Image

base_dir = os.path.dirname(os.path.abspath(__file__))
frames_dir = os.path.join(base_dir, "run", "frames", "idle")
if os.path.exists(frames_dir):
    files = sorted(os.listdir(frames_dir))
    for f in files:
        if f.endswith((".png", ".webp")):
            img = Image.open(os.path.join(frames_dir, f))
            bbox = img.getbbox()
            print(f"{f}: bbox={bbox}, size={img.size}")
else:
    print("idle frames directory not found")
