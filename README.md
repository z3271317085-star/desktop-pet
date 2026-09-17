# 🐾 轻量化桌面互动伴侣客户端 (Desktop Pet)

基于 **Python** 与 **PySide6 (Qt6)** 打造的高性能、沉浸式桌面交互宠物伴侣应用。支持 Windows 桌面无边框异形透明渲染、拟真重力模拟、边缘碰撞感知、多状态有限状态机（FSM）动作管理以及自主漫步 AI。

---

## ✨ 核心特性

- 🖥️ **硬件加速异形透明浮窗**：
  - 基于 PySide6 实现无系统边框、无系统阴影、支持 Alpha 通道半透明与全透明像素渲染；
  - 底层重写绘图刷新事件，每次重绘前清空 Windows DWM 分层显存缓冲区，彻底杜绝传统异形浮窗拖动时的多帧重叠、残影与边缘闪烁撕裂。
- 🎭 **多状态有限状态机（FSM）与动作序列**：
  - 内置 9 组精细化动作状态序列：
    - `idle`：静息待机与轻柔呼吸动效
    - `running-left` / `running-right`：左右方向巡航奔跑
    - `waving`：举手打招呼互动
    - `jumping`：腾空与滞空动作
    - `failed`：失重下落撞击地面后的短暂眩晕与受挫动效
    - `waiting`：趴卧打盹与休息
    - `running`：欢呼雀跃跳跃
    - `review`：驻足认真巡检
- 🌍 **重力模拟与物理碰撞引擎**：
  - 支持鼠标左键抓起提空，宠物随拖拽方向呈现挣扎或奔跑状态；
  - 释放鼠标后受重力加速度自然下落，撞击 Windows 任务栏或屏幕底边后触发落地反馈并回归待机；
  - 自动识别多显示器与当前主屏幕工作区边界，自适应转向与防止越界。
- 💬 **静谧陪伴与动态台词气泡**：
  - 双击或右键呼出对话气泡，支持从外部 `dialogues.txt` 自由扩充台词库；
  - 彻底去除声音音频干扰，安静陪伴，适合办公、自习与编码场景。
- 🚀 **双模运行支持**：
  - **免环境直接运行**：提供编译打包好的独立可执行程序 `dist/JiRuxue_Pet.exe`，双击即开，无需安装 Python 环境；
  - **源码可定制**：完整的 Python 脚本与资产配置文件，易于二次开发与扩充。

---

## 🎮 操作与交互指南

| 操作手势 / 动作 | 触发行为与效果 |
| :--- | :--- |
| **鼠标左键 单击/按住拖拽** | 抓起宠物在屏幕任意位置移动；左右拖动会触发奔跑朝向变化 |
| **鼠标左键 释放** | 宠物处于半空时激活重力下落引擎，下落至任务栏底边并触发落地表情 |
| **鼠标左键 双击** | 随机触发趣味互动（挥手打招呼、欢呼跳跃、趴下休息、文字对话等） |
| **鼠标右键 单击** | 唤起快捷上下文菜单：<br>• **打个招呼**：立刻播放挥手动效<br>• **跟我说话**：随机展示一句台词气泡<br>• **让它乱跑**：立即激活自主漫步模式奔跑一段距离<br>• **退出**：安全关闭气泡与主窗口程序 |

---

## 📂 项目目录结构

```text
desktop-pet/
├── pet_player.py               # 核心主程序（PySide6 状态机与交互控制器）
├── dialogues.txt               # 外部台词文本库（可自由新增/修改台词）
├── README.md                   # 完整使用与开发说明文档
├── LICENSE                     # 开源协议
├── dist/                       # 发行包与独立运行资源
│   ├── pet.exe                 # ★ 独立单文件可执行程序（双击直接运行）
│   ├── dialogues.txt           # 发行目录配套台词
│   └── model/                  # 角色模型与动画资产包
│       ├── pet.json            # 动作帧数、行列与尺寸布局配置
│       ├── spritesheet.png     # 高清动画精灵图
│       └── spritesheet.webp    # 高压缩比 WebP 动画精灵图
└── run/                        # 动作原始序列帧与参考资产
    ├── decoded/                # 动作拆解图集
    ├── frames_miaojiang/       # 各状态分帧切片序列
    └── references/             # 角色设定参考
```

---

## 🚀 启动与使用方式

### 方式一：独立 Exe 双击即用（推荐，无需 Python）
进入 `dist/` 文件夹，直接双击运行：
```text
dist/pet.exe
```

### 方式二：Python 源码运行

1. **环境依赖**：
   - Python 3.10+
   - PySide6 (`pip install PySide6`)
   - Pillow (`pip install Pillow`)

2. **启动命令**：
   ```bash
   python pet_player.py
   ```

---

## 🛠️ 自定义与二次开发

### 1. 修改或增加台词
直接编辑根目录或 `dist/` 下的 `dialogues.txt`，每行写一句您喜欢的对话内容，保存后重启宠物即可生效：
```text
你在写代码吗？我帮你看着呢。
今天也要元气满满！
遇事可智取，不必一味死拼。
久坐伤身，起身活动片刻。
```

### 2. 重新编译打包 EXE
若对 `pet_player.py` 进行了代码修改，可使用 `PyInstaller` 重新编译生成单文件程序：
```bash
pyinstaller --clean --noconfirm --onefile --windowed --name pet \
  --add-data "dist\model\pet.json;dist\model" \
  --add-data "dist\model\spritesheet.webp;dist\model" \
  --add-data "dist\model\spritesheet.png;dist\model" \
  --add-data "dist\dialogues.txt;dist" pet_player.py
```
编译产物将自动输出至 `dist/pet.exe`。

---

## 📄 开源许可证

本项目基于 [MIT 许可证](LICENSE) 开源。
