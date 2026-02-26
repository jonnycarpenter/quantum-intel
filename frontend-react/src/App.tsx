import { useState } from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import {
  Newspaper,
  Compass,
  TrendingUp,
  FlaskConical,
  FileText,
  Settings,
  PanelRightClose,
  PanelRightOpen,
  Bot,
} from 'lucide-react'

import BriefingPage from './pages/BriefingPage'
import ExplorePage from './pages/ExplorePage'
import MarketsPage from './pages/MarketsPage'
import ResearchPage from './pages/ResearchPage'
import FilingsPage from './pages/FilingsPage'
import SettingsPage from './pages/SettingsPage'
import ChatPanel from './components/ChatPanel'
import StatusBar from './components/StatusBar'



const NAV_ITEMS = [
  { path: '/', label: 'Briefing', icon: Newspaper },
  { path: '/explore', label: 'Explore', icon: Compass },
  { path: '/markets', label: 'Markets', icon: TrendingUp },
  { path: '/research', label: 'Research', icon: FlaskConical },
  { path: '/filings', label: 'Filings', icon: FileText },
]

export default function App() {
  const [chatOpen, setChatOpen] = useState(true)
  const location = useLocation()

  // Derive current page name for chat context
  const currentPage = NAV_ITEMS.find(n => n.path === location.pathname)?.label ?? 'Briefing'

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* ─── Header ─── */}
      <header className="flex items-center justify-between px-6 py-3 bg-bg-secondary border-b border-border">
        <div className="flex items-center gap-3">
          <img
            src="/ketzero_logo_teal_transparent.png"
            alt="Ket Zero"
            className="h-7 w-auto"
          />
          <span className="text-lg font-semibold tracking-tight text-text-primary">
            Ket Zero Intelligence
          </span>
        </div>



        <div className="flex items-center gap-3">
          <NavLink to="/settings" className="text-text-muted hover:text-text-secondary transition-colors">
            <Settings className="w-5 h-5" />
          </NavLink>
        </div>
      </header>

      {/* ─── Sub-nav Tabs ─── */}
      <nav className="flex items-center gap-1 px-6 py-2 bg-bg-secondary border-b border-border">
        {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${isActive
                ? 'bg-bg-tertiary text-accent-blue'
                : 'text-text-muted hover:bg-bg-hover hover:text-text-secondary'
              }`
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* ─── Content + Chat ─── */}
      <div className="flex flex-1 min-h-0">
        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Routes>
            <Route path="/" element={<BriefingPage />} />
            <Route path="/explore" element={<ExplorePage />} />
            <Route path="/markets" element={<MarketsPage />} />
            <Route path="/research" element={<ResearchPage />} />
            <Route path="/filings" element={<FilingsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>

        {/* Chat Panel (Right Side) */}
        {chatOpen ? (
          <aside className="w-[380px] min-w-[380px] border-l border-border bg-bg-secondary flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-accent-purple" />
                <span className="text-sm font-medium">AI Assistant</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-muted bg-bg-tertiary px-2 py-0.5 rounded">
                  {currentPage}
                </span>
                <button
                  onClick={() => setChatOpen(false)}
                  className="text-text-muted hover:text-text-secondary transition-colors"
                >
                  <PanelRightClose className="w-4 h-4" />
                </button>
              </div>
            </div>
            <ChatPanel currentPage={currentPage} domain="quantum" />
          </aside>
        ) : (
          <button
            onClick={() => setChatOpen(true)}
            className="fixed right-0 top-1/2 -translate-y-1/2 z-50 bg-bg-secondary border border-border border-r-0 rounded-l-lg px-1.5 py-4 text-text-muted hover:text-accent-purple transition-colors"
            title="Open AI Assistant"
          >
            <PanelRightOpen className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* ─── Status Bar ─── */}
      <StatusBar />
    </div>
  )
}
