import os
import time

search_dirs = [
    os.environ.get("TEMP", ""),
    os.path.expanduser("~")
]

now = time.time()
found_files = []

for s_dir in search_dirs:
    if not os.path.exists(s_dir):
        continue
    for root, dirs, files in os.walk(s_dir):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                path = os.path.join(root, file)
                try:
                    mtime = os.path.getmtime(path)
                    # Files created/modified in the last 15 minutes
                    if now - mtime < 900:
                        found_files.append((path, mtime))
                except Exception:
                    pass

found_files.sort(key=lambda x: x[1], reverse=True)
print("Found recently updated image files:")
for f, t in found_files:
    print(f"File: {f}, Modified at: {time.ctime(t)}")
