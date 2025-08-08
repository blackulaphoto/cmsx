import { Routes, Route, Navigate } from 'react-router-dom'

// Import layout component
import Layout from './components/Layout'

// Import page components
import Dashboard from './pages/Dashboard'
import CaseManagement from './pages/CaseManagement'
import ClientDashboard from './pages/ClientDashboard'
import HousingSearch from './pages/HousingSearch'
import Benefits from './pages/Benefits'
import Resume from './pages/Resume'
import Legal from './pages/Legal'
import Expungement from './pages/Expungement'
import AIChat from './pages/AIChat'
import Services from './pages/Services'
import SmartDaily from './pages/SmartDaily'
import Jobs from './pages/Jobs'

function App() {
  return (
    <Layout>
      <Routes>
        {/* Main Dashboard - replaces old HTML root route */}
        <Route path="/" element={<Dashboard />} />
        
        {/* Core Service Pages - replace old HTML template routes */}
        <Route path="/case-management" element={<CaseManagement />} />
        <Route path="/client/:clientId" element={<ClientDashboard />} />
        <Route path="/housing" element={<HousingSearch />} />
        <Route path="/benefits" element={<Benefits />} />
        <Route path="/resume" element={<Resume />} />
        <Route path="/legal" element={<Legal />} />
        <Route path="/expungement" element={<Expungement />} />
        <Route path="/ai-chat" element={<AIChat />} />
        <Route path="/services" element={<Services />} />
        <Route path="/smart-dashboard" element={<SmartDaily />} />
        <Route path="/jobs" element={<Jobs />} />
        
        {/* Redirect any unmatched routes to dashboard */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default App