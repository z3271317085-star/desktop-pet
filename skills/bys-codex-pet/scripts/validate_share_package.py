#!/usr/bin/env python3
"""Validate a bys-codex-pet share directory or zip without installing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PET_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
REQUIRED_FILES = {
    "pet/pet.json",
    "pet/spritesheet.webp",
    "安装说明.md",
    "install-windows.ps1",
    "install-macos.sh",
    "uninstall-windows.ps1",
    "uninstall-macos.sh",
    "manifest.json",
}
BANNED_MARKERS = (
    "project-state",
    ".env",
    "source-photo",
    "reference-image",
    "prompts/",
    "qa/",
    "generated_images/",
    "openai_api_key",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def has_webp_signature(path: Path) -> bool:
    with path.open("rb") as handle:
        header = handle.read(12)
    return len(header) == 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"


def locate_root(path: Path) -> Path:
    if (path / "manifest.json").is_file():
        return path
    children = [child for child in path.iterdir() if child.is_dir()]
    if len(children) == 1 and (children[0] / "manifest.json").is_file():
        return children[0]
    raise ValueError("无法定位分享包根目录")


def safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as handle:
        root = destination.resolve()
        for member in handle.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"ZIP 包含不安全路径：{member.filename}")
        handle.extractall(destination)


def validate_install_link(link: str, errors: list[str]) -> None:
    parsed = urlparse(link)
    if parsed.scheme != "codex" or parsed.netloc != "pets" or parsed.path != "/install":
        errors.append("install-link.txt 不是 codex://pets/install 链接")
        return
    query = parse_qs(parsed.query)
    if not query.get("name", [""])[0].strip():
        errors.append("安装链接缺少 name")
    image_url = query.get("imageUrl", [""])[0]
    image_parsed = urlparse(image_url)
    if image_parsed.scheme != "https" or not image_parsed.netloc:
        errors.append("安装链接的 imageUrl 不是绝对 HTTPS 地址")
    if query.get("spriteVersionNumber", [""])[0] != "2":
        errors.append("安装链接没有声明 spriteVersionNumber=2")


def validate_root(root: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    actual_files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    missing = sorted(REQUIRED_FILES - actual_files)
    if missing:
        errors.append("缺少文件：" + ", ".join(missing))

    for relative in sorted(actual_files):
        lowered = relative.lower()
        if any(marker in lowered for marker in BANNED_MARKERS):
            errors.append(f"发现不应分享的文件或路径：{relative}")

    pet: dict = {}
    pet_json_path = root / "pet" / "pet.json"
    if pet_json_path.is_file():
        try:
            pet = json.loads(pet_json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"pet.json 无法读取：{exc}")
        else:
            pet_id = str(pet.get("id", ""))
            if not PET_ID_PATTERN.fullmatch(pet_id):
                errors.append("pet.json 的 id 不安全")
            if pet.get("spriteVersionNumber") != 2:
                errors.append("pet.json 必须使用 spriteVersionNumber: 2")
            if pet.get("spritesheetPath") != "spritesheet.webp":
                errors.append("pet.json 的 spritesheetPath 必须是 spritesheet.webp")
            if not str(pet.get("displayName", "")).strip():
                errors.append("pet.json 缺少 displayName")

    spritesheet = root / "pet" / "spritesheet.webp"
    if spritesheet.is_file() and spritesheet.stat().st_size == 0:
        errors.append("spritesheet.webp 为空")
    elif spritesheet.is_file() and not has_webp_signature(spritesheet):
        errors.append("spritesheet.webp 不是有效的 WebP 容器")

    manifest_path = root / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"manifest.json 无法读取：{exc}")
        else:
            if manifest.get("generator") != "bys-codex-pet":
                errors.append("manifest.json generator 不正确")
            if pet and manifest.get("pet", {}).get("id") != pet.get("id"):
                errors.append("manifest.json 与 pet.json 的宠物 id 不一致")
            for relative, metadata in manifest.get("files", {}).items():
                file_path = root / Path(relative)
                if not file_path.is_file():
                    errors.append(f"manifest 引用的文件不存在：{relative}")
                    continue
                expected = str(metadata.get("sha256", ""))
                if expected != sha256(file_path):
                    errors.append(f"文件校验失败：{relative}")

    link_path = root / "install-link.txt"
    if link_path.is_file():
        link = link_path.read_text(encoding="utf-8").strip()
        validate_install_link(link, errors)
    else:
        warnings.append("未提供一键安装链接；离线安装包仍可使用")

    return {
        "ok": not errors,
        "root": str(root),
        "pet_id": pet.get("id") if pet else None,
        "errors": errors,
        "warnings": warnings,
        "files": sorted(actual_files),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="Share package directory or zip")
    args = parser.parse_args()
    package = args.package.expanduser().resolve()
    if not package.exists():
        raise SystemExit(f"分享包不存在：{package}")

    if package.is_dir():
        report = validate_root(locate_root(package))
    elif package.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory(prefix="bys-pet-validate-") as temp:
            destination = Path(temp)
            safe_extract(package, destination)
            report = validate_root(locate_root(destination))
            report["root"] = str(package)
    else:
        raise SystemExit("仅支持目录或 .zip 分享包")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
