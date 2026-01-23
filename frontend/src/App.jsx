import { Routes, Route, Navigate } from 'react-router-dom'

// Import layout component
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'

// Import page components
import Dashboard from './pages/Dashboard'
import EnhancedDashboard from './pages/enhanced_dashboard.jsx'
import CaseManagement from './pages/CaseManagement'
import ClientDashboard from './pages/ClientDashboard'
// ✅ HOUSING SYSTEM - FULLY FUNCTIONAL - DO NOT MODIFY
// This housing system is working perfectly with real Google Housing CSE integration
// Includes: Basic search, Case Manager tools, API testing, real data display
import HousingSearch from './pages/HousingSearch'
import CaseManagerHousing from './pages/CaseManagerHousing'
import HousingTest from './pages/HousingTest'
import Benefits from './pages/Benefits'
import Resume from './pages/Resume'
import Legal from './pages/Legal'
import Expungement from './pages/Expungement'
import AIChat from './pages/AIChat'
import Services from './pages/Services'
import SmartDaily from './pages/SmartDaily'
import Jobs from './pages/Jobs'
import AIAssistantPopup from './components/AIAssistant/AIAssistantPopup'
// System administration and monitoring
import SystemIntegrity from './pages/SystemIntegrity'
// Phase 3: Frontend Integration Audit
import IntegrationAudit from './pages/IntegrationAudit'

function App() {
  return (
    <Layout>
      <Routes>
        {/* Enhanced Dashboard - now the main dashboard with ClickUp-style components */}
        <Route path="/" element={
          <ErrorBoundary>
            <EnhancedDashboard />
          </ErrorBoundary>
        } />
        
        {/* Enhanced Dashboard - backward compatibility route */}
        <Route path="/enhanced-dashboard" element={
          <ErrorBoundary>
            <EnhancedDashboard />
          </ErrorBoundary>
        } />
        
        {/* Old Dashboard - moved to legacy route */}
        <Route path="/legacy-dashboard" element={<Dashboard />} />
        
        {/* Core Service Pages - replace old HTML template routes */}
        <Route path="/case-management" element={<CaseManagement />} />
        <Route path="/client/:clientId" element={<ClientDashboard />} />
        {/* ✅ HOUSING SYSTEM ROUTES - FULLY FUNCTIONAL - DO NOT MODIFY */}
        {/* These routes provide: Real housing search, Case manager tools, API testing */}
        <Route path="/housing" element={<HousingSearch />} />
        <Route path="/housing/case-manager" element={<CaseManagerHousing />} />
        <Route path="/housing/test" element={<HousingTest />} />
        <Route path="/benefits" element={<Benefits />} />
        <Route path="/resume" element={<Resume />} />
        <Route path="/legal" element={<Legal />} />
        <Route path="/expungement" element={<Expungement />} />
        <Route path="/ai-chat" element={<AIChat />} />
        <Route path="/services" element={<Services />} />
        <Route path="/smart-dashboard" element={<SmartDaily />} />
        <Route path="/jobs" element={<Jobs />} />
        {/* System administration and monitoring */}
        <Route path="/system-integrity" element={<SystemIntegrity />} />
        {/* Phase 3: Frontend Integration Audit */}
        <Route path="/integration-audit" element={<IntegrationAudit />} />
        
        {/* Redirect any unmatched routes to dashboard */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <AIAssistantPopup />
    </Layout>
  )
}

export default App
