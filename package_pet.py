import json
import os
import shutil

base_dir = os.path.dirname(os.path.abspath(__file__))
run_dir = os.path.join(base_dir, "run")
request_path = os.path.join(run_dir, "pet_request.json")
with open(request_path, encoding="utf-8") as f:
    request = json.load(f)

pet_id = request["pet_id"]
display_name = request["display_name"]
description = request["description"]

dist_dir = os.path.join(base_dir, "dist", pet_id)
os.makedirs(dist_dir, exist_ok=True)

# Copy spritesheet
shutil.copy2(os.path.join(run_dir, "final", "spritesheet.webp"), os.path.join(dist_dir, "spritesheet.webp"))

# Write pet.json
pet_json = {
    "id": pet_id,
    "displayName": display_name,
    "description": description,
    "spritesheetPath": "spritesheet.webp",
    "animation": {
        "columns": 8,
        "rows": 9,
        "cellWidth": 192,
        "cellHeight": 208,
        "states": {
            "idle": {"row": 0, "frames": 6, "fps": 6},
            "running-right": {"row": 1, "frames": 8, "fps": 8},
            "running-left": {"row": 2, "frames": 8, "fps": 8},
            "waving": {"row": 3, "frames": 4, "fps": 6},
            "jumping": {"row": 4, "frames": 5, "fps": 8},
            "failed": {"row": 5, "frames": 8, "fps": 8},
            "waiting": {"row": 6, "frames": 6, "fps": 6},
            "running": {"row": 7, "frames": 6, "fps": 8},
            "review": {"row": 8, "frames": 6, "fps": 6}
        }
    }
}

with open(os.path.join(dist_dir, "pet.json"), "w", encoding="utf-8") as f:
    json.dump(pet_json, f, indent=2, ensure_ascii=False)

print(f"Pet packaged successfully to {dist_dir}!")
