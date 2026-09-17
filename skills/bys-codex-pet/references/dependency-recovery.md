# 依赖体检与恢复

## 目录

- 检查范围
- 常见路径
- 恢复矩阵
- 图片生成回退
- Python 运行时选择
- 防止恢复死循环
- 重启后的恢复

## 检查范围

运行 `scripts/preflight.py --json` 检查：

- `CODEX_HOME` 与用户目录
- `$hatch-pet` Skill 文件
- `$imagegen` Skill 文件
- `$skill-installer` 是否可见
- 本地 pets 目录是否可创建或已存在
- 当前操作系统

文件检查无法证明当前会话一定暴露内置图片工具。Agent 还要检查自己的可用工具列表，并确认当前使用的是支持 Pets 的 Codex/ChatGPT 桌面端。

文件检查也不能替代 Codex app 的 `load_workspace_dependencies`。该工具返回 bundled Python 时优先使用；返回未配置时立即进入“Python 运行时选择”，不要等到用户完成全部素材沟通后才发现。

## 常见路径

默认 `CODEX_HOME` 为用户主目录下的 `.codex`。用户设置了 `CODEX_HOME` 时始终尊重该值。

```text
Windows: %CODEX_HOME% 或 %USERPROFILE%\.codex
macOS:   $CODEX_HOME 或 ~/.codex
```

常见依赖位置：

```text
<CODEX_HOME>/skills/hatch-pet/SKILL.md
<CODEX_HOME>/skills/.system/imagegen/SKILL.md
<CODEX_HOME>/skills/.system/skill-installer/SKILL.md
```

也检查用户级 `~/.agents/skills/<skill-name>/SKILL.md` 与当前仓库向上层级中的 `.agents/skills`。

## 恢复矩阵

### 全部就绪

创建或恢复项目状态，进入素材采集。

### 缺少 hatch-pet

桌面端优先路径：

1. 打开 **设置 > Pets**。
2. 选择 **Create your own pet**。
3. 等待应用安装捆绑的 `hatch-pet` 并重新加载 Skills。
4. 回到原任务，重新运行体检。

CLI/IDE 路径：明确调用 `$skill-installer` 安装 curated `hatch-pet`，或给它 OpenAI skills 仓库中的对应路径。安装完成后在下一轮重试；如果未出现，重启 Codex。

不要把 `hatch-pet` 的 900 多行说明复制到本 Skill。它是独立升级的技术真源。

### 缺少 imagegen Skill

`imagegen` 通常是 system Skill。先建议：

1. 更新 Codex/ChatGPT 桌面端。
2. 重启应用并重新打开任务。
3. 确认 system skills 没有被损坏或禁用。

不要默认从第三方仓库下载同名 Skill，也不要创建简化版替代品。

### Skill 存在但图片工具不可用

默认停止在角色制作前。说明可选 CLI 回退：

- 需要本机 `OPENAI_API_KEY`
- 不能让用户在聊天中粘贴完整密钥
- 必须获得用户明确同意
- 继续遵循已安装 `$imagegen` 对模型、透明背景和输出路径的当前规则

第三方模型/API 会话可能能正常对话和运行终端，但没有 Codex app 内置的 `image_gen` 工具。必须分别检查“语言模型可用”和“图片工具可用”，不能从前者推断后者。

### Pets 功能不可用

仍可整理角色方案和生成桌宠文件，但不得声称已经成功启用浮动桌宠。建议更新桌面端；只有当设置页出现 Pets 后再执行安装验收。

## 图片生成回退

回退是异常路径，不是普通的质量选项。内置图片工具失败时，不因尺寸、文件名或普通质量偏好自动切换 CLI。

用户同意 CLI 回退后，让其在本机设置环境变量，然后仅确认“已设置”，不要索取密钥内容。

## Python 运行时选择

### 1. Bundled 模式

调用 `load_workspace_dependencies`。若返回 Python 路径：

- 使用返回的精确绝对路径
- 不再探测系统 Python
- 记录 `runtime.mode=bundled`
- 记录解释器路径和版本

### 2. System-verified 兼容模式

bundled runtime 未配置时运行：

```bash
python scripts/runtime_probe.py --json --hatch-pet-dir /absolute/path/to/hatch-pet
```

探针会发现：

- 当前启动探针的 `sys.executable`
- Windows `py -0p` 列出的解释器
- PATH 中的 `python3`、`python` 或 Windows 可执行文件
- 用户通过 `--python` 明确给出的路径

每个候选必须通过：

- Python 3.10 或更高
- Pillow 9.0 或更高
- `Image`、`ImageDraw`、`ImageFilter`、`ImageFont`、`ImageOps` 等所需模块导入
- 当前安装的全部 hatch-pet Python 脚本可由该解释器编译

探针不会安装包、修改 PATH 或运行生成任务。

找到候选后必须让用户明确同意。记录方式：

```bash
python scripts/project_state.py runtime \
  --project-dir /path/to/project \
  --mode system-verified \
  --python /absolute/path/to/python \
  --python-version 3.13.5 \
  --pillow-version 12.2.0 \
  --consent \
  --next-action "使用已验证本机 Python 准备 hatch-pet 运行目录"
```

之后所有 hatch-pet 脚本必须使用状态中记录的绝对路径。禁止使用裸 `python`，因为 Windows 上 `py`、`python` 和 Anaconda 可能分别指向不同解释器。

兼容模式偏离 `$hatch-pet` 的默认受支持路径。用户未同意时保持阻塞，不把沉默或“继续”解释成兼容授权。

### 3. 无可用候选

列出失败原因。若需要安装 Python 或 Pillow，先征得用户同意；不要静默修改环境。

## 防止恢复死循环

为每个根因记录 `last_blocker` 与重试次数，或至少写入 `next_action`。同一 bundled runtime 缺失在原任务、重启任务或新任务中出现第二次时：

- 不再建议“再重启一次”或“再新建一个任务”
- 直接运行本机运行时探针
- 找到候选则请求兼容授权
- 找不到候选则明确列出真正缺失项

第三方接口场景同时检查图片工具。即使 Python 兼容模式通过，缺少 `image_gen` 时仍不能开始角色定稿。

## 重启后的恢复

依赖修复或重启前确保 `project-state.json` 已保存：

- 项目目录
- 当前阶段
- 已确认检查点
- 参考图片绝对路径
- `$hatch-pet` 运行目录（如已创建）
- 运行时模式、解释器绝对路径、Python/Pillow 版本和兼容授权
- 下一步操作

恢复时读取状态，简短说明“已恢复到角色定稿/动作确认”等，不重复完整开场和已经回答的问题。
