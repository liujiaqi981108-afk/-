# 9-Agent 影视级 AI 短视频制片厂 (本地 Chrome 挂载 Google Flow / Nano Banana 零 API Key 全流程版)

一套从**一句话戏剧创意**直达 **`H.264 + 44.1kHz Stereo AAC` 电影级成片 (`final_master.mp4`)** 的工业化 9-Agent 协同短视频制片厂。

核心亮点：**支持在你自己的本地电脑（Windows / macOS / Linux）上免 API Key 部署运行**——通过 Playwright CDP 挂载你本机已登录 Google 账号的专属 Chrome 浏览器窗口，直接驱动网页版 **Google Flow (`labs.google/fx/tools/flow`)** 内置的 **Nano Banana**（带角色三视图+场景母版参考垫图文生图）与 **`Video > Frames` (`Omni Flash 1.2` / `Veo`)**（单起始帧 I2V + 首尾双关键帧插值 KF2V + 原生音效），配合本地 `edge-tts` 中文神经配音、四轨材质拟音与 `PyAV` 手术刀黄金帧剪辑自动合片！

---

## 🚀 三步在本地电脑免 API Key 跑起来

### 第一步：克隆仓库并安装依赖

确保本机已安装 **Python 3.11+** 与 **Google Chrome** 浏览器：

```bash
git clone https://github.com/liujiaqi981108-afk/-.git
cd -

python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1

pip install -e . pytest pytest-asyncio
```

### 第二步：一键启动专属 Chrome (CDP 9222) + 9-Agent 制片厂服务

直接运行内置的一键启动脚本：

```bash
python scripts/start_flow_studio.py
```

启动后会自动完成两件事：
1. **弹出一个独立的本地 Chrome 窗口**（端口 `127.0.0.1:9222`，登录数据保存在项目目录下的 `.chrome_flow_profile/` 中，与你平时用的浏览器互不干扰）。**首次启动时，请在该 Chrome 窗口手动登录你的 Google 账号并进入 `https://labs.google/fx/tools/flow` 页面**（以后重启自动免登录！）。
2. 启动本地制片厂后台并自动将生图 (`image_vendor`) 与生视频 (`video_vendor`) 挂载为 `flow_browser`。

> 💡 也可以分两步手动启动：
> 1. `python scripts/launch_local_chrome.py` （单独拉起 9222 端口 Chrome）
> 2. `uvicorn app.main:app --host 127.0.0.1 --port 8000`

### 第三步：打开本机工作台开始制片

在本机浏览器打开 **`http://127.0.0.1:8000`**：

1. 点击右上角 **「🌐 挂载本地 Google Flow」**（或在「模型与本地浏览器配置」里点击 **「🔍 检测本地 Chrome 9222 连接」** 确认绿灯连通）；
2. 在左侧输入一句话创意，点击 **「开机立项 · 启动 9-Agent 协同」**：
   - **关卡 1**：`01 总导演` + `02 剧作总监` + `03 分镜导演` 生成五幕色彩总谱、潜台词对白（`<=11`字）与 `24fps` 帧级 `6W1H` 分镜表；
   - **关卡 2**：`04 美术总监` + `08 声线总监` 生成 **`1440x960` 角色正/侧/背标准正交三视图**、契诃夫随身道具双状态卡、五维声学基因卡与 **三维罗盘无人空镜母版**；
   - **关卡 3**：`05 防穿模生图师` 自动携带角色三视图与空镜母版作为参考垫图生成单/双关键帧，`06 作画监督` 执行三图并置质检与自动自愈重抽；
   - **Phase 2 真视频渲染 & 成片放映室（`07` 标签页）**：
     - **自动模式**：点击 **「🚀 一键渲染全片视频并压制成片」**，`07 物理运镜总监` 将自动操控本地 Chrome 的 Google Flow `Video > Frames` 上传首帧（及高潮镜尾帧）、填入英文原生动态与原声指令、自动捕获 `.mp4` 片段；
     - **半自动精修兜底**：随时可在 `07` 放映室复制每镜专属 Google Flow 英文提示词，或点击 **「📤 手动上传 Flow `.mp4`」** 拖入你手动挑选的最佳视频片段；
     - **母带合成**：`08 声线总监`（`edge-tts` 中文神经配音 + 空间混响 + 180°背身闷音滤波 + 帧同步金属/银铃拟音 + 暴风雨前 `Music Drop` + `-7.5dB` 侧链闪避）与 `09 剪辑总监`（`PyAV` 手术刀黄金帧裁剪 + 高潮非线性曲线变速 + 35mm 胶片颗粒缝合 + `9:16` 底部黄金安全区字幕）一键输出 `final_master.mp4`！

---

## 🏛️ 9-Agent 工业级职责矩阵

| 编号 | Agent 模块 | 核心工程机制 |
| :--- | :--- | :--- |
| **01** | `DirectorOrchestratorAgent` (`app/agents/director.py`) | 视觉介质锁、五幕色彩总谱、`9:16` 底部 `20%` 净空戒律、不可逆场记连续性总账本、跨部门冲突裁决、穿模三级借位改戏熔断 |
| **02** | `StoryStrategistAgent` (`app/agents/story_strategist.py`) | 高概念认知反差、`0.8s` 异常钩子 + 3-5s 微钩子接力、冰山人物双层驱动、反 AI 套话审查（`<=11`字潜台词）、契诃夫信物三幕回收 |
| **03** | `StoryboardDirectorAgent` (`app/agents/storyboard_director.py`) | 非均等心跳时长波形、四维包络定长公式、`>5.0s` 蒙太奇自动拆镜、`24fps` 起/中/落微时间轴、单首帧 vs 首尾双关键帧动态决策 |
| **04** | `ArtDirectorAgent` (`app/agents/art_director.py`) | `1440x960` 正/侧/背正交角色三视图、配饰左右耳/腕锁死与可见朝向、随身物常驻/手持双态卡、东南西北三维罗盘空镜母版 |
| **05** | `StoryboardArtistAgent` (`app/agents/storyboard_artist.py`) | 按视角动态切片身份锚点（严禁背面画正脸）、双人同框左右分仓防串色、接地阴影、握持分离防穿模、多参考垫图文生图 |
| **06** | `VisualCriticAgent` (`app/agents/visual_critic.py`) | `[角色三视图 + 场景母版 + 分镜成图]` 三图并置交叉质检、12 项穿模缺陷清单、分级自愈处方、连环画拼条连续性核验 |
| **07** | `MotionDirectorAgent` (`app/agents/motion_director.py`) | `I2V / KF2V` 路由、Google Flow 英文原生动态提示词、眼先动 + 4-8帧配饰钟摆滞后惯性、高速动作稳机位铁律、刚体防弯曲锁 |
| **08** | `VoiceAndSoundDirectorAgent` (`app/agents/voice_director.py`) | 五维声学基因锁、`edge-tts` 中文神经语音、句中潜台词停顿、木堂混响与背身闷音、帧同步拟音、跨切镜风雪底噪与 `Music Drop` |
| **09** | `MasterEditorAgent` (`app/agents/master_editor.py`) | `PyAV` 黄金帧裁剪、高潮非线性变速、Google Flow 原生音轨融合、35mm 胶片颗粒统一、`<=11`字黄金安全区字幕压制成片 |

---

## 🛠️ 选择器热更新与安全合规说明

- **Google Flow 页面选择器外置**：所有按钮与输入框候选选择器均独立存放在 `app/providers/flow_selectors.json`，如 Google Labs 微调网页文案，直接编辑该 JSON 即可，无需改动 Python 源码。
- **严格安全与人工接管边界**：`app/providers/flow_browser.py` 仅复用你在本地可见 Chrome 窗口中的正常登录会话；一旦检测到未登录或任何安全验证组件，驱动会**立即安全暂停**并在工作台提示你在 Chrome 窗口手动确认，绝不执行任何绕过或自动点击验证操作。

---

## 🧪 自动化测试与命令行批处理

```bash
# 运行全套 Phase 1 + Phase 2 + Flow CDP 驱动单元测试与端到端合成验证
pytest -v

# 命令行全自动一镜到底生成 Phase 1 + Phase 2 成片 (.mp4)
python cli.py --topic "暴风雪夜边关古驿站，红衣侠女拔出油纸伞中细剑劈飞暗器" --phase2
```