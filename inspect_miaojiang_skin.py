import os
from PIL import Image

base_dir = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base_dir, "run", "decoded", "miaojiang_skin_atlas.png")
if not os.path.exists(path):
    print("Miaojiang skin file not found!")
    exit(1)
    
img = Image.open(path)
print(f"Miaojiang skin atlas: width={img.width}, height={img.height}, mode={img.mode}")
