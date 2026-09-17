#!/usr/bin/env python3
"""Inspect local prerequisites for the bys-codex-pet guided workflow."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path
from typing import Iterable


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = os.path.normcase(str(path.resolve(strict=False)))
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def repo_skill_roots(start: Path) -> list[Path]:
    roots: list[Path] = []
    current = start.resolve()
    while True:
        roots.append(current / ".agents" / "skills")
        if current.parent == current:
            break
        current = current.parent
    return roots


def locate_skill(name: str, roots: list[Path], system: bool = False) -> list[Path]:
    candidates: list[Path] = []
    for root in roots:
        if system:
            candidates.append(root / ".system" / name / "SKILL.md")
        candidates.append(root / name / "SKILL.md")
    return [path.resolve() for path in unique_paths(candidates) if path.is_file()]


def nearest_existing_parent(path: Path) -> Path:
    current = path
    while not current.exists() and current.parent != current:
        current = current.parent
    return current


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="Directory used for repo-scoped skill discovery")
    args = parser.parse_args()

    home = Path.home().resolve()
    codex_home = Path(os.environ.get("CODEX_HOME", home / ".codex")).expanduser().resolve(strict=False)
    roots = unique_paths(
        [
            codex_home / "skills",
            home / ".agents" / "skills",
            *repo_skill_roots(args.cwd),
        ]
    )

    hatch_pet = locate_skill("hatch-pet", roots)
    imagegen = locate_skill("imagegen", roots, system=True)
    skill_installer = locate_skill("skill-installer", roots, system=True)
    pets_dir = codex_home / "pets"
    writable_parent = nearest_existing_parent(pets_dir)
    pets_writable = writable_parent.exists() and os.access(writable_parent, os.W_OK)

    recommendations: list[str] = []
    if not hatch_pet:
        recommendations.append("缺少 hatch-pet：优先在设置 > Pets > Create your own pet 中安装，或使用 $skill-installer 安装 curated hatch-pet。")
    if not imagegen:
        recommendations.append("缺少 imagegen system Skill：建议更新并重启 Codex，不要从未知第三方仓库安装同名替代品。")
    if not pets_writable:
        recommendations.append(f"桌宠目录的现有父目录不可写：{writable_parent}")
    recommendations.append("文件体检无法确认当前会话是否暴露内置 image_gen 工具，也无法确认 Pets UI；请由 Agent 继续检查当前能力。")

    report = {
        "ok": bool(hatch_pet and imagegen and pets_writable),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "home": str(home),
        "codex_home": str(codex_home),
        "pets_dir": str(pets_dir),
        "pets_parent_writable": pets_writable,
        "skill_roots_checked": [str(path) for path in roots],
        "skills": {
            "hatch-pet": [str(path) for path in hatch_pet],
            "imagegen": [str(path) for path in imagegen],
            "skill-installer": [str(path) for path in skill_installer],
        },
        "recommendations": recommendations,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        status = "就绪" if report["ok"] else "需要处理"
        print(f"不一书桌宠生成器环境体检：{status}")
        print(f"操作系统：{report['platform']} {report['platform_release']}")
        print(f"CODEX_HOME：{codex_home}")
        for name, paths in report["skills"].items():
            print(f"{name}：{paths[0] if paths else '未找到'}")
        for item in recommendations:
            print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
