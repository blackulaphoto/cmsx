import { Routes, Route, Navigate, useParams } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Onboarding from './pages/Onboarding'

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
import SoberLivingDirectory from './pages/SoberLivingDirectory'
import SoberLivingDirectoryListing from './pages/SoberLivingDirectoryListing'
import SoberLivingDirectoryReview from './pages/SoberLivingDirectoryReview'
import SoberLivingDirectoryDiscovery from './pages/SoberLivingDirectoryDiscovery'
import SoberLiving from './pages/SoberLiving'
import SoberLivingHouse from './pages/SoberLivingHouse'
import Benefits from './pages/Benefits'
import Medical from './pages/Medical'
import Rolodex from './pages/Rolodex'
import Resume from './pages/Resume'
import Legal from './pages/Legal'
import FMLA from './pages/FMLA'
import UR from './pages/UR'
import DocumentationCenter from './pages/DocumentationCenter'
import AIChat from './pages/AIChat'
import Services from './pages/Services'
import SmartDaily from './pages/SmartDaily'
import Jobs from './pages/Jobs'
import Messages from './pages/Messages'
import SupervisorDashboard from './pages/SupervisorDashboard'
import AIAssistantPopup from './components/AIAssistant/AIAssistantPopup'
// System administration and monitoring
import SystemIntegrity from './pages/SystemIntegrity'
// Phase 3: Frontend Integration Audit
import IntegrationAudit from './pages/IntegrationAudit'
// Group Facilitation module
import Groups from './pages/Groups'
import GroupSessionDetail from './pages/GroupSessionDetail'
import TreatmentPlan from './pages/TreatmentPlan'
// Admissions module
import Admissions from './pages/Admissions'
import AdmissionsNew from './pages/AdmissionsNew'
import AdmissionsPacket from './pages/AdmissionsPacket'
import AdmissionsForm from './pages/AdmissionsForm'

function RedirectCaseManagement() {
  const { clientId } = useParams()
  return <Navigate to={`/client/${clientId}`} replace />
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/onboarding" element={
        <ProtectedRoute allowOnboarding>
          <Onboarding />
        </ProtectedRoute>
      } />
      <Route path="/*" element={
        <ProtectedRoute>
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
        <Route path="/case-management/:clientId" element={<RedirectCaseManagement />} />
        <Route path="/client/:clientId" element={<ClientDashboard />} />
        {/* ✅ HOUSING SYSTEM ROUTES - FULLY FUNCTIONAL - DO NOT MODIFY */}
        {/* These routes provide: Real housing search, Case manager tools, API testing */}
        <Route path="/housing" element={<HousingSearch />} />
        <Route path="/housing/case-manager" element={<CaseManagerHousing />} />
        <Route path="/housing/test" element={<HousingTest />} />
        <Route path="/sober-living-directory" element={<SoberLivingDirectory />} />
        <Route path="/sober-living-directory/discovery" element={<SoberLivingDirectoryDiscovery />} />
        <Route path="/sober-living-directory/review" element={<SoberLivingDirectoryReview />} />
        <Route path="/sober-living-directory/:listingId" element={<SoberLivingDirectoryListing />} />
        <Route path="/sober-living" element={<SoberLiving />} />
        <Route path="/sober-living/:houseId" element={<SoberLivingHouse />} />
        <Route path="/benefits" element={<Benefits />} />
        <Route path="/medical" element={<Medical />} />
        <Route path="/rolodex" element={<Rolodex />} />
        <Route path="/resume" element={<Resume />} />
        <Route path="/legal" element={<Legal />} />
        <Route path="/fmla" element={<FMLA />} />
        <Route path="/ur" element={<UR />} />
        <Route path="/documentation" element={<DocumentationCenter />} />
        <Route path="/ai-chat" element={<AIChat />} />
        <Route path="/services" element={<Services />} />
        <Route path="/messages" element={<Messages />} />
        <Route path="/smart-dashboard" element={<SmartDaily />} />
              <Route path="/supervisor-dashboard" element={
                <ProtectedRoute roles={['admin']}>
                  <SupervisorDashboard />
                </ProtectedRoute>
              } />
        <Route path="/jobs" element={<Jobs />} />
        {/* System administration and monitoring */}
        <Route path="/system-integrity" element={<SystemIntegrity />} />
        {/* Phase 3: Frontend Integration Audit */}
        <Route path="/integration-audit" element={<IntegrationAudit />} />
        {/* Group Facilitation */}
        <Route path="/groups" element={<Groups />} />
        <Route path="/groups/sessions/:sessionId" element={<GroupSessionDetail />} />
        {/* Treatment Plan */}
        <Route path="/treatment-plan" element={<TreatmentPlan />} />
        {/* Admissions module — specific paths declared before parameter routes */}
        <Route path="/admissions" element={<Admissions />} />
        <Route path="/admissions/new" element={<AdmissionsNew />} />
        <Route path="/admissions/:client_id/forms/:form_key" element={<AdmissionsForm />} />
        <Route path="/admissions/:client_id" element={<AdmissionsPacket />} />

        {/* Redirect any unmatched routes to dashboard */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
            <AIAssistantPopup />
          </Layout>
        </ProtectedRoute>
      } />
    </Routes>
  )
}

export default App
