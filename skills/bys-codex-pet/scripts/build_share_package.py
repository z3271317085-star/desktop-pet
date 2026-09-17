#!/usr/bin/env python3
"""Build a safe, Chinese-language offline share package for a Codex v2 pet."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PET_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "assets" / "share-package"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def has_webp_signature(path: Path) -> bool:
    with path.open("rb") as handle:
        header = handle.read(12)
    return len(header) == 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"


def safe_folder_name(value: str) -> str:
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "-", value).strip().rstrip(".")
    value = re.sub(r"\s+", "-", value)
    return value[:80] or "codex-pet"


def render_template(template_name: str, replacements: dict[str, str]) -> str:
    path = TEMPLATE_DIR / template_name
    text = path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace("{{" + key + "}}", value)
    unresolved = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    if unresolved:
        raise ValueError(f"模板仍有未替换字段：{', '.join(sorted(set(unresolved)))}")
    return text


def validate_https_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("--image-url 必须是无账号信息的绝对 HTTPS 地址")
    return value


def write_text(path: Path, content: str, executable: bool = False) -> None:
    encoding = "utf-8-sig" if path.suffix.lower() == ".ps1" else "utf-8"
    path.write_text(content, encoding=encoding, newline="\n")
    if executable and os.name != "nt":
        path.chmod(0o755)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pet-dir", type=Path, required=True, help="Directory containing pet.json and spritesheet.webp")
    parser.add_argument("--output-dir", type=Path, required=True, help="Parent directory for package and zip")
    parser.add_argument("--preview", type=Path, help="Optional contact-sheet preview")
    parser.add_argument("--image-url", help="Optional public HTTPS spritesheet URL for codex:// install link")
    parser.add_argument("--force", action="store_true", help="Replace an existing export with the same name")
    args = parser.parse_args()

    pet_dir = args.pet_dir.expanduser().resolve()
    pet_json_path = pet_dir / "pet.json"
    spritesheet_path = pet_dir / "spritesheet.webp"
    if not pet_json_path.is_file() or not spritesheet_path.is_file():
        raise SystemExit("宠物目录必须同时包含 pet.json 和 spritesheet.webp")

    pet = load_json(pet_json_path)
    pet_id = str(pet.get("id", ""))
    display_name = str(pet.get("displayName") or pet_id)
    description = str(pet.get("description") or "由不一书桌宠生成器制作的 Codex 桌宠")
    if not PET_ID_PATTERN.fullmatch(pet_id):
        raise SystemExit("pet.json 的 id 不安全或不符合分享包要求")
    if pet.get("spriteVersionNumber") != 2:
        raise SystemExit("仅支持 spriteVersionNumber: 2 的新桌宠分享包")
    if pet.get("spritesheetPath") != "spritesheet.webp":
        raise SystemExit("pet.json 的 spritesheetPath 必须是 spritesheet.webp")
    if not display_name.strip():
        raise SystemExit("pet.json 缺少有效 displayName")
    if spritesheet_path.stat().st_size == 0:
        raise SystemExit("spritesheet.webp 为空")
    if not has_webp_signature(spritesheet_path):
        raise SystemExit("spritesheet.webp 不是有效的 WebP 容器")

    output_dir = args.output_dir.expanduser().resolve(strict=False)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_name = safe_folder_name(f"{display_name}-codex-pet")
    package_dir = output_dir / package_name
    zip_path = output_dir / f"{package_name}.zip"
    if package_dir.exists():
        if not args.force:
            raise SystemExit(f"导出目录已存在：{package_dir}。如需替换请使用 --force。")
        shutil.rmtree(package_dir)
    if zip_path.exists():
        if not args.force:
            raise SystemExit(f"ZIP 已存在：{zip_path}。如需替换请使用 --force。")
        zip_path.unlink()

    pet_output = package_dir / "pet"
    pet_output.mkdir(parents=True)
    shutil.copy2(pet_json_path, pet_output / "pet.json")
    shutil.copy2(spritesheet_path, pet_output / "spritesheet.webp")
    if args.preview:
        preview = args.preview.expanduser().resolve()
        if not preview.is_file():
            raise SystemExit(f"预览图不存在：{preview}")
        shutil.copy2(preview, package_dir / "preview.png")

    install_link = ""
    if args.image_url:
        image_url = validate_https_url(args.image_url)
        install_link = "codex://pets/install?" + urlencode(
            {
                "name": display_name,
                "imageUrl": image_url,
                "description": description,
                "spriteVersionNumber": "2",
            },
            quote_via=quote,
        )
        write_text(package_dir / "install-link.txt", install_link + "\n")

    replacements = {
        "PET_ID": pet_id,
        "DISPLAY_NAME": display_name,
        "DESCRIPTION": description,
        "INSTALL_LINK_SECTION": (
            f"## 一键安装链接\n\n如果你的 Codex 已启用桌宠安装链接，可以点击或复制下面的地址：\n\n```text\n{install_link}\n```"
            if install_link
            else "## 一键安装链接\n\n当前分享包没有配置公开 HTTPS 精灵图地址，请使用下面的 Windows 或 macOS 离线安装方式。"
        ),
    }
    templates = {
        "安装说明.md.tmpl": ("安装说明.md", False),
        "install-windows.ps1.tmpl": ("install-windows.ps1", False),
        "install-macos.sh.tmpl": ("install-macos.sh", True),
        "uninstall-windows.ps1.tmpl": ("uninstall-windows.ps1", False),
        "uninstall-macos.sh.tmpl": ("uninstall-macos.sh", True),
    }
    for template_name, (output_name, executable) in templates.items():
        write_text(package_dir / output_name, render_template(template_name, replacements), executable=executable)

    files: dict[str, dict[str, object]] = {}
    for path in sorted(package_dir.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            relative = path.relative_to(package_dir).as_posix()
            files[relative] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    manifest = {
        "schema_version": 1,
        "generator": "bys-codex-pet",
        "generated_at": now_utc(),
        "pet": {
            "id": pet_id,
            "displayName": display_name,
            "description": description,
            "spriteVersionNumber": 2,
        },
        "install_link": install_link or None,
        "files": files,
    }
    write_text(package_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    archive = shutil.make_archive(str(zip_path.with_suffix("")), "zip", root_dir=package_dir.parent, base_dir=package_dir.name)
    print(
        json.dumps(
            {"package_dir": str(package_dir), "zip": archive, "install_link": install_link or None},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
