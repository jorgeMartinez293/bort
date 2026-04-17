// dashboard/src/App.tsx
import './styles/globals.css'
import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Sidebar }   from './components/Sidebar'
import { Pending }   from './pages/Pending'
import { Queue }     from './pages/Queue'
import { Published } from './pages/Published'
import { Rejected }  from './pages/Rejected'
import { Settings }  from './pages/Settings'
import { useIsMobile } from './hooks/useIsMobile'

export default function App() {
  const isMobile = useIsMobile()
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <BrowserRouter>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>

        {/* Mobile-only top bar */}
        {isMobile && (
          <div style={{
            height: 44, flexShrink: 0,
            display: 'flex', alignItems: 'center', padding: '0 0.75rem', gap: '0.65rem',
            background: 'rgba(255,255,255,0.025)',
            backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
            borderBottom: '1px solid rgba(255,255,255,0.07)',
          }}>
            <button
              onClick={() => setDrawerOpen(true)}
              style={{
                width: 30, height: 30, borderRadius: 7,
                background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.09)',
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                gap: 4, cursor: 'pointer', flexShrink: 0,
              }}
            >
              {[0, 1, 2].map(i => (
                <span key={i} style={{
                  display: 'block', width: 14, height: 1.5,
                  background: 'rgba(255,255,255,0.7)', borderRadius: 2,
                }} />
              ))}
            </button>
            <span style={{
              fontFamily: 'var(--font-body)', fontWeight: 700, fontSize: '1.1rem',
              letterSpacing: '-0.03em', color: 'var(--violet-light)',
            }}>bort</span>
          </div>
        )}

        {/* Main content row */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          <Sidebar
            isMobile={isMobile}
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
          />
          <Routes>
            <Route path="/"           element={<Pending />} />
            <Route path="/queue"      element={<Queue />} />
            <Route path="/published"  element={<Published />} />
            <Route path="/rejected"   element={<Rejected />} />
            <Route path="/settings"   element={<Settings />} />
          </Routes>
        </div>

      </div>
    </BrowserRouter>
  )
}
