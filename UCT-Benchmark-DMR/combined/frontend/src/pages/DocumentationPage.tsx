import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { StepExplainer } from '@/components/ui/info-popover';
import {
  Code,
  FileJson,
  BarChart3,
  Rocket,
  Orbit,
  Satellite,
  Target,
  Database,
  Layers,
  ArrowRight,
  BookOpen,
  ChevronDown,
  Sparkles,
  Shield,
  FlaskConical,
  Radio,
  Waves,
  GitBranch,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Copy,
  Check,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/* ------------------------------------------------------------------ */
/*  Collapsible Section                                                 */
/* ------------------------------------------------------------------ */

function CollapsibleSection({ title, children, defaultOpen = false, icon: Icon }: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  icon?: React.ElementType;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-white/10 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-white/[0.02] transition-colors text-left"
      >
        {Icon && <Icon className="h-4 w-4 text-cosmic-cyan flex-shrink-0" />}
        <span className="flex-1 font-semibold text-sm">{title}</span>
        <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform duration-200', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="px-5 pb-5 pt-0 border-t border-white/5">
          {children}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Code Block with copy                                                */
/* ------------------------------------------------------------------ */

function CodeBlock({ code, language = 'json' }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group rounded-xl border border-white/10 bg-black/30 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-white/[0.02]">
        <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
        >
          {copied ? <Check className="h-3 w-3 text-aurora-green" /> : <Copy className="h-3 w-3" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-xs font-mono text-muted-foreground leading-relaxed">
        {code}
      </pre>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Concept Card                                                        */
/* ------------------------------------------------------------------ */

function ConceptCard({ title, description, icon: Icon, color, badge, children }: {
  title: string;
  description: string;
  icon: React.ElementType;
  color: string;
  badge?: string;
  children?: React.ReactNode;
}) {
  const colorMap: Record<string, { border: string; bg: string; text: string; iconBg: string }> = {
    cyan: { border: 'border-cosmic-cyan/20', bg: 'bg-cosmic-cyan/5', text: 'text-cosmic-cyan', iconBg: 'bg-cosmic-cyan/10' },
    purple: { border: 'border-stellar-purple/20', bg: 'bg-stellar-purple/5', text: 'text-stellar-purple', iconBg: 'bg-stellar-purple/10' },
    blue: { border: 'border-cosmic-blue/20', bg: 'bg-cosmic-blue/5', text: 'text-cosmic-blue', iconBg: 'bg-cosmic-blue/10' },
    green: { border: 'border-aurora-green/20', bg: 'bg-aurora-green/5', text: 'text-aurora-green', iconBg: 'bg-aurora-green/10' },
    orange: { border: 'border-nova-orange/20', bg: 'bg-nova-orange/5', text: 'text-nova-orange', iconBg: 'bg-nova-orange/10' },
  };
  const c = colorMap[color] || colorMap.cyan;

  return (
    <div className={cn('rounded-xl border p-5 space-y-3', c.border, c.bg)}>
      <div className="flex items-center gap-3">
        <div className={cn('p-2 rounded-lg', c.iconBg)}>
          <Icon className={cn('h-4 w-4', c.text)} />
        </div>
        <div className="flex-1">
          <h4 className="font-semibold text-sm">{title}</h4>
          {badge && <Badge className={cn('text-[10px] mt-0.5', c.text, c.iconBg)}>{badge}</Badge>}
        </div>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Metric Explainer Card                                               */
/* ------------------------------------------------------------------ */

function MetricCard({ name, formula, description, interpretation }: {
  name: string;
  formula: string;
  description: string;
  interpretation: string;
}) {
  return (
    <div className="rounded-xl border border-white/10 p-4 space-y-2 hover:border-white/20 transition-colors">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-sm">{name}</h4>
        <code className="text-[10px] font-mono bg-white/5 px-2 py-0.5 rounded text-cosmic-cyan">{formula}</code>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
      <div className="flex items-start gap-2 rounded-lg bg-white/[0.03] border border-white/5 p-2.5">
        <Target className="h-3 w-3 text-aurora-green mt-0.5 flex-shrink-0" />
        <p className="text-xs text-muted-foreground">{interpretation}</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Documentation Page                                             */
/* ------------------------------------------------------------------ */

export function DocumentationPage() {
  return (
    <div className="space-y-6">
      {/* ── Page Header ─────────────────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-stellar-purple/5 via-transparent to-cosmic-cyan/5 p-6 sm:p-8">
        <div className="absolute top-0 right-0 w-72 h-72 bg-stellar-purple/8 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-cosmic-cyan/8 rounded-full blur-3xl translate-y-1/3 -translate-x-1/4" />
        <div className="relative z-10">
          <div className="flex items-center gap-2 text-stellar-purple text-sm font-medium mb-2">
            <BookOpen className="h-4 w-4" />
            Documentation
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-bold tracking-tight">
            Learn the <span className="text-gradient-cosmic">Platform</span>
          </h1>
          <p className="text-muted-foreground mt-2 max-w-2xl">
            Everything you need to understand the UI UCTP Benchmark Platform &mdash; from
            generating datasets to interpreting evaluation metrics.
          </p>
        </div>
      </div>

      {/* ── Tabs ─────────────────────────────────────────────────── */}
      <Tabs defaultValue="getting-started" className="space-y-6">
        <TabsList className="flex-wrap h-auto gap-2 bg-white/5 p-1.5 rounded-xl border border-white/10">
          <TabsTrigger value="getting-started" className="gap-2 rounded-lg data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan">
            <Rocket className="h-4 w-4" />
            Getting Started
          </TabsTrigger>
          <TabsTrigger value="key-concepts" className="gap-2 rounded-lg data-[state=active]:bg-stellar-purple/10 data-[state=active]:text-stellar-purple">
            <BookOpen className="h-4 w-4" />
            Key Concepts
          </TabsTrigger>
          <TabsTrigger value="dataset-format" className="gap-2 rounded-lg data-[state=active]:bg-cosmic-blue/10 data-[state=active]:text-cosmic-blue">
            <FileJson className="h-4 w-4" />
            Data Formats
          </TabsTrigger>
          <TabsTrigger value="metrics" className="gap-2 rounded-lg data-[state=active]:bg-aurora-green/10 data-[state=active]:text-aurora-green">
            <BarChart3 className="h-4 w-4" />
            Evaluation Metrics
          </TabsTrigger>
        </TabsList>

        {/* ─── Getting Started ───────────────────────────────────── */}
        <TabsContent value="getting-started" className="space-y-6">
          {/* Quick Start Steps */}
          <Card className="border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Rocket className="h-5 w-5 text-cosmic-cyan" />
                Quick Start Guide
              </CardTitle>
              <CardDescription>
                Five steps to evaluate your UCTP processing algorithm
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  {
                    step: 1,
                    title: 'Generate a Dataset',
                    desc: 'Navigate to Datasets > Generate and configure your benchmark parameters. Start with the Standard preset for balanced testing.',
                    link: '/datasets/generate',
                    linkLabel: 'Go to Generator',
                    color: 'cyan',
                  },
                  {
                    step: 2,
                    title: 'Download the Dataset',
                    desc: 'Once generated, download the JSON file containing observations (angles-only measurements) and the truth catalog (known orbits).',
                    link: '/datasets',
                    linkLabel: 'Browse Datasets',
                    color: 'purple',
                  },
                  {
                    step: 3,
                    title: 'Run Your Algorithm',
                    desc: 'Process the observations with your UCTP algorithm to produce track associations and state estimates for each identified object.',
                    color: 'blue',
                  },
                  {
                    step: 4,
                    title: 'Submit Results',
                    desc: 'Upload your algorithm output through the Submit page. The system validates your JSON and runs the evaluation pipeline automatically.',
                    link: '/submit',
                    linkLabel: 'Submit Results',
                    color: 'green',
                  },
                  {
                    step: 5,
                    title: 'View Results & Compare',
                    desc: 'See detailed metrics (F1-Score, precision, recall, position RMS) and compare against the leaderboard to benchmark your algorithm.',
                    link: '/leaderboard',
                    linkLabel: 'View Leaderboard',
                    color: 'orange',
                  },
                ].map((item) => {
                  const colorMap: Record<string, string> = {
                    cyan: 'border-cosmic-cyan/20 bg-cosmic-cyan/5',
                    purple: 'border-stellar-purple/20 bg-stellar-purple/5',
                    blue: 'border-cosmic-blue/20 bg-cosmic-blue/5',
                    green: 'border-aurora-green/20 bg-aurora-green/5',
                    orange: 'border-nova-orange/20 bg-nova-orange/5',
                  };
                  const numColor: Record<string, string> = {
                    cyan: 'bg-cosmic-cyan/15 text-cosmic-cyan border-cosmic-cyan/30',
                    purple: 'bg-stellar-purple/15 text-stellar-purple border-stellar-purple/30',
                    blue: 'bg-cosmic-blue/15 text-cosmic-blue border-cosmic-blue/30',
                    green: 'bg-aurora-green/15 text-aurora-green border-aurora-green/30',
                    orange: 'bg-nova-orange/15 text-nova-orange border-nova-orange/30',
                  };

                  return (
                    <div key={item.step} className={cn('rounded-xl border p-4 flex gap-4', colorMap[item.color])}>
                      <div className={cn('flex-shrink-0 w-8 h-8 rounded-lg border flex items-center justify-center font-display font-bold text-sm', numColor[item.color])}>
                        {item.step}
                      </div>
                      <div className="flex-1 space-y-1">
                        <h4 className="font-semibold text-sm">{item.title}</h4>
                        <p className="text-xs text-muted-foreground leading-relaxed">{item.desc}</p>
                        {item.link && (
                          <Link to={item.link} className="inline-flex items-center gap-1 text-xs font-medium text-cosmic-cyan hover:underline mt-1">
                            {item.linkLabel} <ArrowRight className="h-3 w-3" />
                          </Link>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* UCTPP Lab Intro */}
          <Card className="border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FlaskConical className="h-5 w-5 text-stellar-purple" />
                UCTPP Algorithm Lab
              </CardTitle>
              <CardDescription>
                Advanced tools for algorithm development and testing
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground leading-relaxed">
                The UCTPP Lab provides an integrated environment for running, testing, and comparing
                UCTP processing algorithms. It includes a visual pipeline builder, ML training studio,
                and API connectivity testing.
              </p>
              <div className="grid sm:grid-cols-3 gap-3">
                <ConceptCard
                  title="Algorithm Workbench"
                  description="Configure and run the full UCTPP pipeline: ingest, cluster, IOD, refine, output."
                  icon={FlaskConical}
                  color="cyan"
                />
                <ConceptCard
                  title="ML Training Studio"
                  description="Train neural network models to enhance clustering and propagation accuracy."
                  icon={Sparkles}
                  color="purple"
                />
                <ConceptCard
                  title="API Connectivity"
                  description="Test connections to external services like Orekit, orbdetpy, and Space-Track."
                  icon={Radio}
                  color="green"
                />
              </div>
              <Link to="/uctp">
                <Button variant="outline" className="gap-2 border-stellar-purple/30 hover:bg-stellar-purple/5">
                  <FlaskConical className="h-4 w-4" />
                  Open UCTPP Lab
                </Button>
              </Link>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─── Key Concepts ──────────────────────────────────────── */}
        <TabsContent value="key-concepts" className="space-y-6">
          {/* Orbital Regimes */}
          <Card className="border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Orbit className="h-5 w-5 text-cosmic-cyan" />
                Orbital Regimes
              </CardTitle>
              <CardDescription>
                Space is divided into altitude bands, each with unique tracking characteristics
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid sm:grid-cols-2 gap-4">
                <ConceptCard
                  title="LEO - Low Earth Orbit"
                  description="200-2,000 km altitude. Home to the ISS, Starlink, and most Earth observation satellites. Objects complete an orbit every ~90 minutes, creating short observation arcs. Dense debris environment makes this the most populated regime."
                  icon={Orbit}
                  color="cyan"
                  badge="200-2,000 km"
                >
                  <div className="text-xs text-muted-foreground bg-white/[0.05] rounded-lg p-2 border border-white/5">
                    <span className="font-medium text-foreground/80">UCTP Challenge:</span> Many short tracks from fast-moving objects. Must associate observations across multiple passes.
                  </div>
                </ConceptCard>

                <ConceptCard
                  title="MEO - Medium Earth Orbit"
                  description="2,000-35,786 km altitude. Hosts navigation constellations: GPS (USA), GLONASS (Russia), Galileo (EU), BeiDou (China). Objects have 12-hour orbital periods with moderate angular rates."
                  icon={Satellite}
                  color="green"
                  badge="2,000-35,786 km"
                >
                  <div className="text-xs text-muted-foreground bg-white/[0.05] rounded-lg p-2 border border-white/5">
                    <span className="font-medium text-foreground/80">UCTP Challenge:</span> Moderate dynamics. Longer observation arcs but fewer objects per sensor field of view.
                  </div>
                </ConceptCard>

                <ConceptCard
                  title="GEO - Geostationary Orbit"
                  description="~35,786 km altitude. Communications and weather satellites appear nearly stationary from ground. Objects are clustered in narrow longitude 'slots', making angular discrimination difficult."
                  icon={Radio}
                  color="orange"
                  badge="~35,786 km"
                >
                  <div className="text-xs text-muted-foreground bg-white/[0.05] rounded-lg p-2 border border-white/5">
                    <span className="font-medium text-foreground/80">UCTP Challenge:</span> Faint targets clustered in longitude slots. Must resolve closely-spaced objects at extreme range.
                  </div>
                </ConceptCard>

                <ConceptCard
                  title="HEO - Highly Elliptical Orbit"
                  description="Variable altitude from low perigee to high apogee. Molniya and Tundra orbits provide extended dwell time over high-latitude regions. Extreme orbital eccentricity creates unique dynamics."
                  icon={Waves}
                  color="purple"
                  badge="Variable altitude"
                >
                  <div className="text-xs text-muted-foreground bg-white/[0.05] rounded-lg p-2 border border-white/5">
                    <span className="font-medium text-foreground/80">UCTP Challenge:</span> Complex non-circular dynamics. Observation geometry changes dramatically across the orbit.
                  </div>
                </ConceptCard>
              </div>
            </CardContent>
          </Card>

          {/* Data Tiers */}
          <Card className="border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers className="h-5 w-5 text-stellar-purple" />
                Data Tiers
              </CardTitle>
              <CardDescription>
                Benchmark datasets are categorized by data quality and origin
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  {
                    tier: 'T1',
                    name: 'Pristine',
                    desc: 'Full-quality real observations with no modifications. The most realistic benchmark scenario.',
                    color: 'aurora-green',
                    detail: 'T1 data comes directly from sensor feeds with all observations intact. This tests how your algorithm handles production-quality data.',
                  },
                  {
                    tier: 'T1H',
                    name: 'Validated (ILRS)',
                    desc: 'Highest quality tier with laser-ranging ground truth. The gold standard for algorithm validation.',
                    color: 'stellar-purple',
                    detail: 'T1H includes ILRS laser-ranging data that provides sub-centimeter position accuracy. This is used as ground truth to evaluate orbit determination accuracy.',
                  },
                  {
                    tier: 'T2',
                    name: 'Downsampled',
                    desc: 'Real observations with reduced density. Tests algorithm robustness to sparse data.',
                    color: 'cosmic-blue',
                    detail: 'T2 data simulates scenarios where sensor access is limited. Observations are systematically removed while preserving track structure.',
                  },
                  {
                    tier: 'T3',
                    name: 'Simulated Obs',
                    desc: 'Synthetic observations generated from real orbits using physics-based propagation.',
                    color: 'nova-orange',
                    detail: 'T3 fills coverage gaps with simulated observations. Real orbits are propagated and simulated sensor measurements are generated with realistic noise models.',
                  },
                  {
                    tier: 'T4',
                    name: 'Fully Synthetic',
                    desc: 'Completely simulated objects and observations. Enables controlled experiment design.',
                    color: 'red-400',
                    detail: 'T4 data provides full control over the scenario. Both objects and observations are simulated, allowing precise control over difficulty parameters.',
                  },
                ].map((t) => (
                  <CollapsibleSection
                    key={t.tier}
                    title={`${t.tier} \u2014 ${t.name}`}
                    icon={Layers}
                    defaultOpen={t.tier === 'T2'}
                  >
                    <div className="space-y-2 pt-3">
                      <p className="text-sm text-muted-foreground leading-relaxed">{t.desc}</p>
                      <div className={cn('rounded-lg border p-3 text-xs text-muted-foreground', `border-${t.color}/20 bg-${t.color}/5`)}>
                        {t.detail}
                      </div>
                    </div>
                  </CollapsibleSection>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* UCTP Pipeline Concepts */}
          <Card className="border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GitBranch className="h-5 w-5 text-cosmic-cyan" />
                UCTP Processing Pipeline
              </CardTitle>
              <CardDescription>
                The standard pipeline stages for Uncorrelated Track processing
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  {
                    step: 'Ingest',
                    icon: Database,
                    desc: 'Load observation data (right ascension, declination, time, sensor ID) from the dataset JSON file.',
                    detail: 'The ingest stage parses the benchmark dataset and prepares observation data structures. Observations are angles-only measurements from ground-based optical/radar sensors.',
                    color: 'cyan',
                  },
                  {
                    step: 'Cluster',
                    icon: GitBranch,
                    desc: 'Group observations into tracks that likely belong to the same object using spatial/temporal clustering.',
                    detail: 'Clustering algorithms (e.g., DBSCAN, MHT, GNN) identify which observations belong together. This is the core association problem \u2014 the most challenging step in UCTP processing.',
                    color: 'purple',
                  },
                  {
                    step: 'IOD (Initial Orbit Determination)',
                    icon: Orbit,
                    desc: 'Compute a preliminary orbit from each cluster using methods like Gauss, Laplace, or Gooding.',
                    detail: 'IOD takes a minimum set of observations (typically 3) and computes an initial orbital state. Different methods (Gauss for angles-only, Gooding for range+angle) suit different scenarios.',
                    color: 'blue',
                  },
                  {
                    step: 'Refine',
                    icon: Target,
                    desc: 'Improve orbit accuracy using all available observations via batch least-squares or sequential filters.',
                    detail: 'Refinement uses all observations in a cluster to improve the orbit. Batch least-squares fits all data simultaneously, while EKF/UKF process observations sequentially for real-time capability.',
                    color: 'green',
                  },
                  {
                    step: 'Output',
                    icon: FileJson,
                    desc: 'Format results as the required JSON submission with track associations, states, and covariances.',
                    detail: 'The output stage packages your algorithm results into the benchmark submission format, including object IDs, associated track IDs, state vectors, covariance matrices, and confidence scores.',
                    color: 'orange',
                  },
                ].map((s, i) => (
                  <div key={s.step} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className={cn(
                        'w-10 h-10 rounded-xl border flex items-center justify-center',
                        `border-${s.color === 'cyan' ? 'cosmic-cyan' : s.color === 'purple' ? 'stellar-purple' : s.color === 'blue' ? 'cosmic-blue' : s.color === 'green' ? 'aurora-green' : 'nova-orange'}/30`,
                        `bg-${s.color === 'cyan' ? 'cosmic-cyan' : s.color === 'purple' ? 'stellar-purple' : s.color === 'blue' ? 'cosmic-blue' : s.color === 'green' ? 'aurora-green' : 'nova-orange'}/10`,
                      )}>
                        <s.icon className="h-4 w-4 text-muted-foreground" />
                      </div>
                      {i < 4 && <div className="w-px flex-1 bg-white/10 my-1" />}
                    </div>
                    <div className="flex-1 pb-4">
                      <h4 className="font-semibold text-sm">{s.step}</h4>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{s.desc}</p>
                      <div className="mt-2 rounded-lg bg-white/[0.03] border border-white/5 p-2.5">
                        <p className="text-xs text-muted-foreground leading-relaxed">{s.detail}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─── Data Formats ──────────────────────────────────────── */}
        <TabsContent value="dataset-format" className="space-y-6">
          {/* Observation Schema */}
          <Card className="border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileJson className="h-5 w-5 text-cosmic-blue" />
                Dataset Format
              </CardTitle>
              <CardDescription>
                Structure of the benchmark dataset JSON file
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <StepExplainer
                title="Dataset Structure Overview"
                description="Each benchmark dataset is a single JSON file containing three sections: observations (sensor measurements), truth catalog (known orbits), and associations (ground truth mapping)."
                tips={[
                  'Observations are angles-only: right ascension (RA) and declination (Dec)',
                  'Truth catalog provides the known orbital state for each object',
                  'Associations map track IDs to satellite IDs for scoring',
                ]}
                variant="info"
                collapsible={false}
              />

              <CollapsibleSection title="Observations Schema" icon={Database} defaultOpen>
                <div className="space-y-3 pt-3">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Each observation represents a single sensor measurement of a space object at a specific time.
                    The primary measurements are right ascension (RA) and declination (Dec) in the celestial coordinate system.
                  </p>
                  <CodeBlock code={`{
  "observations": [
    {
      "obsId": "obs_001",         // Unique observation identifier
      "time": "2024-01-15T...",   // Observation epoch (ISO 8601)
      "ra": 245.123,              // Right Ascension (degrees, 0-360)
      "dec": -12.456,             // Declination (degrees, -90 to +90)
      "raRate": 0.0012,           // RA angular rate (deg/sec) - optional
      "decRate": -0.0003,         // Dec angular rate (deg/sec) - optional
      "raSigma": 2.5,             // RA uncertainty (arcseconds)
      "decSigma": 2.5,            // Dec uncertainty (arcseconds)
      "sensorId": "GEODSS_1",    // Sensor that made the observation
      "trackId": "trk_001"       // Groups obs into sensor-level tracks
    }
  ]
}`} />
                  <div className="grid sm:grid-cols-2 gap-3 text-xs">
                    <div className="rounded-lg border border-cosmic-cyan/20 bg-cosmic-cyan/5 p-3">
                      <p className="font-semibold text-cosmic-cyan mb-1">RA / Dec (Celestial Coordinates)</p>
                      <p className="text-muted-foreground">Right Ascension and Declination are the astronomical equivalent of longitude and latitude on the sky. Sensors measure where an object appears against the background stars.</p>
                    </div>
                    <div className="rounded-lg border border-stellar-purple/20 bg-stellar-purple/5 p-3">
                      <p className="font-semibold text-stellar-purple mb-1">Track ID</p>
                      <p className="text-muted-foreground">A track is a group of observations from a single sensor pass. Your algorithm must associate tracks from different passes to the same object.</p>
                    </div>
                  </div>
                </div>
              </CollapsibleSection>

              <CollapsibleSection title="Truth Catalog Schema" icon={Shield}>
                <div className="space-y-3 pt-3">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    The truth catalog contains the known orbital state of each object at a reference epoch.
                    States are in the Earth-Centered Inertial (ECI) frame.
                  </p>
                  <CodeBlock code={`{
  "truthCatalog": [
    {
      "satId": "25544",                    // NORAD catalog ID
      "epoch": "2024-01-15T12:00:00Z",    // State epoch
      "state": [                           // ECI state vector
        6778.137, 0.0, 0.0,               // Position: x, y, z (km)
        0.0, 7.669, 0.0                    // Velocity: vx, vy, vz (km/s)
      ],
      "covariance": [...]                  // 6x6 covariance (optional)
    }
  ]
}`} />
                  <div className="rounded-lg border border-aurora-green/20 bg-aurora-green/5 p-3 text-xs">
                    <p className="font-semibold text-aurora-green mb-1">ECI Reference Frame</p>
                    <p className="text-muted-foreground">Earth-Centered Inertial (ECI) is a non-rotating reference frame with origin at Earth's center. The x-axis points to the vernal equinox, z-axis to the North Pole.</p>
                  </div>
                </div>
              </CollapsibleSection>

              <CollapsibleSection title="Associations (Ground Truth)" icon={GitBranch}>
                <div className="space-y-3 pt-3">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    The association ground truth maps each track to its true satellite. This is used to score your algorithm's track association accuracy.
                  </p>
                  <CodeBlock code={`{
  "associations": {
    "trk_001": "25544",    // Track trk_001 belongs to sat 25544 (ISS)
    "trk_002": "25544",    // Another pass of the same object
    "trk_003": "40697",    // Different object
    ...
  }
}`} />
                </div>
              </CollapsibleSection>
            </CardContent>
          </Card>

          {/* Submission Format */}
          <Card className="border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code className="h-5 w-5 text-aurora-green" />
                Submission Format
              </CardTitle>
              <CardDescription>
                How to format your algorithm's output for evaluation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <CodeBlock code={`{
  "metadata": {
    "algorithmName": "MyTracker-v2",
    "version": "2.1.0",
    "datasetId": "ds_leo_standard_001",
    "timestamp": "2024-01-16T14:30:00Z"
  },
  "results": [
    {
      "objectId": "obj_001",              // Your algorithm's object ID
      "trackIds": ["trk_001", "trk_002"], // Associated track IDs
      "state": {
        "epoch": "2024-01-15T12:00:00Z",
        "position": [6778.137, 0.0, 0.0],     // km in ECI
        "velocity": [0.0, 7.669, 0.0],         // km/s in ECI
        "covariance": [...]                     // 6x6 covariance matrix
      },
      "confidence": 0.95                  // Association confidence (0-1)
    }
  ]
}`} />

              <div className="space-y-3">
                <h4 className="font-semibold text-sm flex items-center gap-2">
                  <Shield className="h-4 w-4 text-nova-orange" />
                  Validation Rules
                </h4>
                <div className="grid sm:grid-cols-2 gap-3">
                  {[
                    { rule: 'Track IDs must exist in the dataset', icon: CheckCircle2, color: 'aurora-green' },
                    { rule: 'State vectors must be in ECI frame', icon: CheckCircle2, color: 'aurora-green' },
                    { rule: 'Covariance matrices must be positive semi-definite', icon: AlertTriangle, color: 'nova-orange' },
                    { rule: 'Position must be above Earth surface (>6371 km)', icon: AlertTriangle, color: 'nova-orange' },
                    { rule: 'Velocity must be physically reasonable (<12 km/s in LEO)', icon: AlertTriangle, color: 'nova-orange' },
                    { rule: 'Each track can only be assigned to one object', icon: XCircle, color: 'red-400' },
                  ].map((v, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                      <v.icon className={cn('h-3.5 w-3.5 mt-0.5 flex-shrink-0', `text-${v.color}`)} />
                      <span>{v.rule}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─── Evaluation Metrics ────────────────────────────────── */}
        <TabsContent value="metrics" className="space-y-6">
          <Card className="border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-aurora-green" />
                Evaluation Metrics
              </CardTitle>
              <CardDescription>
                How your algorithm's performance is measured and scored
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Binary Classification */}
              <div className="space-y-4">
                <h3 className="font-semibold flex items-center gap-2">
                  <Target className="h-4 w-4 text-cosmic-cyan" />
                  Track Association Metrics
                </h3>
                <StepExplainer
                  title="Understanding TP / FP / FN"
                  description="Track associations are evaluated as a classification problem. Each of your associations is compared against the ground truth to determine correctness."
                  tips={[
                    'True Positive (TP): You correctly linked a track to the right catalog object',
                    'False Positive (FP): You linked a track to the wrong object, or to a non-existent one',
                    'False Negative (FN): A catalog object exists but your algorithm did not find it',
                  ]}
                  variant="info"
                  collapsible={false}
                />

                <div className="grid sm:grid-cols-3 gap-4">
                  <MetricCard
                    name="Precision"
                    formula="TP / (TP + FP)"
                    description="Of all associations your algorithm made, how many are correct?"
                    interpretation="High precision means few false alarms. A precision of 0.95 means 95% of your reported objects are real."
                  />
                  <MetricCard
                    name="Recall"
                    formula="TP / (TP + FN)"
                    description="Of all real objects in the dataset, how many did your algorithm find?"
                    interpretation="High recall means few missed objects. A recall of 0.90 means you found 90% of all catalog objects."
                  />
                  <MetricCard
                    name="F1-Score"
                    formula="2 x P x R / (P + R)"
                    description="The harmonic mean of precision and recall. The primary ranking metric."
                    interpretation="F1 balances precision and recall. A score of 1.0 is perfect; 0.5 means the algorithm is struggling."
                  />
                </div>
              </div>

              <div className="border-t border-white/5 pt-6 space-y-4">
                <h3 className="font-semibold flex items-center gap-2">
                  <Orbit className="h-4 w-4 text-stellar-purple" />
                  Orbit Accuracy Metrics
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  For correctly associated objects (True Positives), the system evaluates how accurately
                  your algorithm determined the orbit. These metrics compare your estimated state against the truth catalog.
                </p>

                <div className="grid sm:grid-cols-2 gap-4">
                  <MetricCard
                    name="Position RMS"
                    formula="sqrt(mean(|r_err|^2))"
                    description="Root mean square error in the position vector, measured in kilometers."
                    interpretation="Lower is better. Sub-km accuracy is excellent for LEO; GEO tolerances are wider due to range."
                  />
                  <MetricCard
                    name="Velocity RMS"
                    formula="sqrt(mean(|v_err|^2))"
                    description="Root mean square error in the velocity vector, measured in km/s."
                    interpretation="Lower is better. Velocity accuracy reflects orbit determination quality and propagation fidelity."
                  />
                  <MetricCard
                    name="Mahalanobis Distance"
                    formula="sqrt(e^T P^-1 e)"
                    description="Normalized error using the covariance matrix. Tests whether your error bars are realistic."
                    interpretation="Values near 1.0 mean your covariance accurately reflects your true uncertainty. >> 1 means overconfident, << 1 means conservative."
                  />
                  <MetricCard
                    name="Residual RMS"
                    formula="sqrt(mean(res^2))"
                    description="RA and Dec observation residuals in arcseconds. Measures orbit-fit quality."
                    interpretation="Small residuals (few arcseconds) indicate a good orbit fit. Large residuals suggest the orbit doesn't match the observations well."
                  />
                </div>
              </div>

              <div className="border-t border-white/5 pt-6">
                <h3 className="font-semibold flex items-center gap-2 mb-3">
                  <BarChart3 className="h-4 w-4 text-aurora-green" />
                  Leaderboard Ranking
                </h3>
                <div className="rounded-xl border border-aurora-green/20 bg-aurora-green/5 p-4 text-sm text-muted-foreground leading-relaxed">
                  Algorithms are ranked primarily by <span className="font-semibold text-aurora-green">F1-Score</span>.
                  In case of ties, <span className="font-semibold text-foreground/80">Position RMS</span> (lower is better)
                  is used as the secondary criterion. This rewards algorithms that both correctly associate tracks
                  <em> and</em> accurately determine orbits.
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
