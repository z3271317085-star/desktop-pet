from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "skills" / "bys-codex-pet" / "scripts"


def run_script(name: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


class PreflightTests(unittest.TestCase):
    def test_preflight_emits_json_without_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env_home = Path(temp) / "codex-home"
            env = os.environ.copy()
            env["CODEX_HOME"] = str(env_home)
            env["PYTHONUTF8"] = "1"
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "preflight.py"), "--json", "--cwd", temp],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
            )
            report = json.loads(result.stdout)
            self.assertEqual(report["codex_home"], str(env_home.resolve()))
            self.assertIn("hatch-pet", report["skills"])
            self.assertFalse(env_home.exists())


class ProjectStateTests(unittest.TestCase):
    def test_project_state_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "my-project"
            run_script("project_state.py", "init", "--project-dir", str(project), "--project-id", "My Pet")
            path = project / "project-state.json"
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["project_id"], "my-pet")
            self.assertEqual(state["language"], "zh-CN")

            run_script(
                "project_state.py",
                "set",
                "--project-dir",
                str(project),
                "--stage",
                "character-review",
                "--next-action",
                "等待用户确认角色定稿",
            )
            run_script(
                "project_state.py",
                "approve",
                "--project-dir",
                str(project),
                "--checkpoint",
                "character",
            )
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["stage"], "character-review")
            self.assertTrue(state["checkpoints"]["character_approved"])

            run_script(
                "project_state.py",
                "runtime",
                "--project-dir",
                str(project),
                "--mode",
                "system-verified",
                "--python",
                sys.executable,
                "--python-version",
                ".".join(str(item) for item in sys.version_info[:3]),
                "--pillow-version",
                "12.2.0",
                "--consent",
            )
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["runtime"]["mode"], "system-verified")
            self.assertTrue(state["runtime"]["compatibility_consent"])
            self.assertEqual(Path(state["runtime"]["python"]), Path(sys.executable).resolve())

    def test_system_runtime_requires_consent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "my-project"
            run_script("project_state.py", "init", "--project-dir", str(project))
            result = run_script(
                "project_state.py",
                "runtime",
                "--project-dir",
                str(project),
                "--mode",
                "system-verified",
                "--python",
                sys.executable,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--consent", result.stderr + result.stdout)


class RuntimeProbeTests(unittest.TestCase):
    def test_probe_verifies_current_interpreter_and_hatch_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            hatch_dir = Path(temp) / "hatch-pet"
            scripts_dir = hatch_dir / "scripts"
            scripts_dir.mkdir(parents=True)
            (scripts_dir / "sample.py").write_text(
                "from __future__ import annotations\nfrom PIL import Image\n",
                encoding="utf-8",
            )
            result = run_script(
                "runtime_probe.py",
                "--json",
                "--python",
                sys.executable,
                "--hatch-pet-dir",
                str(hatch_dir),
            )
            report = json.loads(result.stdout)
            self.assertTrue(report["ok"], report)
            self.assertTrue(report["recommended"]["ok"])
            self.assertTrue(report["recommended"]["hatch_scripts_compiled"])
            self.assertTrue(Path(report["recommended"]["executable"]).is_absolute())


class SharePackageTests(unittest.TestCase):
    def create_pet(self, root: Path, version: int = 2, pet_id: str = "sample-pet") -> Path:
        pet_dir = root / "installed" / pet_id
        pet_dir.mkdir(parents=True)
        pet = {
            "id": pet_id,
            "displayName": "示例桌宠",
            "description": "用于测试的不一书桌宠",
            "spriteVersionNumber": version,
            "spritesheetPath": "spritesheet.webp",
        }
        (pet_dir / "pet.json").write_text(json.dumps(pet, ensure_ascii=False), encoding="utf-8")
        (pet_dir / "spritesheet.webp").write_bytes(b"RIFF\x08\x00\x00\x00WEBPVP8 ")
        return pet_dir

    def test_build_and_validate_directory_and_zip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pet_dir = self.create_pet(root)
            preview = root / "preview.png"
            preview.write_bytes(b"fake-preview")
            result = run_script(
                "build_share_package.py",
                "--pet-dir",
                str(pet_dir),
                "--output-dir",
                str(root / "exports"),
                "--preview",
                str(preview),
                "--image-url",
                "https://example.com/sample-pet.webp",
            )
            output = json.loads(result.stdout)
            package_dir = Path(output["package_dir"])
            zip_path = Path(output["zip"])
            self.assertTrue(package_dir.is_dir())
            self.assertTrue(zip_path.is_file())
            self.assertIn("codex://pets/install", output["install_link"])

            directory_report = json.loads(run_script("validate_share_package.py", str(package_dir)).stdout)
            zip_report = json.loads(run_script("validate_share_package.py", str(zip_path)).stdout)
            self.assertTrue(directory_report["ok"], directory_report)
            self.assertTrue(zip_report["ok"], zip_report)
            self.assertNotIn("{{PET_ID}}", (package_dir / "install-windows.ps1").read_text(encoding="utf-8"))
            self.assertNotIn("{{PET_ID}}", (package_dir / "install-macos.sh").read_text(encoding="utf-8"))

            sh = shutil.which("sh")
            powershell = shutil.which("powershell") or shutil.which("pwsh")
            install_home = root / "codex-home"
            install_env = os.environ.copy()
            install_env["CODEX_HOME"] = str(install_home)
            if os.name == "nt" and powershell:
                subprocess.run(
                    [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(package_dir / "install-windows.ps1")],
                    check=True,
                    capture_output=True,
                    env=install_env,
                )
                self.assertTrue((install_home / "pets" / "sample-pet" / "pet.json").is_file())
                subprocess.run(
                    [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(package_dir / "uninstall-windows.ps1"), "-Yes"],
                    check=True,
                    capture_output=True,
                    env=install_env,
                )
                self.assertFalse((install_home / "pets" / "sample-pet").exists())
            elif sh:
                subprocess.run([sh, "-n", str(package_dir / "install-macos.sh")], check=True)
                subprocess.run([sh, "-n", str(package_dir / "uninstall-macos.sh")], check=True)
                subprocess.run([sh, str(package_dir / "install-macos.sh")], check=True, capture_output=True, env=install_env)
                self.assertTrue((install_home / "pets" / "sample-pet" / "pet.json").is_file())
                subprocess.run([sh, str(package_dir / "uninstall-macos.sh"), "--yes"], check=True, capture_output=True, env=install_env)
                self.assertFalse((install_home / "pets" / "sample-pet").exists())

    def test_rejects_v1_pet(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pet_dir = self.create_pet(root, version=1)
            result = run_script(
                "build_share_package.py",
                "--pet-dir",
                str(pet_dir),
                "--output-dir",
                str(root / "exports"),
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("spriteVersionNumber", result.stderr + result.stdout)

    def test_rejects_unsafe_pet_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pet_dir = self.create_pet(root, pet_id="safe-folder")
            data = json.loads((pet_dir / "pet.json").read_text(encoding="utf-8"))
            data["id"] = "../escape"
            (pet_dir / "pet.json").write_text(json.dumps(data), encoding="utf-8")
            result = run_script(
                "build_share_package.py",
                "--pet-dir",
                str(pet_dir),
                "--output-dir",
                str(root / "exports"),
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("id", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
