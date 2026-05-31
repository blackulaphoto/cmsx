import { initializeApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider } from 'firebase/auth'

const getEnvValue = (viteKey, nextKey) => {
  return import.meta.env[viteKey] || import.meta.env[nextKey] || ''
}

const firebaseConfig = {
  apiKey: getEnvValue('VITE_FIREBASE_API_KEY', 'NEXT_PUBLIC_FIREBASE_API_KEY'),
  authDomain: getEnvValue('VITE_FIREBASE_AUTH_DOMAIN', 'NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN'),
  projectId: getEnvValue('VITE_FIREBASE_PROJECT_ID', 'NEXT_PUBLIC_FIREBASE_PROJECT_ID'),
  storageBucket: getEnvValue('VITE_FIREBASE_STORAGE_BUCKET', 'NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET'),
  messagingSenderId: getEnvValue('VITE_FIREBASE_MESSAGING_SENDER_ID', 'NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID'),
  appId: getEnvValue('VITE_FIREBASE_APP_ID', 'NEXT_PUBLIC_FIREBASE_APP_ID'),
  measurementId: getEnvValue('VITE_FIREBASE_MEASUREMENT_ID', 'NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID'),
}

const missingKeys = Object.entries(firebaseConfig)
  .filter(([, value]) => !value)
  .map(([key]) => key)

const requiredKeys = ['apiKey', 'authDomain', 'projectId', 'appId']
const missingRequiredKeys = requiredKeys.filter((key) => !firebaseConfig[key])

if (missingKeys.length > 0) {
  console.warn('Firebase config is incomplete:', missingKeys.join(', '))
}

export const firebaseConfigError = missingRequiredKeys.length > 0
  ? `Missing Firebase config: ${missingRequiredKeys.join(', ')}`
  : null

const app = firebaseConfigError ? null : initializeApp(firebaseConfig)

export const auth = app ? getAuth(app) : null
export const googleProvider = app ? new GoogleAuthProvider() : null
