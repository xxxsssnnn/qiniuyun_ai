import { StatusCard } from '../components/StatusCard'

export function DashboardPage() {
  return (
    <main className="page-shell">
      <section className="page-hero">
        <span className="badge">Dashboard</span>
        <h2>项目总览</h2>
        <p>查看当前系统状态、实时能力覆盖和运行概况。</p>
      </section>

      <section className="panel-grid">
        <StatusCard title="实时链路" description="音频采集、ASR、翻译、字幕展示与修正链路均已接入。" />
        <StatusCard title="部署状态" description="后端可启动，前端可启动，支持本地演示模式。" />
        <StatusCard title="扩展能力" description="支持术语库、上下文记忆、字幕修正与版本回滚。" />
      </section>

      <section className="panel">
        <h3>当前建议</h3>
        <ul className="feature-list">
          <li>先使用演示模式验证页面与消息流。</li>
          <li>再切换麦克风输入验证音频通路。</li>
          <li>最后替换真实 ASR、翻译和 TTS 服务。</li>
        </ul>
      </section>
    </main>
  )
}
