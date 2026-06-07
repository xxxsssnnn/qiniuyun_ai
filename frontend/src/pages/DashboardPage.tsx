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
    </main>
  )
}
