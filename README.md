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

当前仍使用模拟 ASR / 翻译 / TTS 作为占位实现，后续可以无缝替换为真实模型或云服务。

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

如果启用 Whisper provider，系统会尝试加载 `whisper` 包并执行本地转写。
如果 Whisper 不可用或模型加载失败，会自动回退到 mock ASR，保证项目可运行。

### Whisper 本地运行说明

- 安装 Python 依赖：`whisper`
- 准备本地音频解码环境
- 默认模型名：`base`
- 目前实现先将前端传来的音频 chunk 写入临时文件，再调用 Whisper 推理

> 提示：前端当前发送的是 `webm/opus` 分片，后续如果需要更高稳定性，可以在后端增加 `ffmpeg` 转码成 Whisper 更适合处理的格式。

## 翻译配置

当前默认使用 mock 翻译。可以通过环境变量切换：

```bash
TRANSLATION_PROVIDER=openai
```

如果启用 OpenAI translation provider，系统会尝试调用 OpenAI 兼容的翻译接口。
如果翻译服务不可用，会自动回退到 mock 翻译，保证项目可运行。

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

## 项目启动检查清单

### 后端

- 安装依赖
- 设置可选环境变量 `ASR_PROVIDER`、`TRANSLATION_PROVIDER`、`DATABASE_URL`
- 启动 `uvicorn app.main:app --reload`
- 访问健康检查接口 `http://localhost:8000/health`
- 连接 WebSocket `ws://localhost:8000/api/v1/transcripts/ws/demo-session`
- 确认术语库接口 `GET /api/v1/glossary` 可正常返回

### 前端

- 安装依赖
- 启动 `npm run dev`
- 打开 `http://localhost:5173`
- 确认页面能连接 WebSocket
- 确认“开始演示字幕”可正常推送字幕
- 确认术语库可新增、编辑、删除

### 功能验证

- 演示模式可展示字幕流
- 麦克风采集按钮可启动/停止录音
- 音频块可发送到后端
- 后端可返回字幕 chunk / revision / correction 事件
- 术语库可持久化到数据库

## 后续计划

1. 接入真实 ASR 模型
2. 接入真实翻译服务
3. 接入真实 TTS 服务
4. 增加字幕自动修正机制
5. 增加术语库与上下文记忆的检索增强
