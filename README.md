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

当前仍使用模拟 ASR / 翻译 / TTS 作为占位实现，后续可以无缝替换为真实模型或云服务。

## 目录结构

```text
backend/
  app/
    api/
      v1/
    core/
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

## ASR 配置

当前默认使用 mock ASR。可以通过环境变量切换：

```bash
ASR_PROVIDER=whisper
```

可替换目标包括：

- Whisper
- faster-whisper
- FunASR
- 云语音识别服务

如果未安装 Whisper 或模型不可用，系统会自动回退到 mock ASR，保证项目可运行。

## 后续计划

1. 接入真实 ASR 模型
2. 接入真实翻译服务
3. 接入真实 TTS 服务
4. 增加字幕自动修正机制
5. 增加术语库与上下文记忆
