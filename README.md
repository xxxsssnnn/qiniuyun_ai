# AI 同声传译助手

面向英语及其他外语演讲、技术分享、国际会议和网课场景的实时同声传译助手。

## 项目目标

- 通过 AI 能力将单向音频流实时翻译成中文
- 以字幕或语音形式输出，帮助用户跟上内容节奏
- 支持后续自动纠错与修正

## 当前实现状态

已完成的核心链路：

- 前端麦克风采集
- WebSocket 音频流传输
- 后端会话管理
- ASR 抽象层
- 翻译抽象层
- TTS 抽象层
- 实时字幕展示
- 演示模式
- 字幕修正与版本记录
- 术语库与上下文记忆
- 数据库持久化
- 浏览器端自动播报

当前仍使用模拟 ASR / 翻译 / TTS 作为占位实现，但已保留真实 provider 接入入口，可通过环境变量切换。

## 前端页面拆分

- `Dashboard`：项目总览
- `Live`：实时传译主页面
- `Glossary`：术语库管理
- `Corrections`：字幕修正与历史
- `Settings`：ASR / 翻译 / TTS 配置

当前前端已采用导航式拆分，后续可继续把每个页面拆成独立路由组件。

## 目录结构

```text
backend/
  app/
    api/
      v1/
    core/
    models/
    schemas/
    services/
    main.py
frontend/
  public/
  src/
    components/
    pages/
    services/
    styles/
```

## 启动方式

### 后端

```bash
cd backend
uvicorn app.main:app --reload
```

后端默认地址：

- HTTP: `http://localhost:8000`
- WebSocket: `ws://localhost:8000/api/v1/transcripts/ws/demo-session`

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：

- `http://localhost:5173`

## 前后端通信

### WebSocket 消息类型

- `start_demo`：启动演示字幕流
- `start_audio`：开始音频采集会话
- `stop_audio`：停止音频采集会话
- 二进制音频块：发送麦克风录音数据
- `chunk`：字幕草稿
- `revision`：字幕修正版
- `translated`：翻译结果
- `audio`：音频状态/统计消息
- `status`：连接状态
- `correction`：字幕修正事件
- `rollback`：请求回滚到某个修订版本

## ASR 配置

当前默认使用 mock ASR。可以通过环境变量切换：

```bash
ASR_PROVIDER=whisper
```

如果启用 Whisper provider，系统会优先尝试：

1. `openai-whisper`
2. `faster-whisper`

默认模型名：

```bash
WHISPER_MODEL=base
```

可选运行环境：

```bash
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

如果 Whisper 或模型加载失败，会自动回退到 mock ASR，保证项目可运行。

### Whisper 本地运行说明

- 安装 Python 依赖：`whisper` 或 `faster-whisper`
- 准备本地音频解码环境
- 前端当前发送的是 `webm/opus` 分片，后续如果需要更高稳定性，可以在后端增加 `ffmpeg` 转码

## 翻译配置

当前默认使用 mock 翻译。可以通过环境变量切换：

```bash
TRANSLATION_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_TRANSLATION_MODEL=gpt-4o-mini
```

如果启用 OpenAI translation provider，系统会尝试调用 OpenAI 兼容的翻译接口。
如果翻译服务不可用，会自动回退到 mock 翻译，保证项目可运行。

## TTS 配置

当前默认使用 mock TTS。可以通过环境变量切换：

```bash
TTS_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=alloy
```

如果启用 OpenAI TTS provider，系统会尝试返回可播放的音频字节。
如果 TTS 服务不可用，会自动回退到 mock TTS，保证项目可运行。

## 字幕修正

系统已加入字幕版本记录与回滚管理：

- 每个字幕片段会记录修订版本
- 后续识别或翻译修正时可以保留历史版本
- 前端/后端可以通过 `rollback` 事件请求回退到指定版本
- 后端会返回 `correction` 事件，通知前端局部更新字幕

## 术语库与上下文记忆

- 术语库支持内存模式和数据库持久化模式
- 启动后会自动建表，并从数据库加载术语到内存
- 前端提供术语添加、编辑、删除面板，可直接同步到后端数据库
- 每个会话会保留最近一段上下文，帮助后续翻译更稳定

## 数据库配置

当前已接入 SQLAlchemy 基础结构，默认数据库地址：

```bash
DATABASE_URL=sqlite:///./app.db
```

术语库表会在启动初始化阶段创建，并用于持久化 glossary entries。

## 启动检查清单

### 后端

- 确认 Python 依赖已安装
- 确认 `backend/app/main.py` 可正常启动
- 确认 `/health` 可访问
- 确认 WebSocket 地址 `ws://localhost:8000/api/v1/transcripts/ws/demo-session` 可握手
- 确认数据库文件/表可创建

### 前端

- 确认 `npm install` 已完成
- 确认 `npm run dev` 能启动
- 确认页面能连接 WebSocket
- 确认术语库接口可读写
- 确认麦克风权限可正常申请
- 确认浏览器支持语音播报（可选）

## 后续计划

1. 增加字幕自动修正机制
2. 增加术语库与上下文记忆的检索增强
3. 将 Settings 页真正联通到后端配置持久化
4. 优化 Whisper 音频转码与稳定性
