import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Orbit, Loader2, AlertCircle } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

export function LoginPage() {
  const navigate = useNavigate();
  const { joinAsGuest, isLoading, isAuthenticated, error, clearError } = useAuthStore();

  const [callsign, setCallsign] = useState('');

  // Navigate to home after successful join
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    await joinAsGuest(callsign.trim());
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
            UCTP Benchmark Platform
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

          <p className="text-center text-sm text-muted-foreground">
            Enter your callsign to join the demo
          </p>

          <form onSubmit={handleJoin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="callsign" className="text-sm font-medium">Callsign</Label>
              <Input
                id="callsign"
                type="text"
                placeholder="e.g. Orbital-7"
                value={callsign}
                onChange={(e) => setCallsign(e.target.value)}
                required
                autoFocus
                className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50 focus:ring-cosmic-cyan/20 placeholder:text-muted-foreground/50"
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity shadow-glow-cyan font-semibold"
              disabled={isLoading || !callsign.trim()}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Joining...
                </>
              ) : (
                'Join'
              )}
            </Button>
          </form>
        </CardContent>

        <CardFooter className="flex justify-center pt-2">
          <p className="text-xs text-muted-foreground/70 text-center">
            Demo mode — scores are simulated to demonstrate the evaluation pipeline
          </p>
        </CardFooter>
      </Card>

      {/* Version tag */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-muted-foreground/50">
        SpOC v1.0.0
      </div>
    </div>
  );
}
