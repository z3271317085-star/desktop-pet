import os
import math
from PIL import Image

def color_dist(c1, c2):
    return math.sqrt(sum((a - b)**2 for a, b in zip(c1, c2)))

def analyze_components(image_path, chroma_key=(0, 255, 0), threshold=96.0):
    img = Image.open(image_path).convert("RGB")
    width, height = img.size
    
    # Create mask of non-green pixels
    mask = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            r, g, b = img.getpixel((x, y))
            if color_dist((r, g, b), chroma_key) > threshold:
                mask[y * width + x] = 1
                
    # Find connected components
    visited = bytearray(width * height)
    components = []
    
    for start in range(width * height):
        if not mask[start] or visited[start]:
            continue
            
        stack = [start]
        visited[start] = 1
        pixels = []
        min_x, min_y = width, height
        max_x, max_y = 0, 0
        
        while stack:
            curr = stack.pop()
            pixels.append(curr)
            cx = curr % width
            cy = curr // width
            min_x = min(min_x, cx)
            min_y = min(min_y, cy)
            max_x = max(max_x, cx)
            max_y = max(max_y, cy)
            
            # 4-connectivity neighbors
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height:
                    nidx = ny * width + nx
                    if mask[nidx] and not visited[nidx]:
                        visited[nidx] = 1
                        stack.append(nidx)
                        
        components.append({
            "size": len(pixels),
            "bbox": (min_x, min_y, max_x, max_y),
            "width": max_x - min_x + 1,
            "height": max_y - min_y + 1
        })
        
    # Sort components by size descending
    components.sort(key=lambda c: c["size"], reverse=True)
    return components

base_dir = os.path.dirname(os.path.abspath(__file__))
idle_path = os.path.join(base_dir, "run", "decoded", "idle.png")
if os.path.exists(idle_path):
    print("--- Analyzing idle.png ---")
    idle_components = analyze_components(idle_path)
    print(f"Total components found: {len(idle_components)}")
    for i, comp in enumerate(idle_components[:10]):
        if comp["size"] > 100: # Filter noise
            print(f"Component {i}: Size={comp['size']} pixels, BBox={comp['bbox']}, Dim={comp['width']}x{comp['height']}")

waving_path = os.path.join(base_dir, "run", "decoded", "waving.png")
if os.path.exists(waving_path):
    print("\n--- Analyzing waving.png ---")
    waving_components = analyze_components(waving_path)
    print(f"Total components found: {len(waving_components)}")
    for i, comp in enumerate(waving_components[:10]):
        if comp["size"] > 100:
            print(f"Component {i}: Size={comp['size']} pixels, BBox={comp['bbox']}, Dim={comp['width']}x{comp['height']}")
