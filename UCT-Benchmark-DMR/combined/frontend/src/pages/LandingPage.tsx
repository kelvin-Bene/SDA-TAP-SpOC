import { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/components/theme-provider';
import {
  Orbit,
  Database,
  Upload,
  BarChart3,
  Trophy,
  FlaskConical,
  Globe2,
  Satellite,
  Radio,
  ChevronDown,
  ArrowRight,
  Layers,
  Target,
  Cpu,
  Braces,
  ServerCog,
  HardDrive,
  Rocket,
  Shield,
  Zap,
  Eye,
  FileBarChart,
  Network,
  Binary,
  ScanLine,
  CircleDot,
  Lock,
  Sun,
  Moon,
  Monitor,
} from 'lucide-react';

/* ─────────────────────────────────────────────
   INTERSECTION OBSERVER HOOK
   ───────────────────────────────────────────── */
function useInView(options?: IntersectionObserverInit) {
  const ref = useRef<HTMLDivElement>(null);
  const [isInView, setIsInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsInView(true);
        obs.unobserve(el);
      }
    }, options);
    obs.observe(el);
    return () => obs.disconnect();
  }, [options]);

  return { ref, isInView };
}

/* ─────────────────────────────────────────────
   SCROLL PROGRESS HOOK
   ───────────────────────────────────────────── */
function useScrollProgress(containerRef: React.RefObject<HTMLDivElement | null>) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const windowH = window.innerHeight;
      const elTop = rect.top;
      const elH = rect.height;
      const rawProgress = (windowH - elTop) / (elH + windowH);
      setProgress(Math.min(Math.max(rawProgress, 0), 1));
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [containerRef]);

  return progress;
}

/* ─────────────────────────────────────────────
   ANIMATED COUNTER
   ───────────────────────────────────────────── */
function AnimatedCounter({ end, suffix = '', duration = 2000 }: { end: number; suffix?: string; duration?: number }) {
  const [count, setCount] = useState(0);
  const { ref, isInView } = useInView({ threshold: 0.5 });

  useEffect(() => {
    if (!isInView) return;
    let start = 0;
    const step = end / (duration / 16);
    const timer = setInterval(() => {
      start += step;
      if (start >= end) {
        setCount(end);
        clearInterval(timer);
      } else {
        setCount(Math.floor(start));
      }
    }, 16);
    return () => clearInterval(timer);
  }, [isInView, end, duration]);

  return <span ref={ref as React.RefObject<HTMLSpanElement>}>{count}{suffix}</span>;
}

/* ─────────────────────────────────────────────
   ORBITAL HERO ANIMATION (SVG)
   ───────────────────────────────────────────── */
function OrbitalGraphic() {
  return (
    <div className="relative w-[420px] h-[420px] md:w-[520px] md:h-[520px] mx-auto select-none" aria-hidden="true">
      {/* Outer ring */}
      <svg className="absolute inset-0 w-full h-full animate-orbit-slow" viewBox="0 0 520 520" fill="none">
        <ellipse cx="260" cy="260" rx="250" ry="250" stroke="url(#ring1)" strokeWidth="1" opacity="0.4" />
        <defs>
          <linearGradient id="ring1" x1="0" y1="0" x2="520" y2="520">
            <stop offset="0%" stopColor="hsl(192 91% 52%)" />
            <stop offset="100%" stopColor="hsl(265 89% 66%)" />
          </linearGradient>
        </defs>
      </svg>

      {/* Middle ring – tilted */}
      <svg className="absolute inset-0 w-full h-full animate-orbit-reverse" viewBox="0 0 520 520" fill="none" style={{ transform: 'rotateX(60deg)' }}>
        <ellipse cx="260" cy="260" rx="200" ry="200" stroke="hsl(192 91% 52% / 0.25)" strokeWidth="1" strokeDasharray="8 6" />
      </svg>

      {/* Inner ring */}
      <svg className="absolute inset-0 w-full h-full" style={{ animation: 'orbit 15s linear infinite reverse' }} viewBox="0 0 520 520" fill="none">
        <ellipse cx="260" cy="260" rx="140" ry="140" stroke="hsl(265 89% 66% / 0.2)" strokeWidth="1" />
      </svg>

      {/* Orbiting satellites */}
      <div className="absolute w-3 h-3 rounded-full bg-cosmic-cyan shadow-glow-cyan animate-orbit" style={{ top: '2%', left: '50%', marginLeft: '-6px' }} />
      <div className="absolute w-2 h-2 rounded-full bg-stellar-purple shadow-glow-purple animate-orbit-reverse" style={{ top: '50%', right: '5%', marginTop: '-4px' }} />
      <div className="absolute w-2.5 h-2.5 rounded-full bg-nova-orange" style={{ bottom: '12%', left: '18%', animation: 'orbit 18s linear infinite' }} />
      <div className="absolute w-1.5 h-1.5 rounded-full bg-aurora-green" style={{ top: '22%', left: '14%', animation: 'orbit-reverse 22s linear infinite' }} />

      {/* Center globe */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative w-32 h-32 md:w-40 md:h-40 rounded-full bg-gradient-to-br from-cosmic-blue/30 via-space-deep to-stellar-purple/20 border border-white/10 flex items-center justify-center shadow-glow-lg overflow-hidden">
          {/* Globe grid lines */}
          <svg className="absolute inset-0 w-full h-full opacity-20" viewBox="0 0 160 160">
            <ellipse cx="80" cy="80" rx="70" ry="70" fill="none" stroke="hsl(192 91% 52%)" strokeWidth="0.5" />
            <ellipse cx="80" cy="80" rx="40" ry="70" fill="none" stroke="hsl(192 91% 52%)" strokeWidth="0.5" />
            <ellipse cx="80" cy="80" rx="70" ry="40" fill="none" stroke="hsl(192 91% 52%)" strokeWidth="0.5" />
            <line x1="10" y1="80" x2="150" y2="80" stroke="hsl(192 91% 52%)" strokeWidth="0.5" />
            <line x1="80" y1="10" x2="80" y2="150" stroke="hsl(192 91% 52%)" strokeWidth="0.5" />
          </svg>
          <Globe2 className="w-14 h-14 md:w-16 md:h-16 text-cosmic-cyan/70 relative z-10" />
        </div>
      </div>

      {/* Pulsing detection points */}
      <div className="absolute w-2 h-2 rounded-full bg-cosmic-cyan/80 animate-pulse-glow" style={{ top: '35%', left: '28%' }} />
      <div className="absolute w-1.5 h-1.5 rounded-full bg-aurora-green/80 animate-pulse-glow" style={{ top: '60%', right: '25%', animationDelay: '1s' }} />
      <div className="absolute w-1.5 h-1.5 rounded-full bg-nova-orange/80 animate-pulse-glow" style={{ top: '25%', right: '32%', animationDelay: '2s' }} />
    </div>
  );
}

/* ─────────────────────────────────────────────
   PIPELINE STEP COMPONENT
   ───────────────────────────────────────────── */
interface PipelineStepProps {
  index: number;
  title: string;
  description: string;
  details: React.ReactNode;
  icon: React.ReactNode;
  accentColor: string;
  glowClass: string;
}

function PipelineStep({ index, title, description, details, icon, accentColor, glowClass }: PipelineStepProps) {
  const { ref, isInView } = useInView({ threshold: 0.2, rootMargin: '0px 0px -100px 0px' });

  return (
    <div ref={ref} className="relative grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-6 md:gap-10 items-start py-16 md:py-24">
      {/* Left side – step info (odd) or details (even) */}
      <div
        className={`${index % 2 === 0 ? 'md:order-1' : 'md:order-3 md:text-right'} transition-all duration-700 ${
          isInView ? 'opacity-100 translate-x-0' : index % 2 === 0 ? 'opacity-0 -translate-x-12' : 'opacity-0 translate-x-12'
        }`}
      >
        <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono tracking-wider uppercase mb-4 ${accentColor} bg-white/5 border border-white/10`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
          Phase {String(index + 1).padStart(2, '0')}
        </div>
        <h3 className="font-display text-2xl md:text-3xl font-bold text-foreground mb-3">{title}</h3>
        <p className="text-muted-foreground text-base md:text-lg leading-relaxed max-w-md">{description}</p>
      </div>

      {/* Center – icon node */}
      <div className="hidden md:flex flex-col items-center order-2">
        <div
          className={`relative w-16 h-16 rounded-2xl flex items-center justify-center border border-white/20 transition-all duration-700 ${glowClass} ${
            isInView ? 'opacity-100 scale-100' : 'opacity-0 scale-75'
          }`}
          style={{ background: 'hsl(222 47% 7%)' }}
        >
          {icon}
          {/* Ping effect */}
          <div className={`absolute inset-0 rounded-2xl border ${accentColor.includes('cyan') ? 'border-cosmic-cyan/40' : accentColor.includes('purple') ? 'border-stellar-purple/40' : accentColor.includes('green') ? 'border-aurora-green/40' : accentColor.includes('orange') ? 'border-nova-orange/40' : 'border-cosmic-blue/40'} ${isInView ? 'animate-ping' : ''}`} style={{ animationIterationCount: 1, animationDuration: '1s' }} />
        </div>
      </div>

      {/* Right side – details */}
      <div
        className={`${index % 2 === 0 ? 'md:order-3' : 'md:order-1'} transition-all duration-700 delay-200 ${
          isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
        }`}
      >
        {details}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   FEATURE CARD
   ───────────────────────────────────────────── */
function FeatureCard({ icon, title, description, delay }: { icon: React.ReactNode; title: string; description: string; delay: number }) {
  const { ref, isInView } = useInView({ threshold: 0.2 });

  return (
    <div
      ref={ref}
      className={`group relative overflow-hidden rounded-xl border border-white/10 bg-white/[0.03] backdrop-blur-sm p-6 transition-all duration-500 hover:border-white/20 hover:bg-white/[0.06] hover:-translate-y-1 hover:shadow-card-hover ${
        isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
      }`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {/* Top glow line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cosmic-cyan/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

      <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-4 group-hover:border-cosmic-cyan/30 transition-colors">
        {icon}
      </div>
      <h4 className="font-display text-lg font-semibold text-foreground mb-2">{title}</h4>
      <p className="text-muted-foreground text-sm leading-relaxed">{description}</p>
    </div>
  );
}

/* ─────────────────────────────────────────────
   DATA SOURCE CARD
   ───────────────────────────────────────────── */
function DataSourceCard({ name, type, description, delay }: { name: string; type: 'official' | 'open'; description: string; delay: number }) {
  const { ref, isInView } = useInView({ threshold: 0.3 });

  return (
    <div
      ref={ref}
      className={`relative overflow-hidden rounded-lg border border-white/10 bg-white/[0.03] p-4 transition-all duration-500 hover:border-white/20 ${
        isInView ? 'opacity-100 scale-100' : 'opacity-0 scale-95'
      }`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-sm font-semibold text-foreground">{name}</span>
            <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider ${
              type === 'official' ? 'bg-cosmic-cyan/10 text-cosmic-cyan border border-cosmic-cyan/20' : 'bg-aurora-green/10 text-aurora-green border border-aurora-green/20'
            }`}>
              {type === 'official' ? 'AUTH' : 'OPEN'}
            </span>
          </div>
          <p className="text-muted-foreground text-xs leading-relaxed">{description}</p>
        </div>
        <Radio className="w-4 h-4 text-muted-foreground/40 shrink-0 mt-1" />
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   TECH STACK ITEM
   ───────────────────────────────────────────── */
function TechItem({ icon, name, role, delay }: { icon: React.ReactNode; name: string; role: string; delay: number }) {
  const { ref, isInView } = useInView({ threshold: 0.3 });

  return (
    <div
      ref={ref}
      className={`flex flex-col items-center gap-3 transition-all duration-500 ${
        isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
      }`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <div className="w-16 h-16 rounded-2xl bg-white/[0.04] border border-white/10 flex items-center justify-center">
        {icon}
      </div>
      <div className="text-center">
        <div className="font-mono text-sm font-semibold text-foreground">{name}</div>
        <div className="text-xs text-muted-foreground">{role}</div>
      </div>
    </div>
  );
}

/* ═════════════════════════════════════════════
   LANDING PAGE
   ═════════════════════════════════════════════ */
export function LandingPage() {
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();
  const timelineRef = useRef<HTMLDivElement>(null);
  const scrollProgress = useScrollProgress(timelineRef);

  const scrollToGuide = useCallback(() => {
    document.getElementById('guide')?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  /* ── Nav bar scroll state ── */
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden">
      {/* ── FIXED NAV ── */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled ? 'bg-background/80 backdrop-blur-xl border-b border-white/10 shadow-lg shadow-black/20' : 'bg-transparent'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cosmic-cyan to-cosmic-blue flex items-center justify-center">
              <Orbit className="w-4 h-4 text-white" />
            </div>
            <span className="font-display font-bold text-lg">
              <span className="text-gradient-cosmic">SpOC</span>
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
            <a href="#guide" className="hover:text-foreground transition-colors">How It Works</a>
            <a href="#features" className="hover:text-foreground transition-colors">Features</a>
            <a href="#data-sources" className="hover:text-foreground transition-colors">Data Sources</a>
            <a href="#architecture" className="hover:text-foreground transition-colors">Architecture</a>
          </div>
          <div className="flex items-center gap-3">
            {/* Theme toggle */}
            <div className="flex items-center rounded-lg border border-white/10 bg-white/5 p-0.5">
              {([
                { value: 'light' as const, icon: Sun, label: 'Light' },
                { value: 'dark' as const, icon: Moon, label: 'Dark' },
                { value: 'system' as const, icon: Monitor, label: 'System' },
              ]).map(({ value, icon: Icon, label }) => (
                <button
                  key={value}
                  onClick={() => setTheme(value)}
                  aria-label={`${label} theme`}
                  className={`relative flex items-center justify-center w-8 h-8 rounded-md transition-all duration-200 ${
                    theme === value
                      ? 'bg-white/10 text-cosmic-cyan shadow-sm'
                      : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </button>
              ))}
            </div>

            <Button
              onClick={() => navigate('/login')}
              className="bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity shadow-glow-cyan text-sm font-semibold"
              size="sm"
            >
              <Lock className="w-3.5 h-3.5 mr-1.5" />
              Sign In
            </Button>
          </div>
        </div>
      </nav>

      {/* ── HERO SECTION ── */}
      <section className="relative min-h-screen flex flex-col items-center justify-center px-6 space-bg overflow-hidden">
        {/* Background effects */}
        <div className="starfield" aria-hidden="true" />
        <div className="fixed inset-0 grid-pattern opacity-10 pointer-events-none" aria-hidden="true" />

        {/* Nebula blurs */}
        <div className="absolute top-1/4 left-1/6 w-[500px] h-[500px] bg-cosmic-cyan/5 rounded-full blur-[120px] animate-float" />
        <div className="absolute bottom-1/4 right-1/6 w-[400px] h-[400px] bg-stellar-purple/5 rounded-full blur-[100px] animate-float" style={{ animationDelay: '3s' }} />

        <div className="relative z-10 max-w-6xl w-full mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-center pt-20">
          {/* Left – copy */}
          <div className="text-center lg:text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-mono text-muted-foreground mb-6 animate-slide-up">
              <Shield className="w-3 h-3 text-cosmic-cyan" />
              SDA TAP Lab &times; Space Operations Command
            </div>

            <h1 className="font-display text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6" style={{ animation: 'slide-up-fade 0.6s ease-out both', animationDelay: '0.1s' }}>
              <span className="text-gradient-cosmic">SpOC</span>
              <br />
              <span className="text-foreground/90 text-3xl sm:text-4xl md:text-5xl font-semibold">UCT Benchmarking</span>
              <br />
              <span className="text-muted-foreground text-2xl sm:text-3xl md:text-4xl font-normal">Platform</span>
            </h1>

            <p className="text-muted-foreground text-lg md:text-xl max-w-xl leading-relaxed mb-8" style={{ animation: 'slide-up-fade 0.6s ease-out both', animationDelay: '0.25s' }}>
              The standard benchmark for Uncorrelated Track Processing. Generate datasets from real space surveillance data, submit algorithms, and compare performance across orbital regimes.
            </p>

            <div className="flex flex-wrap gap-4 justify-center lg:justify-start" style={{ animation: 'slide-up-fade 0.6s ease-out both', animationDelay: '0.4s' }}>
              <Button
                onClick={scrollToGuide}
                size="lg"
                className="bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity shadow-glow-cyan font-semibold text-base px-8"
              >
                Get Started
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
              <Button
                onClick={() => navigate('/login')}
                variant="outline"
                size="lg"
                className="border-white/20 bg-white/5 hover:bg-white/10 hover:border-white/30 font-semibold text-base px-8"
              >
                Sign In
              </Button>
            </div>

            {/* Metrics strip */}
            <div className="flex gap-8 mt-12 justify-center lg:justify-start" style={{ animation: 'slide-up-fade 0.6s ease-out both', animationDelay: '0.55s' }}>
              {[
                { value: 8, suffix: '+', label: 'Data Sources' },
                { value: 4, suffix: '', label: 'Data Tiers' },
                { value: 26, suffix: '', label: 'DB Tables' },
              ].map((m) => (
                <div key={m.label} className="text-center lg:text-left">
                  <div className="font-display text-2xl font-bold text-foreground">
                    <AnimatedCounter end={m.value} suffix={m.suffix} />
                  </div>
                  <div className="text-xs text-muted-foreground font-mono uppercase tracking-wider">{m.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Right – orbital graphic */}
          <div className="hidden lg:flex justify-center" style={{ animation: 'scale-in 0.8s ease-out both', animationDelay: '0.3s' }}>
            <OrbitalGraphic />
          </div>
        </div>

        {/* Scroll indicator */}
        <button
          onClick={scrollToGuide}
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-muted-foreground/50 hover:text-muted-foreground transition-colors z-10"
          aria-label="Scroll to learn more"
        >
          <span className="text-xs font-mono uppercase tracking-widest">Explore</span>
          <ChevronDown className="w-5 h-5 animate-float" />
        </button>
      </section>

      {/* ── SCROLL GUIDE / PIPELINE ── */}
      <section id="guide" className="relative" ref={timelineRef}>
        {/* Section header */}
        <div className="max-w-4xl mx-auto text-center px-6 pt-24 pb-8">
          <SectionLabel icon={<Rocket className="w-3.5 h-3.5" />} text="How It Works" />
          <h2 className="font-display text-3xl md:text-5xl font-bold text-foreground mt-4 mb-4">
            Mission <span className="text-gradient-cosmic">Briefing</span>
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            From raw space surveillance data to standardized algorithm evaluation — five phases to benchmark any UCT processor.
          </p>
        </div>

        {/* Timeline container */}
        <div className="relative max-w-6xl mx-auto px-6">
          {/* Vertical progress line (desktop) */}
          <div className="hidden md:block absolute left-1/2 top-0 bottom-0 w-px -translate-x-1/2">
            {/* Background line */}
            <div className="absolute inset-0 bg-white/5" />
            {/* Progress fill */}
            <div
              className="absolute top-0 left-0 w-full bg-gradient-to-b from-cosmic-cyan via-cosmic-blue to-stellar-purple transition-all duration-100"
              style={{ height: `${scrollProgress * 100}%` }}
            />
            {/* Glow dot at progress tip */}
            <div
              className="absolute left-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-cosmic-cyan shadow-glow-cyan transition-all duration-100"
              style={{ top: `${scrollProgress * 100}%`, marginTop: '-6px' }}
            />
          </div>

          {/* Pipeline Steps */}
          <PipelineStep
            index={0}
            title="Acquire Data"
            description="Pull real observations from government and open-source space surveillance networks. The pipeline connects to 8+ sources for comprehensive orbital coverage."
            icon={<Satellite className="w-7 h-7 text-cosmic-cyan" />}
            accentColor="text-cosmic-cyan"
            glowClass="shadow-glow-cyan"
            details={
              <div className="grid grid-cols-2 gap-3">
                {[
                  { name: 'UDL', desc: 'Unified Data Library', type: 'auth' as const },
                  { name: 'Space-Track', desc: 'USSPACECOM catalog', type: 'auth' as const },
                  { name: 'CelesTrak', desc: 'TLE data service', type: 'open' as const },
                  { name: 'SatNOGS', desc: 'RF observations', type: 'open' as const },
                ].map((s) => (
                  <div key={s.name} className="rounded-lg bg-white/[0.03] border border-white/10 p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs font-semibold text-foreground">{s.name}</span>
                      <span className={`text-[9px] px-1 rounded font-mono uppercase ${s.type === 'auth' ? 'bg-cosmic-cyan/10 text-cosmic-cyan' : 'bg-aurora-green/10 text-aurora-green'}`}>
                        {s.type}
                      </span>
                    </div>
                    <p className="text-muted-foreground text-[11px]">{s.desc}</p>
                  </div>
                ))}
              </div>
            }
          />

          <PipelineStep
            index={1}
            title="Generate Datasets"
            description="Transform raw observations into standardized benchmark datasets across four processing tiers — from near-real data to fully synthetic scenarios."
            icon={<Layers className="w-7 h-7 text-cosmic-blue" />}
            accentColor="text-cosmic-blue"
            glowClass="shadow-glow-blue"
            details={
              <div className="space-y-3">
                {[
                  { tier: 'T1', label: 'Light Downsampling', desc: 'Near-real density, regime-aware subsampling', color: 'bg-aurora-green/10 text-aurora-green border-aurora-green/20' },
                  { tier: 'T2', label: 'Heavy Downsampling', desc: 'Sparse data with realistic temporal gaps', color: 'bg-cosmic-blue/10 text-cosmic-blue border-cosmic-blue/20' },
                  { tier: 'T3', label: 'Observation Simulation', desc: 'Synthetic observations fill coverage gaps', color: 'bg-nova-orange/10 text-nova-orange border-nova-orange/20' },
                  { tier: 'T4', label: 'Object Simulation', desc: 'Fully synthetic orbit + observation generation', color: 'bg-red-500/10 text-red-400 border-red-500/20' },
                ].map((t) => (
                  <div key={t.tier} className="flex items-center gap-3 rounded-lg bg-white/[0.03] border border-white/10 p-3">
                    <span className={`inline-flex items-center justify-center w-9 h-9 rounded-lg border text-xs font-mono font-bold ${t.color}`}>
                      {t.tier}
                    </span>
                    <div>
                      <div className="text-sm font-semibold text-foreground">{t.label}</div>
                      <div className="text-xs text-muted-foreground">{t.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            }
          />

          <PipelineStep
            index={2}
            title="Submit Your Algorithm"
            description="Upload your UCT processor, configure pipeline parameters, and run against any benchmark dataset. Supports custom clustering, IOD, and refinement modules."
            icon={<Upload className="w-7 h-7 text-stellar-purple" />}
            accentColor="text-stellar-purple"
            glowClass="shadow-glow-purple"
            details={
              <div className="rounded-xl bg-white/[0.03] border border-white/10 p-5">
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-stellar-purple/10 border border-stellar-purple/20 flex items-center justify-center">
                      <Binary className="w-4 h-4 text-stellar-purple" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-foreground">Clustering</div>
                      <div className="text-xs text-muted-foreground font-mono">Angular DBSCAN &middot; Stone Soup MHT &middot; GNN</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-cosmic-cyan/10 border border-cosmic-cyan/20 flex items-center justify-center">
                      <Target className="w-4 h-4 text-cosmic-cyan" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-foreground">Initial Orbit Determination</div>
                      <div className="text-xs text-muted-foreground font-mono">Gauss &middot; Laplace &middot; Gooding</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-aurora-green/10 border border-aurora-green/20 flex items-center justify-center">
                      <ScanLine className="w-4 h-4 text-aurora-green" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-foreground">Refinement</div>
                      <div className="text-xs text-muted-foreground font-mono">Batch LSQ &middot; EKF &middot; UKF</div>
                    </div>
                  </div>
                </div>
              </div>
            }
          />

          <PipelineStep
            index={3}
            title="Benchmark & Evaluate"
            description="Automated evaluation pipeline scores your processor across binary classification, state vector accuracy, and observation residuals — with full PDF reports."
            icon={<BarChart3 className="w-7 h-7 text-aurora-green" />}
            accentColor="text-aurora-green"
            glowClass="shadow-[0_0_20px_-5px_hsl(142_76%_45%_/_0.5)]"
            details={
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Precision', value: '0.94', icon: <Target className="w-3.5 h-3.5" /> },
                  { label: 'Recall', value: '0.89', icon: <Eye className="w-3.5 h-3.5" /> },
                  { label: 'F1 Score', value: '0.91', icon: <Zap className="w-3.5 h-3.5" /> },
                  { label: 'Pos Error', value: '12.3km', icon: <CircleDot className="w-3.5 h-3.5" /> },
                  { label: 'Vel Error', value: '0.8m/s', icon: <Rocket className="w-3.5 h-3.5" /> },
                  { label: 'Residuals', value: '0.42"', icon: <ScanLine className="w-3.5 h-3.5" /> },
                ].map((m) => (
                  <div key={m.label} className="rounded-lg bg-white/[0.03] border border-white/10 p-3 text-center">
                    <div className="flex justify-center mb-2 text-aurora-green/60">{m.icon}</div>
                    <div className="font-mono text-lg font-bold text-foreground">{m.value}</div>
                    <div className="text-[10px] text-muted-foreground uppercase tracking-wider">{m.label}</div>
                  </div>
                ))}
              </div>
            }
          />

          <PipelineStep
            index={4}
            title="Compare on Leaderboard"
            description="See how your algorithm stacks up across orbital regimes. Filter by LEO, MEO, GEO, HEO, dataset tier, and evaluation metric."
            icon={<Trophy className="w-7 h-7 text-nova-orange" />}
            accentColor="text-nova-orange"
            glowClass="shadow-[0_0_20px_-5px_hsl(25_95%_53%_/_0.5)]"
            details={
              <div className="rounded-xl bg-white/[0.03] border border-white/10 overflow-hidden">
                {/* Fake leaderboard header */}
                <div className="grid grid-cols-[auto_1fr_auto_auto] gap-4 px-4 py-2.5 bg-white/[0.03] border-b border-white/10 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  <span>#</span><span>Algorithm</span><span>F1</span><span>Regime</span>
                </div>
                {[
                  { rank: 1, name: 'DeepTrack-v3', f1: '0.96', regime: 'LEO', color: 'text-cosmic-blue' },
                  { rank: 2, name: 'OrbitalNet', f1: '0.93', regime: 'GEO', color: 'text-nova-orange' },
                  { rank: 3, name: 'TrackFormer', f1: '0.91', regime: 'MEO', color: 'text-aurora-green' },
                ].map((r) => (
                  <div key={r.rank} className="grid grid-cols-[auto_1fr_auto_auto] gap-4 px-4 py-3 border-b border-white/5 items-center hover:bg-white/[0.02] transition-colors">
                    <span className={`font-mono text-sm font-bold ${r.rank === 1 ? 'text-nova-orange' : 'text-muted-foreground'}`}>{r.rank}</span>
                    <span className="font-mono text-sm text-foreground">{r.name}</span>
                    <span className="font-mono text-sm text-aurora-green font-semibold">{r.f1}</span>
                    <span className={`text-xs font-mono ${r.color}`}>{r.regime}</span>
                  </div>
                ))}
              </div>
            }
          />
        </div>
      </section>

      {/* ── FEATURES GRID ── */}
      <section id="features" className="relative py-24 md:py-32">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <SectionLabel icon={<Zap className="w-3.5 h-3.5" />} text="Platform Features" />
            <h2 className="font-display text-3xl md:text-5xl font-bold text-foreground mt-4 mb-4">
              Everything You <span className="text-gradient-cosmic">Need</span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              A complete environment for developing, testing, and benchmarking UCT processing algorithms.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            <FeatureCard
              icon={<Database className="w-5 h-5 text-cosmic-cyan" />}
              title="Dataset Browser"
              description="Browse, filter, and download benchmark datasets across orbital regimes and processing tiers. Preview observation windows and data quality scores."
              delay={0}
            />
            <FeatureCard
              icon={<Upload className="w-5 h-5 text-stellar-purple" />}
              title="Algorithm Submission"
              description="Upload your UCT processor with drag-and-drop. Configure clustering, IOD, and refinement parameters before running against any benchmark."
              delay={100}
            />
            <FeatureCard
              icon={<FileBarChart className="w-5 h-5 text-aurora-green" />}
              title="Evaluation Metrics"
              description="Comprehensive scoring across binary classification, orbit association via Hungarian algorithm, state vector accuracy, and residual analysis."
              delay={200}
            />
            <FeatureCard
              icon={<Trophy className="w-5 h-5 text-nova-orange" />}
              title="Leaderboard"
              description="Compare algorithms head-to-head across datasets and regimes. Filterable rankings with historical performance tracking and trend analysis."
              delay={300}
            />
            <FeatureCard
              icon={<FlaskConical className="w-5 h-5 text-cosmic-blue" />}
              title="UCTP Lab"
              description="Integrated ML pipeline with Angular DBSCAN clustering, multiple IOD methods (Gauss, Laplace, Gooding), and Kalman filter refinement."
              delay={400}
            />
            <FeatureCard
              icon={<Globe2 className="w-5 h-5 text-cosmic-cyan" />}
              title="3D Visualization"
              description="Cesium.js powered orbital viewer for visualizing datasets, satellite tracks, observation coverage, and algorithm outputs in 3D."
              delay={500}
            />
          </div>
        </div>
      </section>

      {/* ── DATA SOURCES ── */}
      <section id="data-sources" className="relative py-24 md:py-32 border-t border-white/5">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <SectionLabel icon={<Network className="w-3.5 h-3.5" />} text="Data Network" />
            <h2 className="font-display text-3xl md:text-5xl font-bold text-foreground mt-4 mb-4">
              <span className="text-gradient-cosmic">8+</span> Space Surveillance Sources
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              Authenticated government APIs and open-source satellite observation networks, unified under a single pipeline.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <DataSourceCard name="UDL" type="official" description="Unified Data Library — DoD authoritative source for space object observations" delay={0} />
            <DataSourceCard name="Space-Track" type="official" description="USSPACECOM satellite catalog with TLE and conjunction data" delay={50} />
            <DataSourceCard name="CelesTrak" type="open" description="Supplementary TLE data service with historical archives" delay={100} />
            <DataSourceCard name="ESA DiscoWeb" type="official" description="European Space Agency debris and satellite properties database" delay={150} />
            <DataSourceCard name="SatNOGS" type="open" description="Open-source satellite RF observation network with global coverage" delay={200} />
            <DataSourceCard name="GCAT" type="open" description="General Catalog of Artificial Space Objects — comprehensive metadata" delay={250} />
            <DataSourceCard name="ILRS" type="open" description="International Laser Ranging Service — sub-centimeter precision validation" delay={300} />
            <DataSourceCard name="UCS" type="open" description="Union of Concerned Scientists — satellite purpose, operator, mass metadata" delay={350} />
          </div>
        </div>
      </section>

      {/* ── ARCHITECTURE ── */}
      <section id="architecture" className="relative py-24 md:py-32 border-t border-white/5">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-16">
            <SectionLabel icon={<Cpu className="w-3.5 h-3.5" />} text="Architecture" />
            <h2 className="font-display text-3xl md:text-5xl font-bold text-foreground mt-4 mb-4">
              Built for <span className="text-gradient-cosmic">Scale</span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              Modern full-stack architecture with dual-database support and high-fidelity orbital mechanics.
            </p>
          </div>

          {/* Tech stack row */}
          <div className="flex flex-wrap justify-center gap-8 md:gap-14 mb-16">
            <TechItem icon={<Braces className="w-6 h-6 text-cosmic-cyan" />} name="React" role="Frontend" delay={0} />
            <TechItem icon={<ServerCog className="w-6 h-6 text-aurora-green" />} name="FastAPI" role="Backend" delay={100} />
            <TechItem icon={<HardDrive className="w-6 h-6 text-cosmic-blue" />} name="DuckDB" role="Dev Database" delay={200} />
            <TechItem icon={<Database className="w-6 h-6 text-stellar-purple" />} name="PostgreSQL" role="Production DB" delay={300} />
            <TechItem icon={<Orbit className="w-6 h-6 text-nova-orange" />} name="Orekit" role="Orbital Mechanics" delay={400} />
          </div>

          {/* Architecture diagram (simplified) */}
          <ArchitectureDiagram />
        </div>
      </section>

      {/* ── CTA / AUTH SECTION ── */}
      <section className="relative py-24 md:py-32 border-t border-white/5">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <CTASection navigate={navigate} />
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-white/5 py-8">
        <div className="max-w-6xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-cosmic-cyan to-cosmic-blue flex items-center justify-center">
                <Orbit className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="font-display font-bold text-sm">
                <span className="text-gradient-cosmic">SpOC</span>
                <span className="text-muted-foreground ml-2 font-normal">UCT Benchmark</span>
              </span>
            </div>
            <div className="flex items-center gap-6 text-xs text-muted-foreground">
              <span>SDA TAP Lab</span>
              <span className="w-1 h-1 rounded-full bg-muted-foreground/30" />
              <span>Space Operations Command</span>
              <span className="w-1 h-1 rounded-full bg-muted-foreground/30" />
              <span className="font-mono">v1.0.0</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

/* ─────────────────────────────────────────────
   SECTION LABEL
   ───────────────────────────────────────────── */
function SectionLabel({ icon, text }: { icon: React.ReactNode; text: string }) {
  const { ref, isInView } = useInView({ threshold: 0.5 });

  return (
    <div
      ref={ref}
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-mono text-cosmic-cyan uppercase tracking-widest transition-all duration-500 ${
        isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      }`}
    >
      {icon}
      {text}
    </div>
  );
}

/* ─────────────────────────────────────────────
   ARCHITECTURE DIAGRAM
   ───────────────────────────────────────────── */
function ArchitectureDiagram() {
  const { ref, isInView } = useInView({ threshold: 0.2 });

  return (
    <div
      ref={ref}
      className={`relative rounded-2xl border border-white/10 bg-white/[0.02] p-6 md:p-8 overflow-hidden transition-all duration-700 ${
        isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
      }`}
    >
      {/* Decorative scan line */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cosmic-cyan/30 to-transparent animate-beam" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
        {/* Frontend */}
        <div className="space-y-3">
          <div className="font-mono text-xs text-cosmic-cyan uppercase tracking-wider">Frontend</div>
          <div className="rounded-xl bg-cosmic-cyan/5 border border-cosmic-cyan/20 p-4 space-y-2">
            <div className="text-sm font-semibold text-foreground">React 18 + TypeScript</div>
            <div className="flex flex-wrap gap-1.5 justify-center">
              {['Tailwind', 'Zustand', 'React Query', 'Cesium.js'].map((t) => (
                <span key={t} className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[10px] font-mono text-muted-foreground">{t}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Backend */}
        <div className="space-y-3">
          <div className="font-mono text-xs text-aurora-green uppercase tracking-wider">Backend</div>
          <div className="rounded-xl bg-aurora-green/5 border border-aurora-green/20 p-4 space-y-2">
            <div className="text-sm font-semibold text-foreground">FastAPI + Python</div>
            <div className="flex flex-wrap gap-1.5 justify-center">
              {['Orekit', 'NumPy', 'Pandas', 'Polars'].map((t) => (
                <span key={t} className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[10px] font-mono text-muted-foreground">{t}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Database */}
        <div className="space-y-3">
          <div className="font-mono text-xs text-stellar-purple uppercase tracking-wider">Data Layer</div>
          <div className="rounded-xl bg-stellar-purple/5 border border-stellar-purple/20 p-4 space-y-2">
            <div className="text-sm font-semibold text-foreground">Dual-Backend DB</div>
            <div className="flex flex-wrap gap-1.5 justify-center">
              {['DuckDB', 'PostgreSQL', 'Supabase', 'Parquet'].map((t) => (
                <span key={t} className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[10px] font-mono text-muted-foreground">{t}</span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Connection lines (decorative) */}
      <div className="hidden md:flex items-center justify-center gap-0 mt-6 mb-2">
        <div className="h-px flex-1 bg-gradient-to-r from-cosmic-cyan/30 to-transparent" />
        <div className="w-8 h-8 rounded-full border border-white/20 bg-white/5 flex items-center justify-center mx-4">
          <Zap className="w-3.5 h-3.5 text-cosmic-cyan" />
        </div>
        <div className="h-px flex-1 bg-gradient-to-l from-stellar-purple/30 to-transparent" />
      </div>

      {/* Bottom note */}
      <div className="text-center mt-4">
        <span className="text-[11px] font-mono text-muted-foreground/60">
          26 tables &middot; Repository pattern &middot; JSON/Parquet/SQL export &middot; Supabase Auth
        </span>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   CTA SECTION
   ───────────────────────────────────────────── */
function CTASection({ navigate }: { navigate: ReturnType<typeof useNavigate> }) {
  const { ref, isInView } = useInView({ threshold: 0.2 });

  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ${isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
    >
      {/* Decorative orbital */}
      <div className="relative w-20 h-20 mx-auto mb-8">
        <div className="absolute inset-0 border border-cosmic-cyan/20 rounded-full animate-orbit-slow" />
        <div className="absolute inset-3 border border-stellar-purple/15 rounded-full animate-orbit-reverse" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cosmic-cyan to-cosmic-blue flex items-center justify-center shadow-glow-cyan animate-pulse-glow">
            <Rocket className="w-5 h-5 text-white" />
          </div>
        </div>
      </div>

      <h2 className="font-display text-3xl md:text-5xl font-bold text-foreground mb-4">
        Ready to <span className="text-gradient-cosmic">Benchmark?</span>
      </h2>
      <p className="text-muted-foreground text-lg max-w-lg mx-auto mb-8">
        Sign in to access the platform, browse datasets, submit your UCT processor, and see how it performs against the community.
      </p>

      <div className="flex flex-wrap gap-4 justify-center">
        <Button
          onClick={() => navigate('/login')}
          size="lg"
          className="bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity shadow-glow-cyan font-semibold text-base px-10"
        >
          Sign In to Platform
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
        <Button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          variant="outline"
          size="lg"
          className="border-white/20 bg-white/5 hover:bg-white/10 hover:border-white/30 font-semibold text-base"
        >
          Back to Top
        </Button>
      </div>

      {/* OAuth preview */}
      <div className="mt-8 flex items-center justify-center gap-3 text-xs text-muted-foreground/60">
        <span>Supports</span>
        <span className="flex items-center gap-1.5 px-2 py-1 rounded bg-white/5 border border-white/10">
          <svg className="h-3 w-3" viewBox="0 0 24 24">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
          </svg>
          Google
        </span>
        <span className="flex items-center gap-1.5 px-2 py-1 rounded bg-white/5 border border-white/10">
          <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
          </svg>
          GitHub
        </span>
        <span className="flex items-center gap-1.5 px-2 py-1 rounded bg-white/5 border border-white/10">
          <Lock className="w-3 h-3" />
          Email
        </span>
      </div>
    </div>
  );
}
