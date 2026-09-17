import os
import math
from PIL import Image

CELL_WIDTH = 192
CELL_HEIGHT = 208

def color_dist(c1, c2):
    return math.sqrt(sum((a - b)**2 for a, b in zip(c1, c2)))

def extract_frames_from_grid(image_path, frame_count, output_dir, chroma_key=(0, 255, 0), threshold=96.0):
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
            
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height:
                    nidx = ny * width + nx
                    if mask[nidx] and not visited[nidx]:
                        visited[nidx] = 1
                        stack.append(nidx)
                        
        components.append({
            "pixels": pixels,
            "size": len(pixels),
            "bbox": (min_x, min_y, max_x + 1, max_y + 1),
            "center_x": (min_x + max_x) / 2,
            "center_y": (min_y + max_y) / 2
        })
        
    # Filter noise components
    components = [c for c in components if c["size"] > 1000]
    print(f"Detected {len(components)} character components (expected {frame_count}).")
    
    if len(components) != frame_count:
        print(f"Warning: Component count mismatch! Sorting top {frame_count} components.")
        components.sort(key=lambda c: c["size"], reverse=True)
        components = components[:frame_count]
        
    # Sort components into rows based on Y coordinates
    # We can cluster Y centers into rows
    # For a grid, Y centers will be distinctly grouped
    # Let's sort all components by Y center
    components.sort(key=lambda c: c["center_y"])
    
    # Simple row clustering: if the distance between adjacent Y centers is > 100 pixels, it's a new row
    rows = []
    current_row = []
    for c in components:
        if not current_row:
            current_row.append(c)
        else:
            if c["center_y"] - current_row[-1]["center_y"] > 150:
                rows.append(current_row)
                current_row = [c]
            else:
                current_row.append(c)
    if current_row:
        rows.append(current_row)
        
    # Sort each row left-to-right (by X center)
    sorted_components = []
    for row in rows:
        row.sort(key=lambda c: c["center_x"])
        sorted_components.extend(row)
        
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract each component and center it in the cell
    for idx, comp in enumerate(sorted_components):
        bbox = comp["bbox"]
        # Crop original image with transparency
        # Convert original to RGBA
        rgba_img = Image.open(image_path).convert("RGBA")
        
        # Make pixels outside the component transparent in the crop
        source_pixels = rgba_img.load()
        comp_pixel_set = set(comp["pixels"])
        
        # Extract sprite bounding box dimensions
        min_x, min_y, max_x, max_y = bbox
        w = max_x - min_x
        h = max_y - min_y
        
        sprite_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sprite_pixels = sprite_img.load()
        
        for idx_p in comp["pixels"]:
            px = idx_p % width
            py = idx_p // width
            sprite_pixels[px - min_x, py - min_y] = source_pixels[px, py]
            
        # Scale if it exceeds the maximum cell dimensions (with 10px margins)
        max_w = CELL_WIDTH - 10
        max_h = CELL_HEIGHT - 10
        scale = min(max_w / w, max_h / h, 1.0)
        
        if scale < 1.0:
            new_w = max(1, round(w * scale))
            new_h = max(1, round(h * scale))
            sprite_img = sprite_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            w, h = new_w, new_h
            
        # Center in the target cell
        target_cell = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
        left = (CELL_WIDTH - w) // 2
        top = (CELL_HEIGHT - h) // 2
        target_cell.alpha_composite(sprite_img, (left, top))
        
        # Save frame
        frame_path = os.path.join(output_dir, f"{idx:02d}.png")
        target_cell.save(frame_path)
        print(f"  Saved frame {idx:02d} to {frame_path}")

# Run test extraction
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(base_dir, "run", "decoded", "idle.png")
    output_dir = os.path.join(base_dir, "run", "frames", "idle_test")
    if os.path.exists(image_path):
        extract_frames_from_grid(image_path, 6, output_dir)
