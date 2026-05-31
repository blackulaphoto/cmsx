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
import { auth, googleProvider } from '../lib/firebase'

const AuthContext = createContext(null)

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
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
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
    async login(email, password) {
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
      await signOut(auth)
      setProfile(null)
    },
  }), [firebaseUser, profile, loading])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return value
}
