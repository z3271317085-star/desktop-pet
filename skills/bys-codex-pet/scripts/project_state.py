#!/usr/bin/env python3
"""Create and update resumable bys-codex-pet project state."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


STAGES = (
    "environment",
    "intake",
    "character-review",
    "motion-review",
    "final-review",
    "installed",
    "shared",
)
CHECKPOINTS = {
    "character": "character_approved",
    "motion": "motion_approved",
    "final": "final_approved",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "codex-pet"


def state_path(project_dir: Path) -> Path:
    return project_dir.expanduser().resolve(strict=False) / "project-state.json"


def load_state(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"状态文件不存在：{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, path)


def init_state(args: argparse.Namespace) -> int:
    path = state_path(args.project_dir)
    if path.exists() and not args.force:
        raise SystemExit(f"状态文件已存在：{path}。如需重建请使用 --force。")
    project_id = safe_slug(args.project_id or f"codex-pet-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    data = {
        "schema_version": 1,
        "generator": "bys-codex-pet",
        "language": "zh-CN",
        "project_id": project_id,
        "pet_name": args.pet_name or "",
        "pet_id": "",
        "stage": "environment",
        "mode": args.mode,
        "reference_images": [],
        "character_brief": "",
        "style_preset": "auto",
        "style_notes": "",
        "consent_confirmed": False,
        "runtime": {
            "mode": "unresolved",
            "python": "",
            "python_version": "",
            "pillow_version": "",
            "compatibility_consent": False,
        },
        "checkpoints": {
            "character_approved": False,
            "motion_approved": False,
            "final_approved": False,
        },
        "paths": {
            "hatch_run": "",
            "canonical_base": "",
            "standard_contact_sheet": "",
            "final_contact_sheet": "",
            "installed_pet_dir": "",
            "share_package": "",
        },
        "next_action": "运行依赖体检",
        "updated_at": now_utc(),
    }
    atomic_write(path, data)
    print(path)
    return 0


def set_state(args: argparse.Namespace) -> int:
    path = state_path(args.project_dir)
    data = load_state(path)
    if args.stage:
        data["stage"] = args.stage
    if args.next_action is not None:
        data["next_action"] = args.next_action
    if args.pet_name is not None:
        data["pet_name"] = args.pet_name
    if args.pet_id is not None:
        data["pet_id"] = args.pet_id
    if args.hatch_run is not None:
        data.setdefault("paths", {})["hatch_run"] = str(Path(args.hatch_run).expanduser().resolve(strict=False))
    data["updated_at"] = now_utc()
    atomic_write(path, data)
    print(path)
    return 0


def approve_state(args: argparse.Namespace) -> int:
    path = state_path(args.project_dir)
    data = load_state(path)
    key = CHECKPOINTS[args.checkpoint]
    data.setdefault("checkpoints", {})[key] = not args.revoke
    data["updated_at"] = now_utc()
    atomic_write(path, data)
    print(path)
    return 0


def runtime_state(args: argparse.Namespace) -> int:
    path = state_path(args.project_dir)
    data = load_state(path)
    runtime = data.setdefault("runtime", {})
    if args.mode == "system-verified":
        if not args.consent:
            raise SystemExit("system-verified 模式必须由用户明确同意并传入 --consent")
        if not args.python:
            raise SystemExit("system-verified 模式必须记录 --python 绝对路径")
        python_path = Path(args.python).expanduser()
        if not python_path.is_absolute() or not python_path.is_file():
            raise SystemExit("--python 必须是存在的绝对解释器路径")
        runtime["python"] = str(python_path.resolve())
    else:
        runtime["python"] = str(Path(args.python).expanduser().resolve()) if args.python else ""
    runtime["mode"] = args.mode
    runtime["python_version"] = args.python_version or ""
    runtime["pillow_version"] = args.pillow_version or ""
    runtime["compatibility_consent"] = bool(args.consent and args.mode == "system-verified")
    if args.next_action is not None:
        data["next_action"] = args.next_action
    data["updated_at"] = now_utc()
    atomic_write(path, data)
    print(path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create project-state.json")
    init_parser.add_argument("--project-dir", type=Path, required=True)
    init_parser.add_argument("--project-id")
    init_parser.add_argument("--pet-name")
    init_parser.add_argument("--mode", choices=("guided", "fast"), default="guided")
    init_parser.add_argument("--force", action="store_true")
    init_parser.set_defaults(func=init_state)

    set_parser = subparsers.add_parser("set", help="Update common state fields")
    set_parser.add_argument("--project-dir", type=Path, required=True)
    set_parser.add_argument("--stage", choices=STAGES)
    set_parser.add_argument("--next-action")
    set_parser.add_argument("--pet-name")
    set_parser.add_argument("--pet-id")
    set_parser.add_argument("--hatch-run")
    set_parser.set_defaults(func=set_state)

    approve_parser = subparsers.add_parser("approve", help="Approve or revoke a checkpoint")
    approve_parser.add_argument("--project-dir", type=Path, required=True)
    approve_parser.add_argument("--checkpoint", choices=tuple(CHECKPOINTS), required=True)
    approve_parser.add_argument("--revoke", action="store_true")
    approve_parser.set_defaults(func=approve_state)

    runtime_parser = subparsers.add_parser("runtime", help="Record the selected Python runtime")
    runtime_parser.add_argument("--project-dir", type=Path, required=True)
    runtime_parser.add_argument("--mode", choices=("unresolved", "bundled", "system-verified"), required=True)
    runtime_parser.add_argument("--python")
    runtime_parser.add_argument("--python-version")
    runtime_parser.add_argument("--pillow-version")
    runtime_parser.add_argument("--consent", action="store_true")
    runtime_parser.add_argument("--next-action")
    runtime_parser.set_defaults(func=runtime_state)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
