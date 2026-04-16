import { useState, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, AlertCircle, CheckCircle2, ArrowLeft, ShieldCheck, Eye, EyeOff } from 'lucide-react';
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
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard';

  const handleDemoSSO = async () => {
    clearError();
    await login('demo@uct-benchmark.org', 'demo');
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
    setShowPassword(false);
    setShowConfirmPassword(false);
    clearError();
    requestAnimationFrame(() => headingRef.current?.focus());
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setSuccessMessage(null);
    await login(email, password);

    const state = useAuthStore.getState();
    if (state.error) {
      return; // Error is already set in the store, LoginPage will show it
    }
    if (state.isAuthenticated) {
      navigate(from, { replace: true });
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setSuccessMessage(null);

    if (password !== confirmPassword) {
      useAuthStore.setState({ error: 'Passwords do not match.' });
      return;
    }

    if (password.length < 8) {
      useAuthStore.setState({ error: 'Password must be at least 8 characters.' });
      return;
    }

    await signup(email, password);

    const currentError = useAuthStore.getState().error;
    if (!currentError) {
      // Auto-confirm is enabled — session already exists, navigate directly
      navigate(from, { replace: true });
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
    <div className="min-h-screen sm:min-h-dvh flex items-center justify-center p-4 space-bg relative overflow-hidden">
      {/* Animated starfield */}
      <div className="starfield" aria-hidden="true" />

      {/* Grid pattern overlay */}
      <div className="fixed inset-0 grid-pattern opacity-20 pointer-events-none" aria-hidden="true" />

      {/* Floating orbs - hidden on mobile for perf */}
      <div className="hidden sm:block motion-reduce:hidden absolute top-1/4 left-1/4 w-96 h-96 bg-cosmic-cyan/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '0s' }} />
      <div className="hidden sm:block motion-reduce:hidden absolute bottom-1/4 right-1/4 w-80 h-80 bg-stellar-purple/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
      <div className="hidden sm:block motion-reduce:hidden absolute top-1/2 right-1/3 w-64 h-64 bg-cosmic-blue/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '4s' }} />

      <Card className="w-full max-w-md relative z-10 glass border-white/10 shadow-2xl">
        <CardHeader className="text-center pb-2">
          {/* Organization logos */}
          <div className="flex justify-center items-center gap-2 sm:gap-3 mb-4 sm:mb-6">
            <div className="h-12 w-12 sm:h-16 sm:w-16 rounded-lg bg-white/90 p-1 flex items-center justify-center">
              <img src="/cfc-emblem.png" alt="Combat Forces Command" className="h-full w-full object-contain" />
            </div>
            <div className="h-11 sm:h-14 rounded-lg bg-white/90 px-2 py-1 flex items-center justify-center">
              <img src="/sda-tap-lab-logo.png" alt="SDA TAP Lab" className="h-full object-contain" />
            </div>
          </div>

          <CardTitle ref={headingRef} tabIndex={-1} className="text-2xl sm:text-3xl font-display font-bold">
            <span className="text-gradient-cosmic">UCT Benchmark</span>
          </CardTitle>
          <CardDescription className="text-base">
            {view === 'login' && 'UCT Benchmark Platform'}
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
                type="button"
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
                You will be signed in as Demo User (demo@uct-benchmark.org)
              </p>
            </>
          )}

          {/* Error display */}
          {error && (
            <div role="alert" aria-live="assertive" className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
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
                    autoComplete="email"
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
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50 focus:ring-cosmic-cyan/20 pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
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
                    autoComplete="email"
                    placeholder="researcher@aerospace.org"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50 focus:ring-cosmic-cyan/20 placeholder:text-muted-foreground/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="signup-password" className="text-sm font-medium">Password</Label>
                  <div className="relative">
                    <Input
                      id="signup-password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      placeholder="Min. 8 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50 focus:ring-cosmic-cyan/20 placeholder:text-muted-foreground/50 pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="signup-confirm" className="text-sm font-medium">Confirm Password</Label>
                  <div className="relative">
                    <Input
                      id="signup-confirm"
                      type={showConfirmPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50 focus:ring-cosmic-cyan/20 pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    >
                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
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
                    autoComplete="email"
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
        v{__APP_VERSION__}
      </div>
    </div>
  );
}
// build-bust: 1774626352
