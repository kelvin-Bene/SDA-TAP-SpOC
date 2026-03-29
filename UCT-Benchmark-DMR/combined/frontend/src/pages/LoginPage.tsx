import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Orbit, Loader2, AlertCircle, CheckCircle2, ArrowLeft } from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { useAuthStore } from '@/stores/authStore';

type AuthView = 'login' | 'signup' | 'forgot-password';

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loginWithOAuth, signup, resetPassword, isLoading, error, clearError } = useAuthStore();

  const [view, setView] = useState<AuthView>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

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
            {view === 'login' && 'UCTP Algorithm Benchmarking Platform'}
            {view === 'signup' && 'Create your account'}
            {view === 'forgot-password' && 'Reset your password'}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6 pt-4">
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

          {/* Login View */}
          {view === 'login' && (
            <>
              {/* OAuth Buttons */}
              <div className="grid grid-cols-2 gap-3">
                <Button
                  type="button"
                  variant="outline"
                  className="bg-white text-gray-800 border-white/20 hover:bg-gray-100 font-medium"
                  disabled={isLoading}
                  onClick={() => loginWithOAuth('google')}
                >
                  <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                    <path
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                      fill="#4285F4"
                    />
                    <path
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      fill="#34A853"
                    />
                    <path
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                      fill="#FBBC05"
                    />
                    <path
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                      fill="#EA4335"
                    />
                  </svg>
                  Google
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="bg-[#24292f] text-white border-white/20 hover:bg-[#32383f] font-medium"
                  disabled={isLoading}
                  onClick={() => loginWithOAuth('github')}
                >
                  <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z" />
                  </svg>
                  GitHub
                </Button>
              </div>

              {/* Separator */}
              <div className="relative">
                <Separator className="bg-white/10" />
                <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-card px-3 text-xs text-muted-foreground">
                  Or continue with email
                </span>
              </div>

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
      </Card>

      {/* Version tag */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-muted-foreground/50">
        SpOC v1.0.0
      </div>
    </div>
  );
}
