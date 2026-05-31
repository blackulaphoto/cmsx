import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'

function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, register, signInWithGoogle } = useAuth()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')

  const redirectTo = location.state?.from?.pathname || '/'

  const handleSubmit = async (event) => {
    event.preventDefault()
    try {
      if (mode === 'register') {
        await register({ email, password, fullName })
        toast.success('Account created')
      } else {
        await login(email, password)
        toast.success('Signed in')
      }
      navigate(redirectTo, { replace: true })
    } catch (error) {
      toast.error(error.message || 'Authentication failed')
    }
  }

  const handleGoogle = async () => {
    try {
      await signInWithGoogle()
      navigate(redirectTo, { replace: true })
    } catch (error) {
      toast.error(error.message || 'Google sign-in failed')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-8 text-white shadow-2xl">
        <h1 className="text-2xl font-semibold">{mode === 'register' ? 'Create account' : 'Sign in'}</h1>
        <p className="mt-2 text-sm text-slate-300">Firebase Auth is required for all case data access.</p>
        {mode === 'register' ? (
          <input className="mt-6 w-full rounded-lg bg-slate-800 px-4 py-3" placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
        ) : null}
        <input className="mt-4 w-full rounded-lg bg-slate-800 px-4 py-3" placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input className="mt-4 w-full rounded-lg bg-slate-800 px-4 py-3" placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <button className="mt-6 w-full rounded-lg bg-cyan-500 px-4 py-3 font-medium text-slate-950" type="submit">
          {mode === 'register' ? 'Register' : 'Login'}
        </button>
        <button className="mt-3 w-full rounded-lg border border-white/15 px-4 py-3" type="button" onClick={handleGoogle}>
          Continue with Google
        </button>
        <button className="mt-4 text-sm text-cyan-300" type="button" onClick={() => setMode((current) => current === 'login' ? 'register' : 'login')}>
          {mode === 'register' ? 'Already have an account? Sign in' : 'Need an account? Register'}
        </button>
      </form>
    </div>
  )
}

export default Login
