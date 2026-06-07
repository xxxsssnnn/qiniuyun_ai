import { useMemo, useState } from 'react'

import { CorrectionsPage } from './pages/CorrectionsPage'
import { DashboardPage } from './pages/DashboardPage'
import { GlossaryPage } from './pages/GlossaryPage'
import { LivePage } from './pages/LivePage'
import { SessionsPage } from './pages/SessionsPage'
import { SettingsPage } from './pages/SettingsPage'

const tabs = [
  { id: 'live', label: '实时传译', shortLabel: 'Live', helper: '开始录音与查看字幕' },
  { id: 'settings', label: '模型设置', shortLabel: 'AI', helper: '配置识别与翻译' },
  { id: 'glossary', label: '术语库', shortLabel: 'Term', helper: '维护专有名词' },
  { id: 'corrections', label: '字幕修正', shortLabel: 'Fix', helper: '回看与修订结果' },
  { id: 'sessions', label: '历史会话', shortLabel: 'Log', helper: '归档、查询与导出' },
  { id: 'dashboard', label: '概览', shortLabel: 'Home', helper: '查看系统状态' },
] as const

type TabId = typeof tabs[number]['id']

export function App() {
  const [activeTab, setActiveTab] = useState<TabId>('live')
  const [liveSessionId, setLiveSessionId] = useState('')
  const activeTabInfo = useMemo(() => tabs.find((tab) => tab.id === activeTab) ?? tabs[0], [activeTab])

  const handleOpenLiveSession = (sessionId: string) => {
    setLiveSessionId(sessionId)
    setActiveTab('live')
  }

  return (
    <div className="app-frame">
      <aside className="app-sidebar">
        <div className="app-brand">
          <span className="brand-mark" aria-hidden="true">译</span>
          <div className="brand-copy">
            <strong>同声传译助手</strong>
            <span>实时外语会议字幕与翻译</span>
          </div>
        </div>

        <nav className="app-nav" aria-label="主要功能">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={tab.id === activeTab ? 'nav-tab active' : 'nav-tab'}
              onClick={() => setActiveTab(tab.id)}
              aria-current={tab.id === activeTab ? 'page' : undefined}
            >
              <span className="nav-icon" aria-hidden="true">{tab.shortLabel}</span>
              <span className="nav-text">
                <strong>{tab.label}</strong>
                <small>{tab.helper}</small>
              </span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="connection-dot" aria-hidden="true" />
          <div>
            <strong>本地服务就绪后即可使用</strong>
            <span>建议使用耳机并保持麦克风清晰</span>
          </div>
        </div>
      </aside>

      <div className="app-workspace">
        <header className="app-header">
          <div className="page-heading">
            <span className="app-kicker">AI Interpretation</span>
            <h1>{activeTabInfo.label}</h1>
            <p>{activeTabInfo.helper}</p>
          </div>
          <div className="header-status">
            <span className="status-pulse" aria-hidden="true" />
            <span>工作台已准备</span>
          </div>
        </header>

        <main className="app-main">
          {activeTab === 'live' && (
            <LivePage
              sessionId={liveSessionId}
              onSessionChange={setLiveSessionId}
            />
          )}
          {activeTab === 'dashboard' && <DashboardPage />}
          {activeTab === 'glossary' && <GlossaryPage />}
          {activeTab === 'corrections' && <CorrectionsPage />}
          {activeTab === 'sessions' && (
            <SessionsPage onOpenSession={handleOpenLiveSession} />
          )}
          {activeTab === 'settings' && <SettingsPage />}
        </main>
      </div>
    </div>
  )
}
