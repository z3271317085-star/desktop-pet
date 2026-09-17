import os
import sys
import json
import math
from PIL import Image

CELL_WIDTH = 192
CELL_HEIGHT = 208

ROW_FRAME_COUNTS = {
    "idle": 6,
    "running-right": 8,
    "waving": 4,
    "jumping": 5,
    "failed": 8,
    "waiting": 6,
    "running": 6,
    "review": 6,
}

def color_dist(c1, c2):
    return math.sqrt(sum((a - b)**2 for a, b in zip(c1, c2)))

def extract_state_frames(image_path, state, frame_count, output_dir, chroma_key=(0, 255, 0), threshold=96.0):
    if not os.path.exists(image_path):
        print(f"Error: {image_path} does not exist!")
        return False
        
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
    print(f"State '{state}': Detected {len(components)} character components (expected {frame_count}).")
    
    if len(components) < frame_count:
        print(f"Warning: Not enough components for '{state}'! Found {len(components)}, expected {frame_count}.")
        # Use simple slot fallback if components fail
        return extract_slots_fallback(image_path, frame_count, output_dir)
        
    if len(components) > frame_count:
        print(f"Filtering top {frame_count} largest components out of {len(components)}.")
        components.sort(key=lambda c: c["size"], reverse=True)
        components = components[:frame_count]
        
    # Sort components into rows based on Y coordinates
    components.sort(key=lambda c: c["center_y"])
    
    rows = []
    current_row = []
    for c in components:
        if not current_row:
            current_row.append(c)
        else:
            # If the Y distance to the previous component's center is significant, it's a new row
            if c["center_y"] - current_row[-1]["center_y"] > 120:
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
        
    # Ensure output directory exists
    state_output_dir = os.path.join(output_dir, state)
    os.makedirs(state_output_dir, exist_ok=True)
    
    # Extract each component
    rgba_img = Image.open(image_path).convert("RGBA")
    source_pixels = rgba_img.load()
    
    for idx, comp in enumerate(sorted_components):
        bbox = comp["bbox"]
        min_x, min_y, max_x, max_y = bbox
        w = max_x - min_x
        h = max_y - min_y
        
        # Crop component pixels with transparency
        sprite_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sprite_pixels = sprite_img.load()
        for idx_p in comp["pixels"]:
            px = idx_p % width
            py = idx_p // width
            sprite_pixels[px - min_x, py - min_y] = source_pixels[px, py]
            
        # Scale if it exceeds the maximum cell dimensions
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
        frame_path = os.path.join(state_output_dir, f"{idx:02d}.png")
        target_cell.save(frame_path)
    print(f"  Successfully extracted {frame_count} frames for '{state}'.")
    return True

def extract_slots_fallback(image_path, frame_count, output_dir):
    print("  Falling back to equal slot-based slicing...")
    # Assume it's a 2x3 or 2x4 grid based on frame count
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    # We assume a 2-row layout for grids:
    # 4 frames: 2x2 grid
    # 5 or 6 frames: 2x3 grid
    # 8 frames: 2x4 grid
    if frame_count <= 4:
        cols, rows = 2, 2
    elif frame_count <= 6:
        cols, rows = 3, 2
    else:
        cols, rows = 4, 2
        
    cell_w = width // cols
    cell_h = height // rows
    
    state = os.path.basename(os.path.dirname(output_dir)) or "fallback"
    state_output_dir = output_dir
    os.makedirs(state_output_dir, exist_ok=True)
    
    idx = 0
    for r in range(rows):
        for c in range(cols):
            if idx >= frame_count:
                break
            left = c * cell_w
            top = r * cell_h
            crop = img.crop((left, top, left + cell_w, top + cell_h))
            
            # Key out green background in fallback
            rgba = crop.convert("RGBA")
            pixels = rgba.load()
            for y in range(rgba.height):
                for x in range(rgba.width):
                    red, green, blue, alpha = pixels[x, y]
                    if color_dist((red, green, blue), (0, 255, 0)) <= 96.0:
                        pixels[x, y] = (0, 0, 0, 0)
                        
            # Get bounding box of non-transparent part
            bbox = rgba.getbbox()
            target_cell = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
            if bbox:
                sprite = rgba.crop(bbox)
                w, h = sprite.size
                max_w = CELL_WIDTH - 10
                max_h = CELL_HEIGHT - 10
                scale = min(max_w / w, max_h / h, 1.0)
                if scale < 1.0:
                    new_w = max(1, round(w * scale))
                    new_h = max(1, round(h * scale))
                    sprite = sprite.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    w, h = new_w, new_h
                left_c = (CELL_WIDTH - w) // 2
                top_c = (CELL_HEIGHT - h) // 2
                target_cell.alpha_composite(sprite, (left_c, top_c))
                
            frame_path = os.path.join(state_output_dir, f"{idx:02d}.png")
            target_cell.save(frame_path)
            idx += 1
    print(f"  Successfully extracted {frame_count} fallback frames.")
    return True

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    decoded_dir = os.path.join(base_dir, "run", "decoded")
    output_dir = os.path.join(base_dir, "run", "frames")
    
    # Process states
    states = ["idle", "running-right", "waving", "jumping", "failed", "waiting", "running", "review"]
    for state in states:
        img_path = os.path.join(decoded_dir, f"{state}.png")
        frame_count = ROW_FRAME_COUNTS[state]
        print(f"Processing state: {state}")
        extract_state_frames(img_path, state, frame_count, output_dir)
        
    # Mirror running-right to running-left
    print("Generating running-left by mirroring running-right...")
    rr_dir = os.path.join(output_dir, "running-right")
    rl_dir = os.path.join(output_dir, "running-left")
    os.makedirs(rl_dir, exist_ok=True)
    if os.path.exists(rr_dir):
        for f in os.listdir(rr_dir):
            if f.endswith(".png"):
                img = Image.open(os.path.join(rr_dir, f))
                mirrored = img.transpose(Image.FLIP_LEFT_RIGHT)
                mirrored.save(os.path.join(rl_dir, f))
        print("  Mirrored running-right to running-left successfully.")
    else:
        print("  Error: running-right folder not found!")
