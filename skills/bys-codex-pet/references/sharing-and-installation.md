# Windows、macOS 安装与分享

## 目录

- 宠物文件合同
- 本地安装
- 应用内启用
- 离线分享包
- 一键安装链接
- 安全边界

## 宠物文件合同

分享的核心宠物目录只包含：

```text
<pet-id>/
  pet.json
  spritesheet.webp
```

新生成桌宠必须使用 `spriteVersionNumber: 2`。实际精灵图规格与验证完全服从当前 `$hatch-pet`，本 Skill 不复制其几何细节。

## 本地安装

安装根目录：

```text
<CODEX_HOME>/pets/<pet-id>
```

未设置 `CODEX_HOME` 时：

```text
Windows: %USERPROFILE%\.codex\pets\<pet-id>
macOS:   ~/.codex/pets/<pet-id>
```

分享包同时提供自动脚本和手动复制说明。安装脚本必须：

- 解析脚本所在目录，不依赖当前终端目录
- 校验源 `pet.json` 和 `spritesheet.webp`
- 只写入目标 `<pet-id>` 目录
- 目标已存在时先停止并提示，除非用户显式传入覆盖参数
- 不读取或输出任何密钥

## 应用内启用

安装后指导：

1. 打开 **设置 > Pets**。
2. 选择 **Refresh**。
3. 选择新宠物。
4. 输入 `/pet` 或选择 **Wake Pet**。

若 Pets 页面不存在，说明当前应用版本或功能入口不支持，不能把文件复制成功等同于启用成功。

## 离线分享包

`build_share_package.py` 输出：

```text
<display-name>-codex-pet/
  pet/
    pet.json
    spritesheet.webp
  preview.png                 # 可选
  安装说明.md
  install-windows.ps1
  install-macos.sh
  uninstall-windows.ps1
  uninstall-macos.sh
  install-link.txt            # 有 HTTPS 地址时
  manifest.json
```

并生成同名 `.zip`。原始照片、`project-state.json`、提示词、QA 缓存、API Key 和 `.env` 不得进入包。

## 一键安装链接

当用户已拥有公开、绝对 HTTPS 精灵图地址时生成：

```text
codex://pets/install?name=<urlencoded-name>&imageUrl=<urlencoded-https-url>&description=<urlencoded-description>&spriteVersionNumber=2
```

仅允许官方参数。`imageUrl` 必须是 HTTPS；不要自行上传或公开用户文件。可建议用户把最终 `spritesheet.webp` 放到其 GitHub Release、对象存储或其他明确授权的 HTTPS 地址。

如果用户没有公网地址，离线 ZIP 是默认分享方式。

## 安全边界

- 不覆盖已安装同名宠物，除非用户明确要求。
- 卸载脚本只允许删除包内清晰记录的单个 `<pet-id>` 目录，并先验证解析后的路径位于 `<CODEX_HOME>/pets` 下。
- 不把用户照片或生成过程文件上传到 GitHub。
- 不把 `OPENAI_API_KEY` 写入安装说明、状态文件、日志或脚本。
- 分享前运行 `validate_share_package.py`。
