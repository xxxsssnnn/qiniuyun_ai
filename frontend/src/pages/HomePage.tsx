import { StatusCard } from '../components/StatusCard'

export function HomePage() {
  return (
    <main className="app-shell">
      <section className="hero">
        <span className="badge">AI 同声传译助手</span>
        <h1>实时字幕翻译与修正的前端骨架</h1>
        <p>
          这是前端项目的基础框架，后续会接入音频采集、WebSocket 实时字幕、翻译结果展示和修正回放。
        </p>
      </section>

      <section className="panel-grid">
        <StatusCard title="实时字幕区" description="用于展示原文、译文、临时字幕和最终字幕。" />
        <StatusCard title="控制区" description="用于选择音频输入、语言、字幕模式和播报开关。" />
        <StatusCard title="会话区" description="用于显示当前连接状态、识别状态和翻译状态。" />
      </section>
    </main>
  )
}
