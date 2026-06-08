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

const AuthContext = createContext(null)
const isFrontendTestAuthEnabled = import.meta.env.VITE_ENABLE_TEST_AUTH === 'true'
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
  const token = await firebaseUser.getIdToken()
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ role }),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Failed to register user profile')
  }
  const data = await response.json()
  return data.user
}

export function AuthProvider({ children }) {
  const [firebaseUser, setFirebaseUser] = useState(null)
  const [profile, setProfile] = useState(isFrontendTestAuthEnabled ? testAuthProfile : null)
  const [loading, setLoading] = useState(isFrontendTestAuthEnabled ? false : !firebaseConfigError)
  const [configError] = useState(firebaseConfigError)

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
        const token = await nextUser.getIdToken()
        const response = await fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!response.ok) {
          throw new Error('Failed to load auth profile')
        }
        const data = await response.json()
        setProfile(data.user)
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
  }), [configError, firebaseUser, profile, loading])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return value
}
