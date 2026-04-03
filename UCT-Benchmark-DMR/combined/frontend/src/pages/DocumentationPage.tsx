import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import {
  Code,
  FileJson,
  BarChart3,
  Rocket,
  Database,
  Upload,
  Eye,
  Trophy,
  Target,
  Crosshair,
  Gauge,
  ArrowRight,
  CheckCircle,
  AlertTriangle,
  Satellite,
  Globe,
} from 'lucide-react';

/* ─── Shared sub-components ─── */

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cosmic-cyan/10 border border-cosmic-cyan/20 text-cosmic-cyan text-xs font-mono tracking-wider uppercase mb-4">
      {children}
    </div>
  );
}

function StepCard({
  number,
  icon: Icon,
  title,
  description,
}: {
  number: number;
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="relative group">
      <div className="flex gap-4 p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-cosmic-cyan/20 transition-colors">
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-cosmic-cyan/20 to-cosmic-blue/20 border border-cosmic-cyan/20 flex items-center justify-center">
          <span className="text-sm font-bold text-cosmic-cyan font-mono">{number}</span>
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Icon className="h-4 w-4 text-cosmic-cyan/70" />
            <h4 className="font-semibold text-sm text-foreground">{title}</h4>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
        </div>
      </div>
    </div>
  );
}

function RegimeCard({
  badge,
  name,
  altitude,
  description,
}: {
  badge: 'leo' | 'meo' | 'geo' | 'heo';
  name: string;
  altitude: string;
  description: string;
}) {
  return (
    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-white/10 transition-colors">
      <div className="flex items-start gap-3">
        <Badge variant={badge} className="mt-0.5 text-xs font-bold">{badge.toUpperCase()}</Badge>
        <div>
          <p className="font-semibold text-sm">{name}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{altitude}</p>
          <p className="text-xs text-muted-foreground/70 mt-1">{description}</p>
        </div>
      </div>
    </div>
  );
}

function TierCard({
  badge,
  name,
  description,
}: {
  badge: 'tier1' | 'tier2' | 'tier3' | 'tier4';
  name: string;
  description: string;
}) {
  const label = badge.replace('tier', 'T');
  return (
    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-white/10 transition-colors">
      <div className="flex items-start gap-3">
        <Badge variant={badge} className="mt-0.5 text-xs font-bold">{label}</Badge>
        <div>
          <p className="font-semibold text-sm">{name}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
        </div>
      </div>
    </div>
  );
}

function CodeBlock({ children, title }: { children: string; title?: string }) {
  return (
    <div className="rounded-xl border border-white/[0.08] overflow-hidden">
      {title && (
        <div className="px-4 py-2 bg-white/[0.04] border-b border-white/[0.06] flex items-center gap-2">
          <FileJson className="h-3.5 w-3.5 text-cosmic-cyan/60" />
          <span className="text-xs font-mono text-muted-foreground">{title}</span>
        </div>
      )}
      <pre className="p-4 bg-white/[0.02] overflow-x-auto text-[13px] leading-relaxed">
        <code className="font-mono text-muted-foreground">
          {children}
        </code>
      </pre>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  name,
  formula,
  description,
  color = 'cyan',
}: {
  icon: React.ElementType;
  name: string;
  formula?: string;
  description: string;
  color?: 'cyan' | 'blue' | 'purple' | 'green' | 'orange';
}) {
  const colorMap = {
    cyan: 'from-cosmic-cyan/15 to-cosmic-cyan/5 border-cosmic-cyan/20 text-cosmic-cyan',
    blue: 'from-cosmic-blue/15 to-cosmic-blue/5 border-cosmic-blue/20 text-cosmic-blue',
    purple: 'from-stellar-purple/15 to-stellar-purple/5 border-stellar-purple/20 text-stellar-purple',
    green: 'from-aurora-green/15 to-aurora-green/5 border-aurora-green/20 text-aurora-green',
    orange: 'from-nova-orange/15 to-nova-orange/5 border-nova-orange/20 text-nova-orange',
  };
  const c = colorMap[color];
  return (
    <div className={`p-4 rounded-xl bg-gradient-to-br ${c.split(' ').slice(0, 2).join(' ')} border ${c.split(' ')[2]}`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`h-4 w-4 ${c.split(' ').slice(-1)[0]}`} />
        <h4 className="font-semibold text-sm">{name}</h4>
      </div>
      {formula && (
        <p className="text-xs font-mono text-muted-foreground mb-2 bg-black/20 rounded px-2 py-1 inline-block">
          {formula}
        </p>
      )}
      <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
    </div>
  );
}

function ValidationRule({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2.5 py-2">
      <CheckCircle className="h-4 w-4 text-aurora-green/70 mt-0.5 flex-shrink-0" />
      <span className="text-sm text-muted-foreground">{children}</span>
    </div>
  );
}

/* ─── Main page ─── */

export function DocumentationPage() {
  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight font-display">Documentation</h1>
        <p className="text-muted-foreground mt-1">
          Technical reference for the SpOC UCTP Benchmark Platform
        </p>
      </div>

      <Tabs defaultValue="getting-started" className="space-y-6">
        <TabsList className="flex-wrap h-auto gap-2 bg-white/[0.03] border border-white/[0.06] p-1.5 rounded-xl">
          <TabsTrigger value="getting-started" className="gap-2 rounded-lg data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan data-[state=active]:border-cosmic-cyan/20">
            <Rocket className="h-4 w-4" />
            Getting Started
          </TabsTrigger>
          <TabsTrigger value="dataset-format" className="gap-2 rounded-lg data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan data-[state=active]:border-cosmic-cyan/20">
            <FileJson className="h-4 w-4" />
            Dataset Format
          </TabsTrigger>
          <TabsTrigger value="submission-format" className="gap-2 rounded-lg data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan data-[state=active]:border-cosmic-cyan/20">
            <Code className="h-4 w-4" />
            Submission Format
          </TabsTrigger>
          <TabsTrigger value="metrics" className="gap-2 rounded-lg data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan data-[state=active]:border-cosmic-cyan/20">
            <BarChart3 className="h-4 w-4" />
            Evaluation Metrics
          </TabsTrigger>
        </TabsList>

        {/* ═══ GETTING STARTED ═══ */}
        <TabsContent value="getting-started" className="space-y-8">
          {/* Welcome */}
          <Card className="bg-white/[0.02] border-white/[0.06]">
            <CardContent className="pt-6">
              <SectionLabel>Overview</SectionLabel>
              <h2 className="text-xl font-bold font-display mb-3">Welcome to SpOC</h2>
              <p className="text-muted-foreground leading-relaxed max-w-3xl">
                The SpOC (Space Operations Center) UCTP Benchmark Platform is a standardized framework
                for evaluating Uncorrelated Track Processing algorithms. Generate benchmark datasets,
                submit your algorithm results, and measure performance against standardized metrics.
              </p>
            </CardContent>
          </Card>

          {/* Quick Start Steps */}
          <div>
            <SectionLabel>Quick Start</SectionLabel>
            <h2 className="text-xl font-bold font-display mb-4">5-Step Workflow</h2>
            <div className="grid gap-3">
              <StepCard
                number={1}
                icon={Database}
                title="Generate a Dataset"
                description="Navigate to Datasets > Generate and configure your benchmark parameters. Select orbital regime, tier, and sensor type."
              />
              <StepCard
                number={2}
                icon={ArrowRight}
                title="Download the Dataset"
                description="Download the JSON file containing observations and the truth catalog for your selected configuration."
              />
              <StepCard
                number={3}
                icon={Satellite}
                title="Run Your Algorithm"
                description="Process the observations with your UCTP algorithm to produce track associations and state estimates."
              />
              <StepCard
                number={4}
                icon={Upload}
                title="Submit Results"
                description="Upload your algorithm output through the Submit page. The system validates your submission and runs the evaluation pipeline."
              />
              <StepCard
                number={5}
                icon={Eye}
                title="View Results"
                description="Review detailed metrics including F1-Score, position RMS, and per-satellite breakdown. Compare against the leaderboard."
              />
            </div>
          </div>

          {/* Key Concepts */}
          <div>
            <SectionLabel>Reference</SectionLabel>
            <h2 className="text-xl font-bold font-display mb-4">Key Concepts</h2>

            <div className="space-y-6">
              {/* Orbital Regimes */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Globe className="h-4 w-4 text-cosmic-cyan/70" />
                  <h3 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground">Orbital Regimes</h3>
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  <RegimeCard badge="leo" name="Low Earth Orbit" altitude="200 – 2,000 km" description="Dense observation environment. ISS, Starlink, debris." />
                  <RegimeCard badge="meo" name="Medium Earth Orbit" altitude="2,000 – 35,786 km" description="Navigation constellations. GPS, Galileo." />
                  <RegimeCard badge="geo" name="Geostationary Orbit" altitude="~35,786 km" description="Communications, weather, surveillance." />
                  <RegimeCard badge="heo" name="Highly Elliptical Orbit" altitude="Variable" description="Molniya, Tundra orbits. Complex tracking." />
                </div>
              </div>

              {/* Data Tiers */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Gauge className="h-4 w-4 text-cosmic-cyan/70" />
                  <h3 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground">Data Tiers</h3>
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  <TierCard badge="tier1" name="Pristine" description="High-quality, complete observations with full orbital coverage." />
                  <TierCard badge="tier2" name="Downsampled" description="Realistic sparse coverage with temporal gaps between passes." />
                  <TierCard badge="tier3" name="Simulated Observations" description="Synthetic observations generated from real orbital parameters." />
                  <TierCard badge="tier4" name="Fully Synthetic" description="Simulated objects and observations for extreme test scenarios." />
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* ═══ DATASET FORMAT ═══ */}
        <TabsContent value="dataset-format" className="space-y-6">
          <Card className="bg-white/[0.02] border-white/[0.06]">
            <CardContent className="pt-6">
              <SectionLabel>Schema</SectionLabel>
              <h2 className="text-xl font-bold font-display mb-3">Dataset Structure</h2>
              <p className="text-muted-foreground leading-relaxed max-w-3xl mb-6">
                Each benchmark dataset is provided as a JSON file containing two main sections:
                observations and the truth catalog. Association ground truth maps observation tracks
                to catalog objects.
              </p>
            </CardContent>
          </Card>

          <div className="space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Crosshair className="h-4 w-4 text-cosmic-cyan/70" />
                <h3 className="font-semibold">Observations Schema</h3>
              </div>
              <CodeBlock title="observations.json">{`{
  "observations": [
    {
      "obsId": "string",           // Unique observation identifier
      "time": "ISO8601 datetime",  // Observation epoch
      "ra": number,                // Right Ascension (degrees)
      "dec": number,               // Declination (degrees)
      "raRate": number,            // RA rate (deg/sec) — optional
      "decRate": number,           // Dec rate (deg/sec) — optional
      "raSigma": number,           // RA uncertainty (arcsec)
      "decSigma": number,          // Dec uncertainty (arcsec)
      "sensorId": "string",        // Sensor identifier
      "trackId": "string"          // Track grouping identifier
    }
  ]
}`}</CodeBlock>
            </div>

            <div>
              <div className="flex items-center gap-2 mb-3">
                <Satellite className="h-4 w-4 text-stellar-purple/70" />
                <h3 className="font-semibold">Truth Catalog Schema</h3>
              </div>
              <CodeBlock title="truth_catalog.json">{`{
  "truthCatalog": [
    {
      "satId": "string",           // NORAD catalog ID or synthetic ID
      "epoch": "ISO8601 datetime", // State epoch
      "state": [x, y, z, vx, vy, vz],  // ECI state vector (km, km/s)
      "covariance": [...]          // 6x6 covariance matrix (optional)
    }
  ]
}`}</CodeBlock>
            </div>

            <div>
              <div className="flex items-center gap-2 mb-3">
                <ArrowRight className="h-4 w-4 text-aurora-green/70" />
                <h3 className="font-semibold">Association Ground Truth</h3>
              </div>
              <CodeBlock title="associations.json">{`{
  "associations": {
    "trackId_001": "satId_25544",   // ISS
    "trackId_002": "satId_25545",   // Object 2
    "trackId_003": "satId_28654"    // NOAA 18
  }
}`}</CodeBlock>
            </div>
          </div>
        </TabsContent>

        {/* ═══ SUBMISSION FORMAT ═══ */}
        <TabsContent value="submission-format" className="space-y-6">
          <Card className="bg-white/[0.02] border-white/[0.06]">
            <CardContent className="pt-6">
              <SectionLabel>Specification</SectionLabel>
              <h2 className="text-xl font-bold font-display mb-3">Submission Structure</h2>
              <p className="text-muted-foreground leading-relaxed max-w-3xl mb-6">
                Your submission should be a JSON file containing your algorithm's track associations
                and state estimates for each identified object. All state vectors must be in the
                Earth-Centered Inertial (ECI) reference frame.
              </p>
            </CardContent>
          </Card>

          <div>
            <div className="flex items-center gap-2 mb-3">
              <Code className="h-4 w-4 text-cosmic-cyan/70" />
              <h3 className="font-semibold">Required Schema</h3>
            </div>
            <CodeBlock title="submission.json">{`{
  "metadata": {
    "algorithmName": "string",
    "version": "string",
    "datasetId": "string",
    "timestamp": "ISO8601 datetime"
  },
  "results": [
    {
      "objectId": "string",        // Your algorithm's object ID
      "trackIds": ["string"],      // Associated track IDs
      "state": {
        "epoch": "ISO8601 datetime",
        "position": [x, y, z],     // km in ECI
        "velocity": [vx, vy, vz],  // km/s in ECI
        "covariance": [...]        // 6x6 covariance matrix
      },
      "confidence": number         // 0.0 to 1.0
    }
  ]
}`}</CodeBlock>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="h-4 w-4 text-nova-orange/70" />
              <h3 className="font-semibold">Validation Rules</h3>
            </div>
            <Card className="bg-white/[0.02] border-white/[0.06]">
              <CardContent className="pt-5 pb-3 divide-y divide-white/[0.04]">
                <ValidationRule>All referenced track IDs must exist in the source dataset</ValidationRule>
                <ValidationRule>State vectors must be in Earth-Centered Inertial (ECI) frame</ValidationRule>
                <ValidationRule>Covariance matrices must be positive semi-definite</ValidationRule>
                <ValidationRule>Position magnitudes must be physically reasonable (above Earth surface, below GEO+)</ValidationRule>
                <ValidationRule>Velocity magnitudes must be consistent with orbital mechanics</ValidationRule>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ═══ EVALUATION METRICS ═══ */}
        <TabsContent value="metrics" className="space-y-8">
          {/* Binary Classification */}
          <div>
            <SectionLabel>Classification</SectionLabel>
            <h2 className="text-xl font-bold font-display mb-2">Binary Classification Metrics</h2>
            <p className="text-muted-foreground text-sm mb-4 max-w-3xl">
              Track associations are evaluated as a binary classification problem. Each catalog object
              is either correctly tracked (TP), incorrectly tracked (FP), or missed entirely (FN).
            </p>

            <div className="grid sm:grid-cols-3 gap-3 mb-6">
              <MetricCard
                icon={Target}
                name="Precision"
                formula="TP / (TP + FP)"
                description="Of your associations, how many are correct? High precision means few false alarms."
                color="cyan"
              />
              <MetricCard
                icon={Crosshair}
                name="Recall"
                formula="TP / (TP + FN)"
                description="Of all catalog objects, how many did you find? High recall means few missed objects."
                color="blue"
              />
              <MetricCard
                icon={Trophy}
                name="F1-Score"
                formula="2 × P × R / (P + R)"
                description="Harmonic mean of precision and recall. Primary ranking metric on the leaderboard."
                color="green"
              />
            </div>

            <Card className="bg-white/[0.02] border-white/[0.06]">
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center gap-2 mb-3">
                  <BarChart3 className="h-4 w-4 text-muted-foreground" />
                  <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Confusion Matrix</h4>
                </div>
                <div className="grid grid-cols-3 gap-2 max-w-md text-center text-xs">
                  <div />
                  <div className="font-mono text-muted-foreground py-1.5">Predicted +</div>
                  <div className="font-mono text-muted-foreground py-1.5">Predicted −</div>
                  <div className="font-mono text-muted-foreground py-1.5 text-right pr-2">Actual +</div>
                  <div className="rounded-lg bg-aurora-green/10 border border-aurora-green/20 text-aurora-green py-2 font-semibold">TP</div>
                  <div className="rounded-lg bg-destructive/10 border border-destructive/20 text-destructive py-2 font-semibold">FN</div>
                  <div className="font-mono text-muted-foreground py-1.5 text-right pr-2">Actual −</div>
                  <div className="rounded-lg bg-nova-orange/10 border border-nova-orange/20 text-nova-orange py-2 font-semibold">FP</div>
                  <div className="rounded-lg bg-white/[0.04] border border-white/[0.08] text-muted-foreground py-2 font-semibold">TN</div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* State Estimation */}
          <div>
            <SectionLabel>State Accuracy</SectionLabel>
            <h2 className="text-xl font-bold font-display mb-2">State Estimation Metrics</h2>
            <p className="text-muted-foreground text-sm mb-4 max-w-3xl">
              For correctly associated objects, orbit determination accuracy is evaluated against
              the truth catalog reference states.
            </p>

            <div className="grid sm:grid-cols-3 gap-3">
              <MetricCard
                icon={Target}
                name="Position RMS"
                description="Root mean square error in position estimate. Measured in kilometers. Lower is better."
                color="purple"
              />
              <MetricCard
                icon={Gauge}
                name="Velocity RMS"
                description="Root mean square error in velocity estimate. Measured in km/s. Lower is better."
                color="orange"
              />
              <MetricCard
                icon={Crosshair}
                name="Mahalanobis Distance"
                description="Normalized error accounting for covariance. Values near 1.0 indicate realistic uncertainty estimates."
                color="cyan"
              />
            </div>
          </div>

          {/* Residual Analysis */}
          <div>
            <SectionLabel>Residuals</SectionLabel>
            <h2 className="text-xl font-bold font-display mb-2">Residual Analysis</h2>
            <p className="text-muted-foreground text-sm mb-4 max-w-3xl">
              Observation residuals measure how well the estimated orbit fits the raw sensor data.
            </p>

            <div className="grid sm:grid-cols-2 gap-3">
              <MetricCard
                icon={Target}
                name="RA Residual RMS"
                description="Right ascension fit quality measured in arcseconds. Indicates how well the orbit matches observed angular positions."
                color="blue"
              />
              <MetricCard
                icon={Crosshair}
                name="Dec Residual RMS"
                description="Declination fit quality measured in arcseconds. Together with RA residuals, characterizes overall orbit fit."
                color="purple"
              />
            </div>
          </div>

          {/* Ranking */}
          <Card className="bg-white/[0.02] border-white/[0.06]">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2">
                <Trophy className="h-5 w-5 text-cosmic-cyan" />
                <h3 className="font-bold font-display">Leaderboard Ranking</h3>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed max-w-3xl">
                Algorithms are ranked primarily by <span className="text-cosmic-cyan font-semibold">F1-Score</span>.
                In case of ties, <span className="text-stellar-purple font-semibold">Position RMS</span> is
                used as a secondary criterion (lower is better). Rankings update in real-time as new
                submissions are evaluated.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
