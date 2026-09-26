import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { useAuth } from '../context/AuthContext';
import { AlertCircle, Shield } from 'lucide-react';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState('consultant@red.tn');
  const [password, setPassword] = useState('Consultant#2026!');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid credentials. Please verify and try again.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-white">
      {/* Left pane - Editorial Property Imagery */}
      <div className="hidden lg:block lg:w-1/2 relative bg-[var(--color-forest)]">
        <img
          src="https://images.unsplash.com/photo-1600585154340-be6161a56a0c?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80"
          alt="Tamil Nadu Prime Property"
          className="absolute inset-0 h-full w-full object-cover opacity-80"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#1F3A37] via-[#1F3A37]/60 to-transparent" />
        <div className="absolute bottom-12 left-12 right-12 text-white">
          <div className="inline-flex items-center gap-2 rounded bg-white/10 px-3 py-1 backdrop-blur-sm text-xs font-semibold tracking-wide text-[var(--color-gold)] mb-4">
            <Shield className="h-3.5 w-3.5" /> TAMIL NADU BROKERAGE WORKSPACE
          </div>
          <h1 className="font-serif text-3xl font-bold leading-tight">
            Rigorous Property Verification & High-Density Brokerage
          </h1>
          <p className="mt-2 text-sm text-gray-200 max-w-md">
            Operational intelligence for Patta/Chitta, EC encumbrance analysis, CMDA/DTCP planning checks, and client pipelines.
          </p>
        </div>
      </div>

      {/* Right pane - Form */}
      <div className="flex w-full flex-col justify-center px-6 sm:px-12 lg:w-1/2 lg:px-20 xl:px-28 bg-[var(--color-parchment-warm)]">
        <div className="mx-auto w-full max-w-sm rounded-lg bg-white p-8 shadow-sm border border-[var(--color-border-ui)]">
          <div className="mb-8">
            <div className="flex items-center">
              <span className="font-serif text-3xl font-bold tracking-tight text-[var(--color-forest)]">RED</span>
              <span className="ml-2 rounded bg-[var(--color-parchment)] px-1.5 py-0.5 text-xs font-semibold text-[var(--color-ink-secondary)]">
                TN V1
              </span>
            </div>
            <h2 className="mt-4 text-xl font-bold tracking-tight text-[var(--color-ink)]">
              Consultant Sign In
            </h2>
            <p className="mt-1 text-xs text-[var(--color-ink-muted)]">
              Enter your credentials to access the operational backend.
            </p>
          </div>

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-3 text-xs text-red-800 border border-red-200 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-[var(--color-ink)] mb-1">
                Consultant Email
              </label>
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="consultant@red.tn"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-[var(--color-ink)] mb-1">
                Password
              </label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <Button type="submit" className="w-full mt-2" isLoading={isLoading}>
              Sign In to Workspace
            </Button>
          </form>

          <div className="mt-6 pt-4 border-t border-[var(--color-border-ui)] text-[11px] text-[var(--color-ink-muted)]">
            <p className="font-medium text-[var(--color-ink)] mb-1">Default Consultant Credentials:</p>
            <div className="bg-gray-50 p-2 rounded text-[10px] space-y-0.5 font-mono">
              <div>Email: <span className="text-gray-900">consultant@red.tn</span></div>
              <div>Password: <span className="text-gray-900">Consultant#2026!</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
