import os
from PIL import Image

base_dir = os.path.dirname(os.path.abspath(__file__))
frame_dir = os.path.join(base_dir, "run", "frames", "idle_test")

for f in sorted(os.listdir(frame_dir)):
    if f.endswith(".png"):
        path = os.path.join(frame_dir, f)
        img = Image.open(path)
        bbox = img.getbbox()
        print(f"Frame: {f}, Size: {img.width}x{img.height}, BBox: {bbox}")
