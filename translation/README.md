# 剧本翻译工具说明

本目录提供游戏剧本的**日文→简体中文**翻译流程：从剧本 JSON 中提取对话，调用本地 Sakura 大模型翻译，译文写入 `out/` 目录；游戏运行时从 `out/` 读取并**实时替换**显示内容，无需修改原始剧本。

---

## 一、翻译原理

### 1. 数据来源

- **剧本文件**：位于项目根目录的 `json/` 下，每个剧本一个 JSON 文件（如 `20013 小春－初H.json`）。
- **待译内容**：脚本从每个 JSON 的 `data.code.articles` 中读取**日文原文**（字符串数组），逐条翻译。

### 2. 译文存储

- **输出目录**：`translation/out/`。
- **文件命名**：与剧本一一对应，例如剧本 `20013 小春－初H.json` 对应译文文件 `out/20013 小春－初H.json`。
- **文件格式**：JSON 对象，键为**原文**（经 trim 与去零宽字符处理），值为**译文**，例如：
  ```json
  {
    "こんにちは": "你好",
    "ありがとう": "谢谢"
  }
  ```
- **增量翻译**：已存在的键不会重复请求 API，下次运行会跳过，只翻译新增原文；每翻译满 10 条会自动保存一次，减少中断丢失。

### 3. 游戏侧如何使用译文

- 游戏主程序在**进入某个剧本**时，会加载 `translation/out/{该剧本id}.json` 到内存（`current_translation_cache`）。
- 显示某句台词时：若**语言**设置为「优先译文」，则用当前句子的**原文**（经与翻译脚本一致的 trim 处理）作为 key 查缓存；查到则显示译文，查不到则显示原文。
- 因此：**不修改原始剧本**，只通过 `out/` 下的 JSON 做「原文→译文」的实时替换。

### 4. 翻译服务

- 使用**本地 Sakura 大模型**（兼容 OpenAI 的 `/v1/chat/completions` 接口）。
- 默认地址：`http://127.0.0.1:8080`，模型名：`sakura`。
- 提示词要求：将日文翻译成简体中文，只输出译文，无解释、无多余换行。

---

## 二、环境与依赖

1. **Python 3**（建议 3.7+）。
2. **requests**：  
   ```bash
   pip install -r requirements.txt
   ```
3. **本地 Sakura 服务**：需先在本机启动 Sakura，并保证 `127.0.0.1:8080` 可访问；未启动时运行翻译会提示连接失败。

---

## 三、目录与配置

```
bokusen-pygame/           # 项目根目录
├── json/                 # 剧本 JSON（只读，不修改）
├── config/
│   └── favorites.json    # 喜好角色 id 列表，用于「仅翻译喜好角色」
└── translation/
    ├── translate.py      # 翻译脚本
    ├── check_translation.py  # 校验脚本
    ├── out/              # 译文输出目录（按剧本 id 存 JSON）
    ├── 启动翻译.bat      # 交互选择：1=仅喜好 2=全部
    ├── 翻译全部角色.bat
    ├── 翻译喜好角色.bat
    ├── 校验翻译.bat
    ├── requirements.txt
    └── README.md         # 本说明
```

- **喜好角色**：`config/favorites.json` 中为数字 id 的数组；剧本文件名中若包含该数字（如 `20013`），则视为该角色剧本。`translate.py --favorites` 只处理这些剧本。

---

## 四、操作方式

### 1. 批处理（推荐）

- **启动翻译.bat**  
  在项目根目录执行，会提示输入 `1` 或 `2`：  
  - `1`：仅翻译喜好角色（依赖 `config/favorites.json`）。  
  - `2`：翻译全部角色（`json/` 下所有 JSON）。

- **翻译全部角色.bat**  
  直接执行「翻译全部角色」，等价于 `python translation/translate.py --all`。

- **翻译喜好角色.bat**  
  直接执行「仅翻译喜好角色」，等价于 `python translation/translate.py --favorites`。

- **校验翻译.bat**  
  执行校验脚本，可选 `1`=仅校验喜好 / `2`=校验全部，查看每个剧本的完成率与未译句。

**注意**：上述 bat 会先 `cd` 到项目根目录（即 `bokusen-pygame`），再调用 `translation/translate.py` 或 `translation/check_translation.py`，因此需在**项目根目录**下运行这些 bat。

### 2. 命令行

在项目根目录下执行：

| 命令 | 说明 |
|------|------|
| `python translation/translate.py --favorites` | 仅翻译喜好角色 |
| `python translation/translate.py --all` | 翻译全部角色 |
| `python translation/translate.py --all --dry-run` | 只统计待翻译条数，不请求 API、不写文件 |
| `python translation/check_translation.py --favorites` | 仅校验喜好角色剧本 |
| `python translation/check_translation.py --all` | 校验全部剧本 |
| `python translation/check_translation.py --all -v` | 校验全部，并输出每个剧本未译原文片段（前 50 字） |

---

## 五、校验脚本说明

`check_translation.py` 用于**检查翻译完成度**：

- 对比剧本中的**原文**（`data.code.articles` 经 trim 后的集合）与译文文件 `out/{剧本id}.json` 的 **key**。
- 输出每个剧本的：总句数、已译数、未译数、完成率；以及合计与「未完成剧本」列表。
- 使用 `-v` 时还会打印每个剧本未译原文的前几条片段，便于查漏。

---

## 六、常见问题

1. **无法连接 Sakura**  
   确认本机已启动 Sakura 服务，且地址为 `127.0.0.1:8080`（可在 `translate.py` 顶部修改 `SAKURA_HOST` / `SAKURA_PORT`）。

2. **游戏里没有显示译文**  
   - 确认游戏设置中「语言」为「优先译文」（或等效选项）。  
   - 确认 `translation/out/` 下存在对应剧本 id 的 JSON，且 key 与剧本原文一致（脚本与游戏使用相同的 trim 规则）。

3. **只翻译部分角色**  
   在 `config/favorites.json` 中配置好角色 id，使用「翻译喜好角色」或 `--favorites`。

4. **翻译中断后如何继续**  
   再次运行相同范围的翻译即可；已存在的原文→译文会跳过，只补译新增内容。

---

## 七、小结

| 项目 | 说明 |
|------|------|
| 原文来源 | `json/*.json` 的 `data.code.articles` |
| 译文存放 | `translation/out/{剧本id}.json`，格式 `{"原文": "译文"}` |
| 翻译服务 | 本地 Sakura，默认 `127.0.0.1:8080` |
| 游戏使用 | 按剧本 id 加载 `out/*.json`，显示时用原文 key 查译文并替换 |
| 可选范围 | 全部角色 / 仅喜好角色（`config/favorites.json`） |

按上述方式运行翻译并保证 Sakura 可用后，游戏内选择「优先译文」即可看到中文替换效果。
