import { useMemo, useState } from 'react'

import { CorrectionsPage } from './pages/CorrectionsPage'
import { DashboardPage } from './pages/DashboardPage'
import { GlossaryPage } from './pages/GlossaryPage'
import { LivePage } from './pages/LivePage'
import { SettingsPage } from './pages/SettingsPage'

const tabs = [
  { id: 'dashboard', label: 'Dashboard', shortLabel: 'DB' },
  { id: 'live', label: 'Live', shortLabel: 'LIVE' },
  { id: 'glossary', label: 'Glossary', shortLabel: 'GL' },
  { id: 'corrections', label: 'Corrections', shortLabel: 'CR' },
  { id: 'settings', label: 'Settings', shortLabel: 'ST' },
] as const

type TabId = typeof tabs[number]['id']

export function App() {
  const [activeTab, setActiveTab] = useState<TabId>('live')
  const activeLabel = useMemo(() => tabs.find((tab) => tab.id === activeTab)?.label ?? 'Live', [activeTab])

  return (
    <div className="app-frame">
      <aside className="app-sidebar">
        <div className="app-brand">
          <span className="brand-mark" aria-hidden="true">AI</span>
          <div className="brand-copy">
            <strong>Interpreter</strong>
            <span>Realtime workspace</span>
          </div>
        </div>

        <nav className="app-nav" aria-label="Main navigation">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={tab.id === activeTab ? 'nav-tab active' : 'nav-tab'}
              onClick={() => setActiveTab(tab.id)}
              aria-current={tab.id === activeTab ? 'page' : undefined}
            >
              <span className="nav-icon" aria-hidden="true">{tab.shortLabel}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="connection-dot" aria-hidden="true" />
          <div>
            <strong>Local workspace</strong>
            <span>AI simultaneous interpretation</span>
          </div>
        </div>
      </aside>

      <div className="app-workspace">
        <header className="app-header">
          <div className="page-heading">
            <span className="app-kicker">AI INTERPRETATION</span>
            <h1>{activeLabel}</h1>
            <p>Realtime interpretation console</p>
          </div>
          <div className="header-status">
            <span className="status-pulse" aria-hidden="true" />
            <span>Workspace ready</span>
          </div>
        </header>

        <main className="app-main">
          <div hidden={activeTab !== 'live'}>
            <LivePage />
          </div>
          {activeTab === 'dashboard' && <DashboardPage />}
          {activeTab === 'glossary' && <GlossaryPage />}
          {activeTab === 'corrections' && <CorrectionsPage />}
          {activeTab === 'settings' && <SettingsPage />}
        </main>
      </div>
    </div>
  )
}
