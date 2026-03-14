# BOKUSEN — ぼくらの放課後戦争 剧本播放器

基于原仓库进行修改， Pygame 的剧本/视觉小说播放器，可播放项目内剧本 JSON，支持 CG、BGM、音效、文本与翻译切换。

---

## 一、项目简介

- **用途**：读取 `json/` 下的剧本 JSON，按指令驱动 CG、背景、文本、BGM、SE 等，实现剧情播放。
- **运行方式**：Python 直接运行 `bokusen_main.py`，或使用打包后的 `BOKUSEN.exe`。
- **依赖**：Pygame、Pydub、FFmpeg（用于部分音频格式）；翻译功能需本地 Sakura 服务；更新功能需网络。

---

## 二、功能概览

- **剧本列表**
  - 从 `json/` 目录扫描剧本，以网格形式展示；支持分页（按钮 + 鼠标滚轮）。
  - 列表按「收藏优先 + 角色名分组」排序，便于查找。

- **收藏**
  - 右键剧本可收藏/取消收藏，收藏列表保存在 `config/favorites.json`。
  - 收藏项在列表中排在最前；与翻译脚本的「喜好角色」共用该配置。

- **播放**
  - 选中剧本后点击 **Load** 下载资源（若有），点击 **Play** 进入播放。Ctrl 强制快进。
  - 支持 CG、立绘、背景、文本、BGM、音效、简单动画等（见 `指令对照.md`）。

- **语言/翻译**
  - 在 `settings.json` 中可设「语言」：0=仅原文，1=优先译文（无译文则显示原文）。
  - 译文来自 `translation/out/{剧本id}.json`，游戏按「原文→译文」实时替换，不修改原剧本。翻译工具与原理见 **`translation/README.md`**。

- **自动更新**
  - 使用 `BOKUSEN_Update.exe` 可检查并更新：主程序、更新程序自身、附加资源 `extra.rar`；支持单项或全部更新。

---

## 三、目录结构（要点）

```
bokusen-pygame/
├── bokusen_main.py       # 主程序入口
├── settings.json         # 窗口大小、BGM 音量、语言等
├── msgothic.ttc          # 字体（打包时需与 exe 同目录）
├── json/                 # 剧本 JSON（只读）
├── resource/             # 各剧本下载的图片、音频等（按剧本分目录）
├── config/
│   ├── favorites.json    # 收藏/喜好角色 id 列表
│   ├── bgm/              # 菜单 BGM 等
│   └── ui/               # UI 资源（如 love.png）
├── translation/          # 翻译工具与译文
│   ├── README.md         # 翻译原理与操作说明
│   ├── translate.py      # 翻译脚本（Sakura）
│   ├── check_translation.py  # 校验完成度
│   └── out/              # 译文 JSON（游戏从此读取）
├── update_exe.py         # 更新程序源码
├── update_config.json    # 更新用配置（GitHub API 等）
├── build_exe.py          # 主程序打包脚本
├── build_update_exe.py   # 更新程序打包脚本
├── 打包说明.md            # 详细打包步骤
├── 指令对照.md            # 剧本指令与参数说明
└── README.md             # 本说明
```

---

## 四、运行与依赖

- **直接运行（开发）**
  - 安装依赖：`pip install -r requirements.txt`（若存在）；需 Pygame、Pydub，翻译需 `requests`。
  - 确保 `json/` 下有剧本、`settings.json` 存在；可选安装 FFmpeg 以支持 m4a 等格式。
  - 运行：`python bokusen_main.py`。

- **打包后运行**
  - 将 `BOKUSEN.exe` 与 `msgothic.ttc`、`settings.json`、`json/` 等放在同一目录；`resource/` 可在首次 Load 时按需下载。
  - 若使用译文，需有 `translation/out/` 及对应剧本的译文 JSON。

- **FFmpeg**
  - 用于部分音频转换/播放；未安装时相关功能会降级或提示，将 `ffmpeg.exe` 放在 exe 同目录或系统 PATH 即可。

---

## 五、配置说明（settings.json）

- **窗口宽度 / 窗口高度**：主窗口分辨率（非默认分辨率不保证布局完美）。
- **bgm音量**：如 `"80%"`，控制 BGM 音量。
- **语言**：`0` = 仅显示原文，`1` = 优先显示译文（无译文则原文）。

其他键以代码中 `user_setting` 为准。

---

## 六、翻译

- 译文不写回剧本，只存放在 `translation/out/{剧本id}.json`，格式为 `{"原文": "译文"}`。
- 游戏进入剧本时加载对应 `out/*.json`，显示时用原文 key 查译文并替换。
- **完整说明**（原理、环境、操作、校验）：见 **`translation/README.md`**。
- 简要操作：
  - 启动本地 Sakura（默认 `127.0.0.1:8080`）。
  - 使用 `translation/` 下的 bat 或 `translate.py --favorites` / `--all` 进行翻译；用 `check_translation.py` 校验完成度。

---

## 七、更新与发布

- **BOKUSEN_Update.exe**
  - 从 GitHub 最新 Release 检查：主程序 `BOKUSEN.exe`、更新程序自身 `BOKUSEN_Update.exe`、附加资源 `extra.rar`。
  - 先检查三项，若有更新则提供菜单：单项更新（1/2/3）或 4=全部更新，0=退出；若均最新则提示无需更新。
  - 自更新会下载新 exe 并通过批处理替换后重启；`extra.rar` 会先下载到游戏根目录，再尝试解压（需 7-Zip 或 UnRAR，否则提示手动解压）。

- **配置**
  - `update_config.json` 中可配置 GitHub API 地址、目标文件名等；与 `update_exe.py` 一起使用。

---

## 八、打包

- **主程序**：使用 `build_exe.py` 或按 `打包说明.md` 用 PyInstaller 打包 `bokusen_main.py`，输出 `BOKUSEN.exe`。
- **更新程序**：使用 `build_update_exe.py` 打包 `update_exe.py`，输出 `BOKUSEN_Update.exe`，需附带 `update_config.json`。
- 详细步骤、参数、spec 说明见 **`打包说明.md`**。

---

## 九、其他文档

| 文档 | 说明 |
|------|------|
| **translation/README.md** | 翻译原理、环境、操作、校验、常见问题 |
| **打包说明.md** | 主程序/更新程序打包步骤与参数 |
| **指令对照.md** | 剧本指令名、参数个数、示例与备注 |

---

## 十、小结

- **玩**：运行主程序 → 选剧本 → Load（如需）→ Play；在设置中开启「优先译文」可看中文。
- **译**：见 `translation/README.md`；译文放 `translation/out/`，游戏自动读取。
- **更**：用 `BOKUSEN_Update.exe` 检查并更新主程序、更新程序与 extra.rar。
- **包**：见 `打包说明.md` 与 `build_exe.py` / `build_update_exe.py`。

如有问题可先查阅上述分点与对应子文档。
