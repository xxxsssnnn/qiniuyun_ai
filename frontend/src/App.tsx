import { useMemo, useState } from 'react'

import { CorrectionsPage } from './pages/CorrectionsPage'
import { DashboardPage } from './pages/DashboardPage'
import { GlossaryPage } from './pages/GlossaryPage'
import { LivePage } from './pages/LivePage'
import { SettingsPage } from './pages/SettingsPage'

const tabs = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'live', label: 'Live' },
  { id: 'glossary', label: 'Glossary' },
  { id: 'corrections', label: 'Corrections' },
  { id: 'settings', label: 'Settings' },
] as const

type TabId = typeof tabs[number]['id']

export function App() {
  const [activeTab, setActiveTab] = useState<TabId>('live')
  const activeLabel = useMemo(() => tabs.find((tab) => tab.id === activeTab)?.label ?? 'Live', [activeTab])

  return (
    <div className="app-frame">
      <header className="app-header">
        <div>
          <span className="app-kicker">AI 同声传译助手</span>
          <h1>{activeLabel}</h1>
        </div>
        <nav className="app-nav">
          {tabs.map((tab) => (
            <button key={tab.id} className={tab.id === activeTab ? 'nav-tab active' : 'nav-tab'} onClick={() => setActiveTab(tab.id)}>
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="app-main">
        {activeTab === 'dashboard' && <DashboardPage />}
        {activeTab === 'live' && <LivePage />}
        {activeTab === 'glossary' && <GlossaryPage />}
        {activeTab === 'corrections' && <CorrectionsPage />}
        {activeTab === 'settings' && <SettingsPage />}
      </main>
    </div>
  )
}
