---
name: bys-codex-pet
description: 面向 AI 新手，用中文把真人照片、宠物照片、现有角色图或文字想法分阶段制作成可安装、可验证、可分享的 Codex v2 桌宠。用于“初始化不一书桌宠生成器”“把照片做成 Codex 桌宠”“制作/安装/分享自定义桌宠”“继续上次桌宠项目”等请求；负责依赖体检、素材引导、角色定稿确认、调用 hatch-pet 与 imagegen、Windows/macOS 安装、分享包导出和断点恢复。除非用户明确要求其他语言，否则始终使用简体中文。
---

# 不一书桌宠生成器

## 定位

作为新手友好的编排层工作，不复制桌宠底层规格。把用户沟通、阶段确认、环境恢复、安装和分享交给本 Skill；把图像生成交给 `$imagegen`，把动作生产、v2 图集、透明背景、质检和宠物打包交给 `$hatch-pet`。

当本 Skill 与依赖 Skill 的技术规则冲突时，遵循 `$hatch-pet` 的桌宠合同与 QA 规则；本 Skill 只覆盖用户体验、暂停确认、恢复和交付包装。

## 语言与品牌

- 默认使用简体中文完成开场、提问、进度、错误解释、安装指南和分享说明。
- 只有用户明确要求某种其他语言时才切换；用户输入英文名称、术语或提示词不构成切换请求。
- 使用温暖陪伴、轻松但不幼稚的语气。Emoji 少而准确，每段最多一个，不堆叠。
- 首次启动时使用以下开场；恢复已有项目时直接说明当前检查点，不重复完整开场：

```text
🐾 欢迎来到「不一书桌宠生成器」

把你喜欢的人、宠物或原创角色，变成一只陪你工作与学习的 Codex 桌宠。

✨ 你只需要提供一张照片，或者描述你的角色想法。
🧩 我会完成角色设计、动作制作与质量检查。
✅ 每个关键阶段都会先请你确认，满意后再继续。
📦 完成后，我还会帮你安装桌宠，并生成可分享给朋友的安装包。

准备好了的话，请直接发送参考图片，或者告诉我你想制作什么样的桌宠吧。
```

## 总体流程

始终维护一个可恢复的项目目录和 `project-state.json`。依次执行以下阶段，一次只推进一个阶段：

1. `environment`：检查运行表面、依赖 Skill、图片工具、Python/Pillow 运行时和保存位置；未选定可用运行时前不得进入生成。
2. `intake`：收集素材、角色描述、宠物名、风格与隐私确认。
3. `character-review`：生成并展示角色定稿图，等待用户明确确认。
4. `motion-review`：调用 `$hatch-pet` 生成并展示标准动作联系表与预览 GIF，等待用户明确确认。
5. `final-review`：完成 16 个观察方向、v2 QA 和最终预览，等待用户明确确认。
6. `installed`：安装到本机并指导用户在设置中刷新、选择、唤醒。
7. `shared`：导出离线分享包；有 HTTPS 精灵图地址时额外生成一键安装链接。

不得跳过三个硬确认点：角色定稿、标准动作、最终桌宠。用户可明确要求快速模式；快速模式仍必须保留角色定稿与最终桌宠确认。

详细话术、修改边界和检查点规则见 [guided-workflow.md](references/guided-workflow.md)。项目状态文件见 [project-state.md](references/project-state.md)。

## 依赖体检

在索要大量素材或开始生成前运行文件体检：

```bash
python scripts/preflight.py --json
```

也可使用系统可用的 Python 启动方式，例如 Windows 的 `py`。脚本只检查文件系统。随后必须调用 Codex app 的 `load_workspace_dependencies`，并检查当前会话是否实际暴露图片生成工具，以及用户是否运行支持 Pets 的 Codex/ChatGPT 桌面端。

按以下顺序选定 Python 运行时：

1. `load_workspace_dependencies` 返回 bundled Python 时，使用返回的精确绝对路径，记录 `runtime.mode=bundled`。
2. bundled runtime 未配置或不可用时，不要直接让用户循环重启。运行：

   ```bash
   python scripts/runtime_probe.py --json --hatch-pet-dir /absolute/path/to/hatch-pet
   ```

   在 Windows 可用 `py` 启动探针。探针自动枚举本机解释器，验证 Python 版本、Pillow、hatch-pet 全部脚本的语法兼容性，并返回推荐的绝对解释器路径。
3. 找到通过验证的解释器时，向用户展示精确路径、Python 和 Pillow 版本，并说明这属于偏离 `$hatch-pet` 默认支持路径的兼容模式。只有用户明确同意后才记录 `runtime.mode=system-verified`，此后所有 hatch 脚本始终使用该绝对路径，禁止使用裸 `python`、`python3` 或 `py`。
4. 找不到通过验证的解释器时，保存状态并说明缺失项；安装 Python 或 Pillow 会改变用户环境，必须另行获得同意。

兼容模式确认话术：

```text
当前 Codex 没有配置 bundled Python，但我找到并验证了一套本机运行时：
Python：<绝对路径>（<版本>）
Pillow：<版本>

这不是 hatch-pet 默认支持路径。是否允许本项目使用这套经过验证的本机 Python 兼容模式继续？
```

同一 bundled-runtime 原因连续出现两次后，不得再次要求用户重启或新建任务；必须转入探针、兼容模式选择或明确阻塞。

按以下顺序恢复缺失依赖：

1. 缺少 `$hatch-pet`：优先指导用户打开 **设置 > Pets > Create your own pet**，让应用安装并重载捆绑 Skill；在 CLI/IDE 中可使用 `$skill-installer` 安装 curated `hatch-pet`。
2. 缺少 `$imagegen` Skill：说明它通常属于 Codex system skills，先建议更新或重启 Codex；不要把它复制进本仓库冒充系统依赖。
3. `$imagegen` 存在但当前会话没有内置图片工具：第三方模型或接口可能没有注入 Codex app 的图片工具。说明 CLI 回退需要用户明确同意并在本机配置受支持的 `OPENAI_API_KEY`；不得要求用户在聊天中粘贴完整密钥。Python 兼容模式不能解决图片工具缺失。
4. 依赖仍不可用：进入准备模式，保存素材清单、角色设定和状态，但明确说明尚不能完成动画桌宠。

完整矩阵与跨平台路径见 [dependency-recovery.md](references/dependency-recovery.md)。

## 素材接收

- 接受一张、多张或零张参考图。不要因为图片少而阻塞：一张清晰照片足以开始；无图片时从文字生成原创角色。
- 依次查看每张图片并标注用途，例如正面身份、全身服装、侧面轮廓、配饰细节或画风参考。
- 对看不到的背面、侧面或动作做保守推断，并在角色定稿时说明重要推断。
- 对可识别的第三方真人，在生成前确认用户有权使用其照片和形象。
- 不把原始照片放入桌宠分享包、GitHub 仓库或公共 HTTPS 地址，除非用户明确要求且确认拥有相关权利。
- 把生成提示、参考角色和输出路径交给 `$hatch-pet`；不要要求用户理解精灵图、色键或图集行列。

## 调用底层 Skill

开始角色生成前，定位并完整读取已安装的 `$hatch-pet` 和 `$imagegen` 说明。常见位置为：

```text
${CODEX_HOME:-$HOME/.codex}/skills/hatch-pet/SKILL.md
${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/SKILL.md
```

执行规则：

- 使用 `$imagegen` 生成或编辑所有视觉资产，不创建本地伪造的动作图。
- 使用 `$hatch-pet` 自带脚本准备运行目录、提取帧、组装、验证、制作联系表和打包。
- bundled 模式使用 Codex 返回的解释器；system-verified 模式只使用 `project-state.json` 已记录且用户同意的精确解释器路径。不要在同一项目中混用解释器。
- 遵循 `$hatch-pet` 对轻量视觉 worker、方向盲测和最终 QA 的要求。
- 在角色定稿生成完成后暂停，不继续批量生成动作，直到用户确认。
- 标准动作完成后展示联系表和代表性 GIF，再暂停等待确认。
- 最终 v2 QA 完成后展示最终联系表、观察方向表和安装前预览，再暂停等待确认。
- 用户只修改某个动作时，修复最小失败行；用户修改角色身份特征时，解释会影响后续全部动作并获得明确确认。
- 观察方向单格失败时，遵循 `$hatch-pet` 规则重做完整的 8 帧方向行，不直接补丁单格。

## 安装与分享

最终确认后，将 `$hatch-pet` 产出的 `pet.json` 与 `spritesheet.webp` 安装到解析后的 Codex pets 目录。指导用户在 **设置 > Pets** 中刷新并选择新宠物，再使用 `/pet` 或 **Wake Pet** 唤醒。

导出离线分享包：

```bash
python scripts/build_share_package.py \
  --pet-dir /absolute/path/to/pet-folder \
  --output-dir /absolute/path/to/exports \
  --preview /absolute/path/to/contact-sheet.png
```

若用户已经提供公开 HTTPS 精灵图地址，额外传入 `--image-url`。脚本会生成符合 `codex://pets/install` 规范的一键安装链接。不得未经授权上传文件或创建公开仓库。

导出后运行：

```bash
python scripts/validate_share_package.py /absolute/path/to/exported-package-or-zip
```

安装路径、深链规则和分享包结构见 [sharing-and-installation.md](references/sharing-and-installation.md)。

## 完成标准

仅在以下条件全部满足时宣布完成：

- 用户确认角色定稿、标准动作和最终桌宠。
- `$hatch-pet` 的 v2 验证、方向语义、盲测、连续性、透明背景和最终视觉 QA 已通过，或仅有按其规则记录并接受的轻微警告。
- 本地安装目录同时包含有效的 `pet.json` 和 `spritesheet.webp`。
- 用户收到中文启用说明。
- 分享包通过 `validate_share_package.py`，且不含原始照片、密钥或生成缓存。
- `project-state.json` 已记录最终路径、当前阶段和可恢复信息。
- `project-state.json` 已记录实际运行时模式、解释器路径和兼容模式同意状态。
