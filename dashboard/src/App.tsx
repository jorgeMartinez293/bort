// dashboard/src/App.tsx
import './styles/globals.css'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Sidebar }   from './components/Sidebar'
import { Pending }   from './pages/Pending'
import { Queue }     from './pages/Queue'
import { Published } from './pages/Published'
import { Rejected }  from './pages/Rejected'
import { Settings }  from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
        <Sidebar />
        <Routes>
          <Route path="/"           element={<Pending />} />
          <Route path="/queue"      element={<Queue />} />
          <Route path="/published"  element={<Published />} />
          <Route path="/rejected"   element={<Rejected />} />
          <Route path="/settings"   element={<Settings />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
