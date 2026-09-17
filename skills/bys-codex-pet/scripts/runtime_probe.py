#!/usr/bin/env python3
"""Discover and verify local Python runtimes for hatch-pet compatibility mode."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def unique_existing(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        try:
            resolved = path.expanduser().resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if not resolved.is_file():
            continue
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            result.append(resolved)
    return result


def launcher_candidates() -> list[Path]:
    if os.name != "nt" or not shutil.which("py"):
        return []
    try:
        output_encoding = "mbcs" if os.name == "nt" else "utf-8"
        result = subprocess.run(
            ["py", "-0p"],
            check=False,
            capture_output=True,
            text=True,
            encoding=output_encoding,
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    candidates: list[Path] = []
    for line in result.stdout.splitlines():
        match = re.search(r"([A-Za-z]:\\.*?python(?:\.exe)?)\s*$", line.strip(), re.IGNORECASE)
        if match:
            candidates.append(Path(match.group(1)))
    return candidates


def path_candidates() -> list[Path]:
    names = ["python3", "python"] if os.name != "nt" else ["python.exe", "python3.exe"]
    candidates: list[Path] = []
    for name in names:
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    return candidates


def discover(explicit: list[str]) -> list[Path]:
    candidates = [Path(value) for value in explicit]
    candidates.append(Path(sys.executable))
    candidates.extend(launcher_candidates())
    candidates.extend(path_candidates())
    return unique_existing(candidates)


def probe_runtime(executable: Path, hatch_pet_dir: Path | None) -> dict:
    probe_code = r'''
import json
import pathlib
import re
import sys

result = {
    "executable": sys.executable,
    "python_version": ".".join(str(part) for part in sys.version_info[:3]),
    "pillow_version": None,
    "python_supported": sys.version_info >= (3, 10),
    "pillow_supported": False,
    "hatch_scripts_compiled": False,
    "errors": [],
}
try:
    import PIL
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
    result["pillow_version"] = getattr(PIL, "__version__", "unknown")
    match = re.match(r"(\d+)\.(\d+)", result["pillow_version"])
    result["pillow_supported"] = bool(match and (int(match.group(1)), int(match.group(2))) >= (9, 0))
except Exception as exc:
    result["errors"].append(f"Pillow import failed: {exc}")

hatch_dir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else None
if hatch_dir:
    scripts_dir = hatch_dir / "scripts"
    if not scripts_dir.is_dir():
        result["errors"].append(f"hatch-pet scripts directory missing: {scripts_dir}")
    else:
        try:
            scripts = sorted(scripts_dir.glob("*.py"))
            if not scripts:
                raise RuntimeError("no Python scripts found")
            for script in scripts:
                compile(script.read_text(encoding="utf-8"), str(script), "exec")
            result["hatch_scripts_compiled"] = True
        except Exception as exc:
            result["errors"].append(f"hatch-pet compile check failed: {exc}")
else:
    result["hatch_scripts_compiled"] = None

result["ok"] = bool(
    result["python_supported"]
    and result["pillow_supported"]
    and result["hatch_scripts_compiled"] is not False
    and not result["errors"]
)
print(json.dumps(result, ensure_ascii=False))
'''
    hatch_arg = str(hatch_pet_dir.resolve()) if hatch_pet_dir else ""
    try:
        completed = subprocess.run(
            [str(executable), "-X", "utf8", "-c", probe_code, hatch_arg],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"executable": str(executable), "ok": False, "errors": [str(exc)]}
    if completed.returncode != 0:
        return {
            "executable": str(executable),
            "ok": False,
            "errors": [completed.stderr.strip() or f"probe exited {completed.returncode}"],
        }
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {"executable": str(executable), "ok": False, "errors": [f"invalid probe JSON: {exc}"]}
    result["requested_executable"] = str(executable)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", action="append", default=[], help="Explicit interpreter path; may be repeated")
    parser.add_argument("--hatch-pet-dir", type=Path, help="Installed hatch-pet skill directory")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    hatch_dir = args.hatch_pet_dir.expanduser().resolve() if args.hatch_pet_dir else None
    candidates = discover(args.python)
    results = [probe_runtime(candidate, hatch_dir) for candidate in candidates]
    verified = [item for item in results if item.get("ok")]
    report = {
        "ok": bool(verified),
        "recommended": verified[0] if verified else None,
        "candidates": results,
        "policy": {
            "requires_explicit_user_consent": True,
            "use_exact_executable_path": True,
            "never_install_packages_silently": True,
            "compatibility_mode_is_not_hatch_pet_default": True,
        },
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if verified:
            best = verified[0]
            print("找到可验证的本机 Python 兼容运行时：")
            print(f"Python：{best['executable']} ({best['python_version']})")
            print(f"Pillow：{best['pillow_version']}")
            print("继续前仍需用户明确同意使用兼容模式。")
        else:
            print("没有找到通过验证的本机 Python/Pillow 运行时。")
            for item in results:
                print(f"- {item.get('executable')}: {'; '.join(item.get('errors', []))}")
    return 0 if verified else 2


if __name__ == "__main__":
    raise SystemExit(main())
