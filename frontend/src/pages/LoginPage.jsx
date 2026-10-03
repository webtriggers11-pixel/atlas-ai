/**
 * Sign in / create account — shown only when the server runs with AUTH_ENABLED=true.
 * A self-hosted install (the default) never sees this page.
 */
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { LogIn, UserPlus } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/store/authStore'
import { Button, Field, Input, Notice, Panel } from '@/components/kit'
import { Logo, ThemeToggle } from '@/components/layout'

export default function LoginPage({ registration }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const signIn = useAuth((s) => s.signIn)
  const queryClient = useQueryClient()

  const submit = useMutation({
    mutationFn: () => (mode === 'login' ? api.login(email, password) : api.register(email, password)),
    onSuccess: (session) => {
      queryClient.clear()   // nothing cached from a previous user survives
      signIn(session)
    },
  })

  const isLogin = mode === 'login'
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="flex h-14 items-center justify-between border-b border-border px-4 sm:px-6">
        <Logo />
        <ThemeToggle />
      </header>
      <main className="grid flex-1 place-items-center px-4 py-10">
        <Panel className="w-full max-w-sm p-6">
          <h1 className="text-xl font-semibold tracking-tight">{isLogin ? 'Sign in' : 'Create an account'}</h1>
          <p className="mt-1 text-sm text-muted">
            {isLogin ? 'Your analyses are private to your account.' : 'Use at least 8 characters for the password.'}
          </p>
          <form
            className="mt-5 space-y-4"
            onSubmit={(e) => { e.preventDefault(); submit.mutate() }}
          >
            <Field label="Email">
              <Input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </Field>
            <Field label="Password">
              <Input
                type="password"
                autoComplete={isLogin ? 'current-password' : 'new-password'}
                required
                minLength={8}
                maxLength={128}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
            {submit.isError && <Notice>{submit.error.message}</Notice>}
            <Button type="submit" className="w-full justify-center" icon={isLogin ? LogIn : UserPlus} disabled={submit.isPending}>
              {submit.isPending ? 'Please wait…' : isLogin ? 'Sign in' : 'Create account'}
            </Button>
          </form>
          {registration && (
            <button
              type="button"
              className="mt-4 w-full cursor-pointer text-center text-sm text-muted hover:text-foreground"
              onClick={() => { setMode(isLogin ? 'register' : 'login'); submit.reset() }}
            >
              {isLogin ? 'No account? Create one' : 'Already have an account? Sign in'}
            </button>
          )}
        </Panel>
      </main>
    </div>
  )
}
