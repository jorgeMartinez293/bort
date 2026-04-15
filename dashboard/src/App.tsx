// dashboard/src/App.tsx
import './styles/globals.css'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Topbar }    from './components/Topbar'
import { Sidebar }   from './components/Sidebar'
import { Pending }   from './pages/Pending'
import { Published } from './pages/Published'
import { Rejected }  from './pages/Rejected'
import { Settings }  from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
        <Topbar />
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          <Sidebar />
          <Routes>
            <Route path="/"           element={<Pending />} />
            <Route path="/published"  element={<Published />} />
            <Route path="/rejected"   element={<Rejected />} />
            <Route path="/settings"   element={<Settings />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
