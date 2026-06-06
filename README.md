# AI 同声传译助手

一个面向英语及其他外语演讲、技术分享、国际会议和网课场景的实时同声传译助手。

通过 AI 能力将单向音频流实时翻译成中文，并以字幕或语音形式呈现，帮助用户降低语言门槛、提升信息获取效率。

## 特性

- 实时麦克风音频采集与 WebSocket 传输
- 流式字幕展示与修正
- ASR / 翻译 / TTS 可切换 provider
- Whisper 本地识别支持
- DeepSeek 翻译支持
- OpenAI 兼容翻译与语音合成支持
- 字幕版本记录与回滚
- 术语库管理与上下文记忆
- 数据库持久化
- 浏览器端自动播报
- 多页面前端结构

## 页面

- `Dashboard`：项目总览
- `Live`：实时传译工作台
- `Glossary`：术语库管理
- `Corrections`：字幕修正与历史
- `Settings`：ASR / 翻译 / TTS 配置

## 技术栈

- **Frontend**：React + TypeScript + Vite
- **Backend**：FastAPI + WebSocket
- **Database**：SQLite + SQLAlchemy
- **AI**：Whisper / DeepSeek / OpenAI 兼容翻译与 TTS / 浏览器语音播报

## 快速开始

### 1. 复制环境变量

```bash
cp .env.example .env
```

### 2. 启动后端

```bash
cd backend
uvicorn app.main:app --reload
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 打开应用

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- WebSocket：`ws://localhost:8000/api/v1/transcripts/ws/demo-session`

## 环境变量

主要配置项：

- `DATABASE_URL`
- `ASR_PROVIDER`
- `TRANSLATION_PROVIDER`
- `TTS_PROVIDER`
- `OPENAI_API_KEY`
- `OPENAI_TRANSLATION_MODEL`
- `OPENAI_TTS_MODEL`
- `OPENAI_TTS_VOICE`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL`
- `DEEPSEEK_BASE_URL`
- `WHISPER_MODEL`
- `WHISPER_DEVICE`
- `WHISPER_COMPUTE_TYPE`

详见 `.env.example`。

## WebSocket 消息

### 客户端发送

- `start_demo`
- `start_audio`
- `stop_audio`
- `rollback`
- 二进制音频块

### 服务端发送

- `status`
- `audio`
- `chunk`
- `revision`
- `translated`
- `correction`

## 项目亮点

- 支持实时同声传译核心链路
- 具备术语库与上下文记忆
- 支持字幕自动修正与回滚
- 可通过 provider 切换接入真实模型
- 适合演示、扩展与进一步产品化

## 说明

当前项目已经具备完整的产品原型结构，可用于演示和后续接入真实 AI 服务。

## 后续计划

- 更稳定的音频转码与分片处理
- 更智能的字幕修正策略
- 更强的术语库检索增强
- 更细粒度的历史版本对比与回放
- 更完整的生产级 provider 接入
