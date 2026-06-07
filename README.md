# AI 同声传译助手 2.0

一个面向英语及其他外语演讲、技术分享、国际会议和网课场景的实时 AI 同声传译助手。

系统通过 AI 能力将单向音频流实时识别、翻译成中文，并以字幕或语音形式呈现，帮助用户降低语言门槛，提升信息获取效率。2.0 版本在原有实时传译原型基础上，进一步增强了自动纠错、会话持久化、字幕导出和历史归档能力，更接近可落地的商用产品形态。

## 2.0 版本更新

- 新增 AI 自动纠错引擎。
- 新增低置信度片段二次翻译修订。
- 新增字幕 revision 修订链路和 correction 推送。
- 新增会话字幕持久化到 SQLite。
- 新增历史会话页面。
- 新增会话字幕导出：`TXT` / `SRT` / `JSON`。
- 新增前端纠错次数统计和纠错原因展示。
- 增强术语库与自动纠错联动。
- 增强 README、接口和商用化说明。

## AI 能力体现

本项目中的 AI 不只是简单调用翻译接口，而是体现在完整的实时同传链路中：

1. **语音识别 ASR**
   - 将用户输入的英语或其他外语音频实时转成文本。
   - 可通过 provider 切换 Mock、Whisper、Qwen 等识别服务。

2. **机器翻译**
   - 将识别文本实时翻译成中文。
   - 支持 OpenAI 兼容翻译 provider。
   - 支持结合上下文和术语库提升翻译一致性。

3. **自动纠错**
   - 对 ASR 识别结果和翻译结果进行二次修正。
   - 自动清理口语噪声、重复词和常见识别混淆。
   - 对低置信度识别片段触发二次翻译。
   - 根据术语库修正专业名词一致性。

4. **语音播报 TTS**
   - 支持将中文译文通过浏览器或后端 TTS provider 播报。
   - 适合字幕和语音双通道输出场景。

5. **上下文记忆**
   - 系统会记录当前会话上下文。
   - 后续可用于翻译一致性、术语增强和语义级纠错。

## 核心功能

- 实时麦克风音频采集。
- WebSocket 二进制音频流传输。
- 实时原文字幕展示。
- 实时中文译文展示。
- 浏览器端自动语音播报。
- ASR / 翻译 / TTS provider 可切换。
- 字幕版本记录与回滚。
- AI 自动纠错与 correction 推送。
- 术语库管理。
- 历史会话归档。
- 字幕导出 `TXT` / `SRT` / `JSON`。
- SQLite 数据库持久化。
- 多页面前端工作台。

## 自动纠错机制

2.0 版本已经实现自动纠错升级。自动纠错流程如下：

1. ASR provider 返回识别结果。
2. 系统根据是否 final、置信度和 revision 生成字幕版本。
3. 最终字幕进入翻译流程。
4. 翻译完成后进入自动纠错引擎。
5. 自动纠错引擎检查：
   - 口语填充词，例如 `um`、`uh`、`you know`。
   - 重复词。
   - 常见识别混淆，例如 `open ai` → `OpenAI`。
   - 术语库命中但译文未体现的情况。
   - 低置信度片段。
6. 如果发现可修正内容，系统生成新的 revision。
7. 后端通过 WebSocket 推送 `correction` 消息。
8. 前端更新字幕，并显示“AI 已自动纠错”和纠错原因。

当前支持的典型识别混淆包括：

- `open ai` → `OpenAI`
- `chat g p t` → `ChatGPT`
- `web socket` → `WebSocket`
- `fast api` → `FastAPI`
- `type script` → `TypeScript`
- `java script` → `JavaScript`
- `kubernetees` → `Kubernetes`

## 商用化能力

当前项目已经从单纯演示原型增强为更接近商用产品的版本，主要体现在：

- **会话持久化**：最终字幕会保存到 SQLite 数据库。
- **历史归档**：前端提供“历史会话”页面，可以查看过往传译记录。
- **字幕导出**：支持按会话导出 `TXT`、`SRT`、`JSON`。
- **纠错审计**：自动纠错结果会保存 revision、纠错标记和纠错原因。
- **配置化 provider**：ASR、翻译、TTS 均支持通过配置切换。
- **前后端分离**：便于后续部署、扩展和接入真实云服务。
- **可扩展架构**：后续可以继续接入用户系统、权限、计费和生产级监控。

## 页面说明

- `Live`：实时传译工作台，负责录音、字幕、译文、播报、纠错提示和导出。
- `Settings`：模型设置页面，用于配置 ASR / 翻译 / TTS provider。
- `Glossary`：术语库管理页面，用于维护专业词汇翻译。
- `Corrections`：字幕修正页面，用于查看和管理修订记录。
- `Sessions`：历史会话页面，用于查看归档字幕和导出文件。
- `Dashboard`：项目概览页面，用于展示系统状态和能力说明。

## 技术栈

- **Frontend**：React + TypeScript + Vite
- **Backend**：FastAPI + WebSocket
- **Database**：SQLite + SQLAlchemy
- **AI Provider**：Whisper / OpenAI 兼容翻译 / OpenAI 兼容 TTS / Qwen ASR / Mock Provider
- **Audio**：Web Audio API + PCM16 Worklet
- **Transport**：HTTP API + WebSocket

## 快速开始

### 1. 安装后端依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量文件：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

如果当前项目中没有根目录 `.env.example`，可以参考 `frontend/.env.example` 和 README 的环境变量说明自行创建 `.env`。

### 3. 启动后端

```bash
cd backend
uvicorn app.main:app --reload
```


### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

## 环境变量

主要配置项：

- `DATABASE_URL`：数据库地址，默认可使用 SQLite。
- `ASR_PROVIDER`：语音识别 provider。
- `TRANSLATION_PROVIDER`：翻译 provider。
- `TTS_PROVIDER`：语音合成 provider。
- `OPENAI_API_KEY`：OpenAI 兼容服务 API Key。
- `OPENAI_TRANSLATION_MODEL`：翻译模型。
- `OPENAI_TTS_MODEL`：TTS 模型。
- `OPENAI_TTS_VOICE`：TTS 音色。
- `WHISPER_MODEL`：Whisper 模型名称。
- `WHISPER_DEVICE`：Whisper 运行设备。
- `WHISPER_COMPUTE_TYPE`：Whisper 计算类型。
- `AUTO_CORRECTION_ENABLED`：是否启用自动纠错，默认 `true`。
- `AUTO_CORRECTION_MIN_CONFIDENCE`：低置信度二次校正阈值，默认 `0.68`。
- `MIN_TRANSLATE_CHARS`：触发翻译的最小缓冲字符数。
- `MAX_TRANSLATE_BUFFER_SECONDS`：最大缓冲时间。
- `TRANSLATION_TIMEOUT_SECONDS`：翻译超时时间。

## WebSocket 消息

### 客户端发送

- `start_demo`：启动演示流。
- `start_audio`：开始真实音频采集。
- `stop_audio`：停止真实音频采集。
- `rollback`：回滚指定字幕版本。
- 二进制音频块：实时麦克风 PCM 音频数据。

### 服务端发送

- `status`：连接和流程状态。
- `audio`：音频采集状态。
- `source_partial`：临时原文识别结果。
- `source_final`：最终原文识别结果。
- `chunk`：字幕片段。
- `revision`：字幕修订版本。
- `translated`：翻译结果。
- `correction`：自动纠错或手动回滚事件。
- `error`：链路错误信息。

## HTTP API

常用接口：

- `GET /api/v1/health`
- `GET /api/v1/settings`
- `PUT /api/v1/settings`
- `GET /api/v1/glossary`
- `POST /api/v1/glossary`
- `PUT /api/v1/glossary/{source}`
- `DELETE /api/v1/glossary/{source}`
- `GET /api/v1/transcripts/latest`
- `GET /api/v1/transcripts/sessions`
- `GET /api/v1/transcripts/sessions/{session_id}/chunks`
- `GET /api/v1/transcripts/sessions/{session_id}/export?format=txt`
- `GET /api/v1/transcripts/sessions/{session_id}/export?format=srt`
- `GET /api/v1/transcripts/sessions/{session_id}/export?format=json`

## 项目亮点

- 覆盖实时同声传译核心链路。
- 支持识别、翻译、纠错、播报全流程。
- 具备术语库和上下文记忆。
- 支持字幕自动修正、revision 记录和回滚。
- 支持历史会话归档和字幕导出。
- 支持 provider 扩展，便于接入真实 AI 服务。
- 适合课程项目、比赛演示和后续产品化扩展。

## 当前完成度

当前版本已经具备：

- 可运行的前后端工作台。
- 实时 WebSocket 音频链路。
- 实时字幕和翻译展示。
- AI 自动纠错基础能力。
- 会话级字幕持久化。
- 历史会话查询。
- 字幕导出能力。
- 术语库管理。
- 模型 provider 配置。

如果用于课程设计或比赛答辩，已经可以完整展示 AI 同声传译助手的核心价值。

如果用于真实商用部署，还建议继续补充生产级能力。

## 后续计划

- 接入更稳定的生产级流式 ASR。
- 增加 VAD 静音检测和智能断句。
- 增加用户登录和多用户隔离。
- 增加 API 鉴权和访问权限控制。
- 增加 Docker / docker-compose 部署。
- 增加 HTTPS / WSS 部署方案。
- 增加更精确的 SRT 时间戳。
- 增加语义级大模型自动纠错。
- 增加字幕版本差异对比。
- 增加生产级日志、监控和错误追踪。
