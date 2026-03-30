import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Orbit, Loader2, AlertCircle, CheckCircle2, ArrowLeft, ShieldCheck } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true';

type AuthView = 'login' | 'signup' | 'forgot-password';

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, signup, resetPassword, isLoading, error, clearError } = useAuthStore();

  const [view, setView] = useState<AuthView>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  const handleDemoSSO = async () => {
    clearError();
    await login('demo@spoc-benchmark.org', 'demo');
    const currentError = useAuthStore.getState().error;
    if (!currentError) {
      navigate(from, { replace: true });
    }
  };

  const switchView = (newView: AuthView) => {
    setView(newView);
    setEmail('');
    setPassword('');
    setConfirmPassword('');
    setSuccessMessage(null);
    clearError();
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setSuccessMessage(null);
    await login(email, password);

    // If login succeeded (no error set after await), navigate
    const currentError = useAuthStore.getState().error;
    if (!currentError) {
      navigate(from, { replace: true });
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setSuccessMessage(null);

    if (password !== confirmPassword) {
      // Use the store's error mechanism is not ideal here, so handle locally
      useAuthStore.setState({ error: 'Passwords do not match.' });
      return;
    }

    if (password.length < 6) {
      useAuthStore.setState({ error: 'Password must be at least 6 characters.' });
      return;
    }

    await signup(email, password);

    const currentError = useAuthStore.getState().error;
    if (!currentError) {
      setSuccessMessage('Check your email for a confirmation link to complete your signup.');
      setView('login');
      setPassword('');
      setConfirmPassword('');
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setSuccessMessage(null);
    await resetPassword(email);

    const currentError = useAuthStore.getState().error;
    if (!currentError) {
      setSuccessMessage('If an account exists with that email, you will receive a password reset link.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 space-bg relative overflow-hidden">
      {/* Animated starfield */}
      <div className="starfield" aria-hidden="true" />

      {/* Grid pattern overlay */}
      <div className="fixed inset-0 grid-pattern opacity-20 pointer-events-none" aria-hidden="true" />

      {/* Floating orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cosmic-cyan/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '0s' }} />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-stellar-purple/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
      <div className="absolute top-1/2 right-1/3 w-64 h-64 bg-cosmic-blue/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '4s' }} />

      <Card className="w-full max-w-md relative z-10 glass border-white/10 shadow-2xl">
        <CardHeader className="text-center pb-2">
          {/* Animated orbital logo */}
          <div className="flex justify-center mb-6">
            <div className="relative w-20 h-20 flex items-center justify-center">
              {/* Outer orbit rings */}
              <div className="absolute inset-0 border-2 border-cosmic-cyan/30 rounded-full animate-orbit-slow" />
              <div className="absolute inset-2 border border-stellar-purple/20 rounded-full animate-orbit-reverse" />
              <div className="absolute inset-4 border border-cosmic-blue/20 rounded-full animate-orbit" style={{ animationDuration: '15s' }} />

              {/* Center icon with glow */}
              <div className="relative z-10 w-12 h-12 rounded-full bg-gradient-to-br from-cosmic-cyan to-cosmic-blue flex items-center justify-center shadow-glow-lg animate-pulse-glow">
                <Orbit className="h-6 w-6 text-white" />
              </div>

              {/* Orbiting dots */}
              <div className="absolute w-2 h-2 rounded-full bg-cosmic-cyan shadow-glow-cyan animate-orbit" style={{ top: '-4px', left: '50%', marginLeft: '-4px' }} />
              <div className="absolute w-1.5 h-1.5 rounded-full bg-stellar-purple shadow-glow-purple animate-orbit-reverse" style={{ top: '50%', right: '-4px', marginTop: '-3px' }} />
            </div>
          </div>

          <CardTitle className="text-3xl font-display font-bold">
            <span className="text-gradient-cosmic">SpOC</span>
          </CardTitle>
          <CardDescription className="text-base">
            {view === 'login' && 'UCT Algorithm Benchmarking Platform'}
            {view === 'signup' && 'Create your account'}
            {view === 'forgot-password' && 'Reset your password'}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6 pt-4">
          {/* Demo mode section */}
          {isDemoMode && view === 'login' && (
            <>
              {/* Prominent demo banner */}
              <div className="rounded-lg border border-cosmic-cyan/30 bg-cosmic-cyan/5 p-4 space-y-2">
                <div className="flex items-center gap-2 text-cosmic-cyan font-semibold text-sm">
                  <ShieldCheck className="h-4 w-4" />
                  Demo Mode
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  This is a demonstration instance with mock authentication.
                  No real credentials are required. Click below to enter as a demo user.
                </p>
                <div className="flex items-center gap-3 pt-1 text-xs text-muted-foreground/70">
                  <span className="flex items-center gap-1">
                    <div className="h-1.5 w-1.5 rounded-full bg-green-400" />
                    Mock SSO
                  </span>
                  <span className="flex items-center gap-1">
                    <div className="h-1.5 w-1.5 rounded-full bg-green-400" />
                    Synthetic Data
                  </span>
                  <span className="flex items-center gap-1">
                    <div className="h-1.5 w-1.5 rounded-full bg-green-400" />
                    Full Platform Access
                  </span>
                </div>
              </div>

              {/* SSO Button */}
              <Button
                onClick={handleDemoSSO}
                className="w-full h-12 bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity shadow-glow-cyan font-semibold text-base"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Authenticating...
                  </>
                ) : (
                  <>
                    <ShieldCheck className="mr-2 h-5 w-5" />
                    Sign in with SSO
                  </>
                )}
              </Button>

              {/* Demo user hint */}
              <p className="text-center text-xs text-muted-foreground/50">
                You will be signed in as Demo User (demo@spoc-benchmark.org)
              </p>
            </>
          )}

          {/* Error display */}
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <p>{error}</p>
            </div>
          )}

          {/* Success display */}
          {successMessage && (
            <div className="flex items-center gap-2 rounded-lg border border-green-500/50 bg-green-500/10 p-3 text-sm text-green-400">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <p>{successMessage}</p>
            </div>
          )}

          {/* Production Login View */}
          {!isDemoMode && view === 'login' && (
            <>
              {/* Email/Password Form */}
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-sm font-medium">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="researcher@aerospace.org"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50 focus:ring-cosmic-cyan/20 placeholder:text-muted-foreground/50"
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password" className="text-sm font-medium">Password</Label>
                    <button
                      type="button"
                      onClick={() => switchView('forgot-password')}
                      className="text-sm text-cosmic-cyan hover:text-cosmic-cyan/80 transition-colors"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50 focus:ring-cosmic-cyan/20"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity shadow-glow-cyan font-semibold"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Signing in...
                    </>
                  ) : (
                    'Sign in'
                  )}
                </Button>
              </form>
            </>
          )}

          {/* Signup View */}
          {view === 'signup' && (
            <>
              <form onSubmit={handleSignup} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="signup-email" className="text-sm font-medium">Email</Label>
                  <Input
                    id="signup-email"
                    type="email"
                    placeholder="researcher@aerospace.org"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50 focus:ring-cosmic-cyan/20 placeholder:text-muted-foreground/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="signup-password" className="text-sm font-medium">Password</Label>
                  <Input
                    id="signup-password"
                    type="password"
                    placeholder="Min. 6 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={6}
                    className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50 focus:ring-cosmic-cyan/20 placeholder:text-muted-foreground/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="signup-confirm" className="text-sm font-medium">Confirm Password</Label>
                  <Input
                    id="signup-confirm"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    minLength={6}
                    className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50 focus:ring-cosmic-cyan/20"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity shadow-glow-cyan font-semibold"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating account...
                    </>
                  ) : (
                    'Create Account'
                  )}
                </Button>
              </form>
            </>
          )}

          {/* Forgot Password View */}
          {view === 'forgot-password' && (
            <>
              <form onSubmit={handleForgotPassword} className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Enter your email address and we will send you a link to reset your password.
                </p>
                <div className="space-y-2">
                  <Label htmlFor="reset-email" className="text-sm font-medium">Email</Label>
                  <Input
                    id="reset-email"
                    type="email"
                    placeholder="researcher@aerospace.org"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50 focus:ring-cosmic-cyan/20 placeholder:text-muted-foreground/50"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity shadow-glow-cyan font-semibold"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    'Send Reset Link'
                  )}
                </Button>
              </form>
              <button
                type="button"
                onClick={() => switchView('login')}
                className="flex items-center gap-1 text-sm text-cosmic-cyan hover:text-cosmic-cyan/80 transition-colors mx-auto"
              >
                <ArrowLeft className="h-3 w-3" />
                Back to sign in
              </button>
            </>
          )}
        </CardContent>

        {!isDemoMode && (
          <CardFooter className="flex justify-center pt-2">
            {view === 'login' && (
              <p className="text-sm text-muted-foreground">
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => switchView('signup')}
                  className="text-cosmic-cyan hover:text-cosmic-cyan/80 font-medium transition-colors"
                >
                  Sign up
                </button>
              </p>
            )}
            {view === 'signup' && (
              <p className="text-sm text-muted-foreground">
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => switchView('login')}
                  className="text-cosmic-cyan hover:text-cosmic-cyan/80 font-medium transition-colors"
                >
                  Sign in
                </button>
              </p>
            )}
          </CardFooter>
        )}
      </Card>

      {/* Version tag */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-muted-foreground/50">
        SpOC v1.0.0
      </div>
    </div>
  );
}
// build-bust: 1774626352
