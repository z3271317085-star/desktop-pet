# 项目状态与断点恢复

## 状态文件

每个项目根目录保存 `project-state.json`。使用 UTF-8 JSON，不写入 API Key、访问令牌或图片二进制。

建议结构：

```json
{
  "schema_version": 1,
  "generator": "bys-codex-pet",
  "language": "zh-CN",
  "project_id": "friendly-slug-20260713-203000",
  "pet_name": "",
  "pet_id": "",
  "stage": "environment",
  "mode": "guided",
  "reference_images": [],
  "character_brief": "",
  "style_preset": "auto",
  "style_notes": "",
  "consent_confirmed": false,
  "runtime": {
    "mode": "unresolved",
    "python": "",
    "python_version": "",
    "pillow_version": "",
    "compatibility_consent": false
  },
  "checkpoints": {
    "character_approved": false,
    "motion_approved": false,
    "final_approved": false
  },
  "paths": {
    "hatch_run": "",
    "canonical_base": "",
    "standard_contact_sheet": "",
    "final_contact_sheet": "",
    "installed_pet_dir": "",
    "share_package": ""
  },
  "next_action": "运行依赖体检",
  "updated_at": "2026-07-13T12:30:00Z"
}
```

## 阶段值

允许阶段：

```text
environment
intake
character-review
motion-review
final-review
installed
shared
```

只在真实文件或用户确认存在后推进阶段。不能因为已经发送了确认问题就把检查点标记为通过。

## 初始化与更新

使用 `scripts/project_state.py init` 创建状态，使用 `set` 更新简单字段和检查点。复杂路径或列表也可由 Agent 以安全的 JSON 编辑方式更新。

示例：

```bash
python scripts/project_state.py init --project-dir /path/to/project --project-id my-pet
python scripts/project_state.py set --project-dir /path/to/project --stage character-review --next-action "等待用户确认角色定稿"
python scripts/project_state.py approve --project-dir /path/to/project --checkpoint character
python scripts/project_state.py runtime --project-dir /path/to/project --mode bundled --python /bundled/python --python-version 3.11.0 --pillow-version 11.0.0
python scripts/project_state.py runtime --project-dir /path/to/project --mode system-verified --python /local/python --python-version 3.13.5 --pillow-version 12.2.0 --consent
```

`system-verified` 必须带 `--consent` 和存在的绝对解释器路径。状态里记录路径不代表用户曾同意；只有 `compatibility_consent: true` 才允许继续。

## 恢复规则

用户说“继续桌宠项目”时：

1. 优先使用用户给出的项目目录。
2. 未给目录时，在最近使用的项目路径和 `<CODEX_HOME>/pet-runs/bys-codex-pet/` 中查找 `project-state.json`。
3. 读取当前阶段、检查点与 `next_action`。
4. 验证状态里引用的关键文件仍存在。
5. 缺失文件时回退到最后一个真实通过的检查点，不伪造完成状态。
6. 如果上次阻塞是 bundled runtime 缺失，先读取 `runtime`：已有 system-verified 授权时直接复验并继续；未授权时运行探针，不再循环要求重启。
7. 用两三句话说明恢复位置与下一步。

## 隐私

状态文件可以保存参考图片的本地绝对路径，但不得复制照片到 GitHub 仓库。导出分享包时不包含状态文件，除非先生成已去除本地路径和私人信息的公开摘要。
