import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import Input from '../components/ui/Input'
import Button from '../components/ui/Button'

const REQUIREMENTS = [
  { label: 'At least 12 characters',      test: (p: string) => p.length >= 12 },
  { label: 'Uppercase letter (A–Z)',       test: (p: string) => /[A-Z]/.test(p) },
  { label: 'Lowercase letter (a–z)',       test: (p: string) => /[a-z]/.test(p) },
  { label: 'Number (0–9)',                 test: (p: string) => /\d/.test(p) },
  { label: 'Special character (!@#$…)',   test: (p: string) => /[!@#$%^&*()\-_=+[\]{};:'",.<>/?\\|`~]/.test(p) },
]

const STRENGTH_LABEL = ['', 'Very Weak', 'Weak', 'Fair', 'Good', 'Strong']
const STRENGTH_COLOR = ['', 'bg-red-500', 'bg-orange-400', 'bg-yellow-400', 'bg-blue-400', 'bg-green-500']
const STRENGTH_TEXT  = ['', 'text-red-500', 'text-orange-500', 'text-yellow-600', 'text-blue-500', 'text-green-600']

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register, loading, error, clearError } = useAuthStore()

  const [email, setEmail]       = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [touched, setTouched]   = useState(false)

  const met      = REQUIREMENTS.map((r) => r.test(password))
  const strength = met.filter(Boolean).length
  const allMet   = strength === REQUIREMENTS.length

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setTouched(true)
    if (!allMet) return
    clearError()
    try {
      await register(email, username, password)
      navigate('/')
    } catch {
      // error shown via store
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-indigo-50 to-slate-100 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mb-2 text-4xl font-bold text-indigo-700">Boardly</div>
          <p className="text-sm text-gray-500">Create your account</p>
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-lg">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
            <Input
              label="Username"
              type="text"
              placeholder="yourname"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />

            <div>
              <Input
                label="Password"
                type="password"
                placeholder="Min. 12 characters"
                value={password}
                onChange={(e) => { setTouched(true); setPassword(e.target.value) }}
                required
              />

              {touched && password.length > 0 && (
                <div className="mt-2 space-y-2">
                  {/* Strength bar */}
                  <div className="flex gap-1">
                    {REQUIREMENTS.map((_, i) => (
                      <div
                        key={i}
                        className={`h-1.5 flex-1 rounded-full transition-colors duration-200 ${
                          i < strength ? STRENGTH_COLOR[strength] : 'bg-gray-200'
                        }`}
                      />
                    ))}
                  </div>
                  <p className={`text-xs font-semibold ${STRENGTH_TEXT[strength]}`}>
                    {STRENGTH_LABEL[strength]}
                  </p>

                  {/* Requirements checklist */}
                  <ul className="space-y-1">
                    {REQUIREMENTS.map((r, i) => (
                      <li
                        key={i}
                        className={`flex items-center gap-1.5 text-xs transition-colors ${
                          met[i] ? 'text-green-600' : 'text-gray-400'
                        }`}
                      >
                        <span className="w-3 shrink-0">{met[i] ? '✓' : '✗'}</span>
                        {r.label}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>
            )}

            <Button
              type="submit"
              loading={loading}
              disabled={touched && !allMet}
              className="w-full"
              size="lg"
            >
              Create account
            </Button>
          </form>

          <p className="mt-5 text-center text-sm text-gray-500">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-indigo-600 hover:text-indigo-800">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
