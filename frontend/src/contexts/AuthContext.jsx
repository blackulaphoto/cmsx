import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  updateProfile,
} from 'firebase/auth'
import { auth, firebaseConfigError, googleProvider } from '../lib/firebase'
import { apiCall, isFrontendTestAuthEnabled } from '../api/config'

const AuthContext = createContext(null)
const testAuthProfile = {
  firebase_uid: import.meta.env.VITE_TEST_AUTH_USER || 'uid-e2e',
  email: import.meta.env.VITE_TEST_AUTH_EMAIL || 'e2e.case.manager@example.com',
  full_name: import.meta.env.VITE_TEST_AUTH_NAME || 'E2E Case Manager',
  role: import.meta.env.VITE_TEST_AUTH_ROLE || 'admin',
  case_manager_id: import.meta.env.VITE_TEST_AUTH_CASE_MANAGER || 'cm_e2e',
  auth_provider: 'test',
  is_active: true
}

async function fetchBackendProfile(firebaseUser, role = 'case_manager') {
  const data = await apiCall('/api/auth/register', {
    method: 'POST',
    authUser: firebaseUser,
    body: JSON.stringify({ role }),
  })
  return data.user
}

export function AuthProvider({ children }) {
  const [firebaseUser, setFirebaseUser] = useState(null)
  const [profile, setProfile] = useState(isFrontendTestAuthEnabled ? testAuthProfile : null)
  const [loading, setLoading] = useState(isFrontendTestAuthEnabled ? false : !firebaseConfigError)
  const [configError] = useState(firebaseConfigError)
  // SaaS-mode flag from /api/auth/me. Defaults false (single-org) until /me reports.
  const [multiTenantEnabled, setMultiTenantEnabled] = useState(false)

  useEffect(() => {
    if (isFrontendTestAuthEnabled) {
      setProfile(testAuthProfile)
      setLoading(false)
      return undefined
    }

    if (!auth) {
      setLoading(false)
      return undefined
    }

    const unsubscribe = onAuthStateChanged(auth, async (nextUser) => {
      setFirebaseUser(nextUser)
      if (!nextUser) {
        setProfile(null)
        setLoading(false)
        return
      }
      try {
        const data = await apiCall('/api/auth/me', { authUser: nextUser })
        setProfile(data.user)
        setMultiTenantEnabled(Boolean(data.multi_tenant_enabled))
      } catch (error) {
        console.error(error)
        setProfile(null)
      } finally {
        setLoading(false)
      }
    })
    return unsubscribe
  }, [])

  const value = useMemo(() => ({
    firebaseUser,
    profile,
    loading,
    configError,
    multiTenantEnabled,
    async login(email, password) {
      if (!auth) throw new Error(configError || 'Firebase Auth is not configured')
      setLoading(true)
      try {
        const credential = await signInWithEmailAndPassword(auth, email, password)
        const backendProfile = await fetchBackendProfile(credential.user)
        setProfile(backendProfile)
        return backendProfile
      } finally {
        setLoading(false)
      }
    },
    async register({ email, password, fullName, role = 'case_manager' }) {
      if (!auth) throw new Error(configError || 'Firebase Auth is not configured')
      setLoading(true)
      try {
        const credential = await createUserWithEmailAndPassword(auth, email, password)
        if (fullName) {
          await updateProfile(credential.user, { displayName: fullName })
        }
        const backendProfile = await fetchBackendProfile(credential.user, role)
        setProfile(backendProfile)
        return backendProfile
      } finally {
        setLoading(false)
      }
    },
    async signInWithGoogle(role = 'case_manager') {
      if (!auth || !googleProvider) throw new Error(configError || 'Firebase Auth is not configured')
      setLoading(true)
      try {
        const credential = await signInWithPopup(auth, googleProvider)
        const backendProfile = await fetchBackendProfile(credential.user, role)
        setProfile(backendProfile)
        return backendProfile
      } finally {
        setLoading(false)
      }
    },
    async logout() {
      if (isFrontendTestAuthEnabled) {
        setProfile(testAuthProfile)
        return
      }
      if (!auth) return
      await signOut(auth)
      setProfile(null)
    },
  }), [configError, firebaseUser, profile, loading, multiTenantEnabled])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return value
}
