import os
import math
from PIL import Image

def color_dist(c1, c2):
    return math.sqrt(sum((a - b)**2 for a, b in zip(c1, c2)))

def analyze_components(image_path, chroma_key=(0, 255, 0), threshold=96.0):
    if not os.path.exists(image_path):
        return None
    img = Image.open(image_path).convert("RGB")
    width, height = img.size
    
    mask = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            r, g, b = img.getpixel((x, y))
            if color_dist((r, g, b), chroma_key) > threshold:
                mask[y * width + x] = 1
                
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
        
    components.sort(key=lambda c: c["size"], reverse=True)
    return components

files = ["failed.png", "waiting.png", "running.png", "review.png"]
base_dir = os.path.dirname(os.path.abspath(__file__))
decoded_dir = os.path.join(base_dir, "run", "decoded")

for f in files:
    p = os.path.join(decoded_dir, f)
    print(f"=== File: {f} ===")
    comps = analyze_components(p)
    if comps is None:
        print("  File not found")
        continue
    print(f"  Total components found: {len(comps)}")
    valid_count = sum(1 for c in comps if c["size"] > 1000)
    print(f"  Character-sized components (>1000px): {valid_count}")
    for i, comp in enumerate(comps[:10]):
        if comp["size"] > 1000:
            print(f"    Component {i}: Size={comp['size']} px, BBox={comp['bbox']}, Dim={comp['width']}x{comp['height']}")
