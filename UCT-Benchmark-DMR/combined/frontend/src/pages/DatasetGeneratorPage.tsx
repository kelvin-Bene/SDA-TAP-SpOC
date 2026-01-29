import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGenerateDataset, useJobStatus, MAX_TIMEFRAME_DAYS } from '@/hooks/useDatasets';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { InfoPopover, ConceptBadge, StepExplainer } from '@/components/ui/info-popover';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Clock,
  Satellite,
  Zap,
  Settings2,
  FileCheck,
  Loader2,
  AlertCircle,
  Database,
  Layers,
  Shield,
  Sparkles,
  Orbit,
  Radio,
  Target,
  FlaskConical,
  Waves,
  Eye,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { OrbitalRegime, DataTier, DatasetGenerationConfig, DownsamplingOptions, SimulationOptions, SearchStrategy, OpenSourceOptions, DatasetPreset } from '@/types';

/* ------------------------------------------------------------------ */
/*  Step definitions                                                    */
/* ------------------------------------------------------------------ */

const steps = [
  { id: 1, name: 'Preset', icon: Sparkles, description: 'Choose data sources' },
  { id: 2, name: 'Regime', icon: Orbit, description: 'Orbital environment' },
  { id: 3, name: 'Quality', icon: Target, description: 'Coverage & density' },
  { id: 4, name: 'Objects', icon: Satellite, description: 'Count & time range' },
  { id: 5, name: 'Advanced', icon: Settings2, description: 'Fine-tuning' },
  { id: 6, name: 'Review', icon: FileCheck, description: 'Confirm & generate' },
];

/* ------------------------------------------------------------------ */
/*  Preset definitions                                                  */
/* ------------------------------------------------------------------ */

const datasetPresets: DatasetPreset[] = [
  {
    id: 'quick-test',
    name: 'Quick Test',
    description: 'Fast dataset with UDL data only. No enrichment for quick testing.',
    icon: 'zap',
    dataSources: ['UDL', 'ESA'],
    config: {
      tier: 'T2',
      objectCount: 10,
      openSource: {
        enableEnrichment: false,
        sensorMode: 'EO',
        includeIlrsValidation: false,
      },
    },
  },
  {
    id: 'standard',
    name: 'Standard Dataset',
    description: 'UDL observations enriched with UCS/GCAT satellite metadata for accurate HAMR detection.',
    icon: 'database',
    dataSources: ['UDL', 'ESA', 'UCS', 'GCAT'],
    config: {
      tier: 'T2',
      objectCount: 40,
      openSource: {
        enableEnrichment: true,
        sensorMode: 'EO',
        includeIlrsValidation: false,
      },
    },
  },
  {
    id: 'multi-phenom',
    name: 'Multi-Phenomenology',
    description: 'Combines optical (UDL) and RF (SatNOGS) observations for sensor fusion testing.',
    icon: 'layers',
    dataSources: ['UDL', 'ESA', 'UCS', 'GCAT', 'SatNOGS'],
    config: {
      tier: 'T2',
      objectCount: 30,
      openSource: {
        enableEnrichment: true,
        sensorMode: 'MX',
        includeIlrsValidation: false,
      },
    },
  },
  {
    id: 'validation',
    name: 'Validation Dataset (T1H)',
    description: 'Highest quality tier with ILRS laser-ranging ground truth for algorithm validation.',
    icon: 'shield',
    dataSources: ['UDL', 'ESA', 'UCS', 'GCAT', 'ILRS'],
    config: {
      tier: 'T1H' as DataTier,
      objectCount: 20,
      coverage: 'high',
      openSource: {
        enableEnrichment: true,
        sensorMode: 'EO',
        includeIlrsValidation: true,
      },
    },
  },
  {
    id: 'full-integration',
    name: 'Full Integration',
    description: 'All data sources enabled: UDL + ESA + UCS + GCAT + SatNOGS + ILRS validation.',
    icon: 'sparkles',
    dataSources: ['UDL', 'ESA', 'UCS', 'GCAT', 'SatNOGS', 'ILRS'],
    config: {
      tier: 'T1H' as DataTier,
      objectCount: 25,
      coverage: 'high',
      openSource: {
        enableEnrichment: true,
        sensorMode: 'MX',
        includeIlrsValidation: true,
      },
    },
  },
  {
    id: 'custom',
    name: 'Custom Configuration',
    description: 'Start from scratch and configure all data sources manually.',
    icon: 'settings',
    dataSources: [],
    config: {},
  },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                             */
/* ------------------------------------------------------------------ */

function calculateTimeframeDays(startDate: string, endDate: string): number {
  const start = new Date(startDate);
  const end = new Date(endDate);
  if (isNaN(start.getTime()) || isNaN(end.getTime())) return 0;
  return Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
}

const defaultDownsampling: DownsamplingOptions = {
  enabled: false,
  targetCoverage: 0.05,
  targetGap: 2.0,
  maxObsPerSat: 50,
  preserveTracks: true,
};

const defaultSimulation: SimulationOptions = {
  enabled: false,
  fillGaps: true,
  sensorModel: 'GEODSS',
  applyNoise: true,
  maxSyntheticRatio: 0.5,
};

const defaultOpenSource: OpenSourceOptions = {
  enableEnrichment: true,
  sensorMode: 'EO',
  includeIlrsValidation: false,
};

const defaultConfig: DatasetGenerationConfig = {
  regime: 'LEO',
  tier: 'T2',
  coverage: 'standard',
  observationDensity: 50,
  trackGapTarget: 2,
  objectCount: 40,
  includeHamr: false,
  startDate: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  endDate: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  sensors: ['optical'],
  downsampling: defaultDownsampling,
  simulation: defaultSimulation,
  searchStrategy: 'hybrid',
  windowSizeMinutes: 10,
  openSource: defaultOpenSource,
};

/* ------------------------------------------------------------------ */
/*  Preset icon mapping                                                 */
/* ------------------------------------------------------------------ */

function getPresetIcon(iconName: string) {
  switch (iconName) {
    case 'zap': return <Zap className="h-5 w-5" />;
    case 'database': return <Database className="h-5 w-5" />;
    case 'layers': return <Layers className="h-5 w-5" />;
    case 'shield': return <Shield className="h-5 w-5" />;
    case 'sparkles': return <Sparkles className="h-5 w-5" />;
    default: return <Settings2 className="h-5 w-5" />;
  }
}

/* ------------------------------------------------------------------ */
/*  Data source educational content                                     */
/* ------------------------------------------------------------------ */

const dataSourceInfo: Record<string, { label: string; full: string; description: string; detail: string }> = {
  UDL: {
    label: 'UDL',
    full: 'Unified Data Library',
    description: 'Primary satellite observation data from the U.S. Space Command sensor network.',
    detail: 'UDL aggregates optical and radar observations from military and civilian sensors worldwide. It provides the core angles-only measurements (right ascension & declination) used for orbit determination.',
  },
  ESA: {
    label: 'ESA',
    full: 'ESA Discosweb',
    description: 'European Space Agency\'s database of orbital elements and Two-Line Elements (TLEs).',
    detail: 'Discosweb provides cataloged orbital parameters that serve as reference ephemerides. TLEs encode mean orbital elements in the SGP4 propagation framework used by the space surveillance community.',
  },
  UCS: {
    label: 'UCS',
    full: 'Union of Concerned Scientists',
    description: 'Satellite metadata including purpose, operator, mass, and launch details.',
    detail: 'The UCS Satellite Database is the go-to public resource for satellite characteristics. Mass data from UCS is critical for HAMR (High Area-to-Mass Ratio) detection \u2014 identifying tumbling debris vs. active satellites.',
  },
  GCAT: {
    label: 'GCAT',
    full: 'General Catalog of Artificial Space Objects',
    description: 'Comprehensive catalog with mass data for HAMR classification.',
    detail: 'Jonathan McDowell\'s GCAT provides detailed physical properties of space objects. Combined with UCS, it enables the benchmark to flag objects whose area-to-mass ratio indicates non-standard dynamics.',
  },
  SatNOGS: {
    label: 'SatNOGS',
    full: 'Satellite Networked Open Ground Station',
    description: 'Open-source RF observations from a global network of ground stations.',
    detail: 'SatNOGS provides radio-frequency observation data (signal strength, Doppler) from volunteer-run ground stations. Including RF data enables multi-phenomenology testing \u2014 combining optical and radio measurements for richer datasets.',
  },
  ILRS: {
    label: 'ILRS',
    full: 'International Laser Ranging Service',
    description: 'Sub-centimeter precision laser ranging used as ground truth for validation.',
    detail: 'ILRS stations bounce laser pulses off retroreflectors on satellites, achieving ~1 cm range accuracy. This is orders of magnitude better than radar or optical tracking, making ILRS the gold standard for validating orbit determination algorithms.',
  },
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                      */
/* ------------------------------------------------------------------ */

export function DatasetGeneratorPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [config, setConfig] = useState<DatasetGenerationConfig>(defaultConfig);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);

  const generateDatasetMutation = useGenerateDataset();
  const { data: jobStatus } = useJobStatus(jobId);

  const calculatedTimeframe = calculateTimeframeDays(config.startDate, config.endDate);
  const today = new Date().toISOString().split('T')[0];
  const isEndDateFuture = config.endDate > today;
  const isTimeframeValid = calculatedTimeframe >= 1 && calculatedTimeframe <= MAX_TIMEFRAME_DAYS && !isEndDateFuture;
  const timeframeError = isEndDateFuture
    ? 'End date cannot be in the future (no observation data available)'
    : calculatedTimeframe > MAX_TIMEFRAME_DAYS
    ? `Date range exceeds maximum of ${MAX_TIMEFRAME_DAYS} days (currently ${calculatedTimeframe} days)`
    : calculatedTimeframe < 1
    ? 'End date must be after start date'
    : null;

  useEffect(() => {
    if (jobStatus) {
      setGenerationProgress(jobStatus.progress);
      if (jobStatus.status === 'completed') {
        setIsGenerating(false);
        navigate('/datasets/my-datasets');
      } else if (jobStatus.status === 'failed') {
        setIsGenerating(false);
        setJobId(null);
      }
    }
  }, [jobStatus, navigate]);

  const updateConfig = <K extends keyof DatasetGenerationConfig>(
    key: K,
    value: DatasetGenerationConfig[K]
  ) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const nextStep = () => setCurrentStep((prev) => Math.min(prev + 1, 6));
  const prevStep = () => setCurrentStep((prev) => Math.max(prev - 1, 1));

  const applyPreset = (preset: DatasetPreset) => {
    setSelectedPreset(preset.id);
    if (preset.id !== 'custom') {
      setConfig((prev) => ({
        ...prev,
        ...preset.config,
        openSource: preset.config.openSource ?? defaultOpenSource,
      }));
    }
  };

  const updateDownsampling = <K extends keyof DownsamplingOptions>(
    key: K,
    value: DownsamplingOptions[K]
  ) => {
    setConfig((prev) => ({
      ...prev,
      downsampling: { ...prev.downsampling!, [key]: value },
    }));
  };

  const updateSimulation = <K extends keyof SimulationOptions>(
    key: K,
    value: SimulationOptions[K]
  ) => {
    setConfig((prev) => ({
      ...prev,
      simulation: { ...prev.simulation!, [key]: value },
    }));
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerationProgress(0);
    try {
      const result = await generateDatasetMutation.mutateAsync(config);
      if (result?.job_id) {
        setJobId(result.job_id);
      } else {
        setTimeout(() => {
          setIsGenerating(false);
          navigate('/datasets/my-datasets');
        }, 1000);
      }
    } catch (error: any) {
      let errorMessage = 'Unknown error';
      const detail = error?.response?.data?.detail;
      if (Array.isArray(detail)) {
        errorMessage = detail.map((e: any) =>
          `${e.loc?.join(' -> ')}: ${e.msg}`
        ).join('\n');
      } else if (typeof detail === 'string') {
        errorMessage = detail;
      } else if (error?.message) {
        errorMessage = error.message;
      }
      alert(`Failed to generate dataset:\n${errorMessage}`);
      setIsGenerating(false);
    }
  };

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* ── Page Header ─────────────────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-cosmic-cyan/5 via-transparent to-stellar-purple/5 p-6 sm:p-8">
        <div className="absolute top-0 right-0 w-72 h-72 bg-cosmic-cyan/8 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-stellar-purple/8 rounded-full blur-3xl translate-y-1/3 -translate-x-1/4" />
        <div className="relative z-10">
          <div className="flex items-center gap-2 text-cosmic-cyan text-sm font-medium mb-2">
            <FlaskConical className="h-4 w-4" />
            Dataset Generation
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-bold tracking-tight">
            Build Your <span className="text-gradient-cosmic">Benchmark Dataset</span>
          </h1>
          <p className="text-muted-foreground mt-2 max-w-2xl">
            Configure observation sources, orbital parameters, and quality settings to generate
            a custom UCT benchmark dataset for algorithm evaluation.
          </p>
        </div>
      </div>

      {/* ── Step Progress ────────────────────────────────────────── */}
      <div className="relative">
        {/* Progress line behind steps */}
        <div className="absolute top-6 left-0 right-0 h-0.5 bg-white/5 hidden sm:block" />
        <div
          className="absolute top-6 left-0 h-0.5 bg-gradient-to-r from-cosmic-cyan to-stellar-purple transition-all duration-500 ease-out hidden sm:block"
          style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
        />

        <div className="relative flex items-start justify-between gap-1">
          {steps.map((step) => {
            const isActive = currentStep === step.id;
            const isCompleted = currentStep > step.id;
            return (
              <button
                key={step.id}
                type="button"
                onClick={() => {
                  if (isCompleted) setCurrentStep(step.id);
                }}
                className={cn(
                  'flex flex-col items-center gap-1.5 group transition-all duration-300',
                  isCompleted ? 'cursor-pointer' : 'cursor-default',
                )}
              >
                <div
                  className={cn(
                    'relative flex items-center justify-center w-12 h-12 rounded-xl border-2 transition-all duration-300',
                    isActive
                      ? 'border-cosmic-cyan bg-cosmic-cyan/10 shadow-[0_0_20px_-4px_hsl(192_91%_52%/0.4)] scale-110'
                      : isCompleted
                      ? 'border-aurora-green/60 bg-aurora-green/10'
                      : 'border-white/10 bg-white/5',
                  )}
                >
                  {isCompleted ? (
                    <Check className="h-5 w-5 text-aurora-green" />
                  ) : (
                    <step.icon className={cn(
                      'h-5 w-5 transition-colors',
                      isActive ? 'text-cosmic-cyan' : 'text-muted-foreground',
                    )} />
                  )}
                  {isActive && (
                    <span className="absolute -inset-1 rounded-xl border border-cosmic-cyan/20 animate-pulse" />
                  )}
                </div>
                <span className={cn(
                  'text-xs font-medium transition-colors hidden sm:block',
                  isActive ? 'text-cosmic-cyan' : isCompleted ? 'text-aurora-green' : 'text-muted-foreground',
                )}>
                  {step.name}
                </span>
                <span className="text-[10px] text-muted-foreground hidden lg:block">
                  {step.description}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Step Content ─────────────────────────────────────────── */}
      <Card className="border-white/10 overflow-hidden">
        {/* ─── Step 1: Preset Selection ──────────────────────────── */}
        {currentStep === 1 && (
          <>
            <CardHeader>
              <div className="flex items-center gap-3">
                <CardTitle className="flex-1">Choose Data Source Configuration</CardTitle>
                <InfoPopover
                  title="What are Presets?"
                  description="Presets pre-configure which external data sources are included in your benchmark dataset. Each source adds different observation types and metadata."
                  details={[
                    'Quick Test uses minimal sources for rapid iteration',
                    'Standard includes enrichment for realistic benchmarking',
                    'Multi-Phenomenology combines optical + RF sensors',
                    'Validation (T1H) uses ILRS laser ranging as ground truth',
                  ]}
                  learnMore="The benchmark platform pulls from real-world space surveillance data sources. Different combinations test different capabilities of your UCT algorithm. For example, multi-phenomenology datasets test whether your algorithm can fuse different sensor types, while validation datasets let you measure absolute accuracy against laser-ranging truth."
                  variant="concept"
                  size="md"
                />
              </div>
              <CardDescription>
                Select a preset to configure which data sources to pull from, or choose custom for full control
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Preset cards */}
              <div className="grid gap-3">
                {datasetPresets.map((preset) => {
                  const isSelected = selectedPreset === preset.id;
                  return (
                    <div
                      key={preset.id}
                      onClick={() => applyPreset(preset)}
                      className={cn(
                        'relative flex items-start gap-4 rounded-xl border p-4 cursor-pointer transition-all duration-200',
                        'hover:bg-white/[0.02]',
                        isSelected
                          ? 'border-cosmic-cyan/40 bg-cosmic-cyan/5 ring-1 ring-cosmic-cyan/20 shadow-[0_0_24px_-8px_hsl(192_91%_52%/0.15)]'
                          : 'border-white/10 hover:border-white/20',
                      )}
                    >
                      {/* Icon */}
                      <div className={cn(
                        'p-2.5 rounded-xl transition-colors',
                        isSelected ? 'bg-cosmic-cyan/15 text-cosmic-cyan' : 'bg-white/5 text-muted-foreground',
                      )}>
                        {getPresetIcon(preset.icon)}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0 space-y-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold">{preset.name}</span>
                          {preset.id === 'standard' && (
                            <Badge className="bg-cosmic-cyan/15 text-cosmic-cyan border-cosmic-cyan/30 text-[10px]">
                              Recommended
                            </Badge>
                          )}
                          {preset.id === 'full-integration' && (
                            <Badge variant="secondary" className="text-[10px]">All Sources</Badge>
                          )}
                          {preset.id === 'validation' && (
                            <Badge className="bg-aurora-green/15 text-aurora-green border-aurora-green/30 text-[10px]">
                              Ground Truth
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground leading-relaxed">{preset.description}</p>
                        {preset.dataSources.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-1">
                            {preset.dataSources.map((source) => (
                              <ConceptBadge
                                key={source}
                                label={source}
                                explanation={dataSourceInfo[source]?.description || ''}
                                variant="info"
                              />
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Check indicator */}
                      {isSelected && (
                        <div className="flex-shrink-0 p-1.5 rounded-full bg-cosmic-cyan/15">
                          <Check className="h-4 w-4 text-cosmic-cyan" />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Data Sources Educational Panel */}
              <StepExplainer
                title="Understanding Data Sources"
                description="Each data source provides a different type of space surveillance information. The combination determines how realistic and challenging your benchmark dataset will be."
                tips={[
                  'UDL provides the raw angle measurements your algorithm processes',
                  'UCS/GCAT metadata enables detection of HAMR (High Area-to-Mass Ratio) objects like tumbling debris',
                  'SatNOGS adds RF observations for multi-sensor fusion testing',
                  'ILRS laser ranging provides sub-centimeter truth for validating orbit accuracy',
                ]}
                variant="concept"
                defaultOpen={false}
              />
            </CardContent>
          </>
        )}

        {/* ─── Step 2: Regime Selection ──────────────────────────── */}
        {currentStep === 2 && (
          <>
            <CardHeader>
              <div className="flex items-center gap-3">
                <CardTitle className="flex-1">Select Orbital Regime</CardTitle>
                <InfoPopover
                  title="What is an Orbital Regime?"
                  description="An orbital regime defines the altitude band in which satellites operate. Each regime has unique tracking challenges due to different orbital periods, velocities, and observation geometries."
                  details={[
                    'LEO satellites complete an orbit in ~90 minutes and move quickly across the sky',
                    'MEO hosts navigation constellations (GPS, Galileo) at medium altitudes',
                    'GEO satellites appear stationary but are faint and far away',
                    'HEO objects follow elongated paths, making consistent tracking very difficult',
                  ]}
                  learnMore="The orbital regime fundamentally affects the difficulty of the UCT (Uncorrelated Track) processing problem. LEO objects generate many short observation tracks due to fast motion, requiring algorithms to associate observations across passes. GEO objects are nearly stationary but faint, creating a different association challenge. HEO objects have the most complex dynamics and are the hardest to track."
                  variant="concept"
                  size="md"
                  docsLink="/docs"
                  docsLabel="Orbital Regimes in Docs"
                />
              </div>
              <CardDescription>
                Choose the orbital environment for your benchmark dataset
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <RadioGroup
                value={config.regime}
                onValueChange={(value) => updateConfig('regime', value as OrbitalRegime)}
                className="grid sm:grid-cols-2 gap-4"
              >
                {([
                  {
                    value: 'LEO',
                    label: 'Low Earth Orbit',
                    altitude: '200 \u2013 2,000 km',
                    desc: 'Fast-moving satellites, short observation arcs, dense debris environment.',
                    color: 'orbital-leo',
                    icon: Orbit,
                    challenge: 'Many short tracks to correlate across passes',
                  },
                  {
                    value: 'MEO',
                    label: 'Medium Earth Orbit',
                    altitude: '2,000 \u2013 35,786 km',
                    desc: 'Navigation constellations (GPS, GLONASS, Galileo, BeiDou).',
                    color: 'orbital-meo',
                    icon: Satellite,
                    challenge: 'Moderate dynamics, fewer but longer tracks',
                  },
                  {
                    value: 'GEO',
                    label: 'Geostationary Orbit',
                    altitude: '~35,786 km',
                    desc: 'Communications satellites, nearly stationary from ground perspective.',
                    color: 'orbital-geo',
                    icon: Radio,
                    challenge: 'Faint objects, clustered in longitude slots',
                  },
                  {
                    value: 'HEO',
                    label: 'Highly Elliptical Orbit',
                    altitude: 'Variable (perigee to apogee)',
                    desc: 'Molniya-type orbits with extreme altitude variation.',
                    color: 'orbital-heo',
                    icon: Waves,
                    challenge: 'Complex dynamics, irregular observation patterns',
                  },
                ] as const).map((regime) => (
                  <Label
                    key={regime.value}
                    htmlFor={regime.value}
                    className={cn(
                      'flex flex-col rounded-xl border p-5 cursor-pointer transition-all duration-200',
                      'hover:bg-white/[0.02]',
                      config.regime === regime.value
                        ? `border-${regime.color}/40 bg-${regime.color}/5 ring-1 ring-${regime.color}/20`
                        : 'border-white/10 hover:border-white/20',
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <RadioGroupItem value={regime.value} id={regime.value} className="mt-1" />
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <div className={cn(`w-3 h-3 rounded-full bg-${regime.color}`)} />
                          <span className="font-semibold">{regime.label}</span>
                        </div>
                        <p className="text-xs text-muted-foreground font-mono">{regime.altitude}</p>
                        <p className="text-sm text-muted-foreground">{regime.desc}</p>
                        <div className={cn(
                          'flex items-start gap-2 rounded-lg p-2.5 mt-2',
                          config.regime === regime.value ? `bg-${regime.color}/10` : 'bg-white/5',
                        )}>
                          <Target className="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                          <span className="text-xs text-muted-foreground">
                            <span className="font-medium text-foreground/80">Challenge: </span>
                            {regime.challenge}
                          </span>
                        </div>
                      </div>
                    </div>
                  </Label>
                ))}
              </RadioGroup>

              <StepExplainer
                title="Why does the orbital regime matter?"
                description="Your algorithm faces fundamentally different challenges in each regime. LEO requires rapid track-to-track association across short observation windows, while GEO demands detecting faint objects clustered in narrow longitude bands."
                tips={[
                  'Start with LEO if you want the most common benchmark scenario',
                  'GEO is useful for testing association in crowded angular space',
                  'HEO is the most challenging due to highly variable orbital dynamics',
                ]}
                variant="tip"
                defaultOpen={false}
              />
            </CardContent>
          </>
        )}

        {/* ─── Step 3: Quality Parameters ────────────────────────── */}
        {currentStep === 3 && (
          <>
            <CardHeader>
              <div className="flex items-center gap-3">
                <CardTitle className="flex-1">Data Quality Parameters</CardTitle>
                <InfoPopover
                  title="Quality Parameters"
                  description="These settings control how much observation data is available and how it's distributed. They simulate the real-world variability in space surveillance coverage."
                  details={[
                    'Coverage: What fraction of the orbital arc has observations',
                    'Density: How many measurements per satellite per 3-day window',
                    'Track Gaps: The spacing between observation passes',
                  ]}
                  variant="info"
                  size="md"
                />
              </div>
              <CardDescription>
                Configure observation coverage, density, and gap characteristics
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-8">
              {/* Coverage */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <Label className="text-base font-medium">Orbital Coverage</Label>
                  <InfoPopover
                    title="Orbital Coverage"
                    description="The percentage of the satellite's orbital arc that is covered by ground-based sensor observations."
                    details={[
                      'High (>70%): Well-observed conditions with extensive sensor network coverage',
                      'Standard (30-70%): Typical operational conditions for most regimes',
                      'Low (<30%): Sparse coverage simulating limited sensor access or bad weather',
                      'Mixed: Varies per object, simulating real-world heterogeneity',
                    ]}
                    learnMore="In real-world space surveillance, coverage varies dramatically. A satellite may be well-observed over one ground station arc but have large gaps elsewhere. Low-coverage scenarios test whether your algorithm can maintain track association with minimal data \u2014 a critical capability for operational SSA."
                    variant="info"
                  />
                </div>
                <RadioGroup
                  value={config.coverage}
                  onValueChange={(value) => updateConfig('coverage', value as typeof config.coverage)}
                  className="grid grid-cols-2 sm:grid-cols-4 gap-2"
                >
                  {[
                    { value: 'high', label: 'High (>70%)', icon: '|||' },
                    { value: 'standard', label: 'Standard', icon: '|| ' },
                    { value: 'low', label: 'Low (<30%)', icon: '|  ' },
                    { value: 'mixed', label: 'Mixed', icon: '|.|' },
                  ].map((opt) => (
                    <Label
                      key={opt.value}
                      htmlFor={`coverage-${opt.value}`}
                      className={cn(
                        'flex items-center gap-2.5 rounded-xl border p-3.5 cursor-pointer transition-all duration-200',
                        config.coverage === opt.value
                          ? 'border-cosmic-cyan/40 bg-cosmic-cyan/5'
                          : 'border-white/10 hover:border-white/20 hover:bg-white/[0.02]',
                      )}
                    >
                      <RadioGroupItem value={opt.value} id={`coverage-${opt.value}`} />
                      <div>
                        <span className="text-sm font-medium">{opt.label}</span>
                      </div>
                    </Label>
                  ))}
                </RadioGroup>
                <p className="text-xs text-muted-foreground bg-white/[0.03] rounded-lg px-3 py-2 border border-white/5">
                  <Eye className="h-3 w-3 inline mr-1.5 text-cosmic-cyan" />
                  <span className="font-medium text-foreground/80">{config.coverage.charAt(0).toUpperCase() + config.coverage.slice(1)} coverage</span>
                  {' '}{config.coverage === 'low' ? 'simulates sparse observation scenarios where algorithms must work with incomplete data' : config.coverage === 'high' ? 'simulates well-observed conditions with extensive sensor network coverage' : config.coverage === 'mixed' ? 'varies per object, simulating real-world coverage heterogeneity' : 'simulates typical operational conditions'}.
                </p>
              </div>

              <Separator className="bg-white/5" />

              {/* Observation Density */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Observation Density</Label>
                    <InfoPopover
                      title="Observation Density"
                      description="The target number of individual measurements per satellite over a 3-day observation window."
                      details={[
                        'Sparse (10-30): Few observations, harder to determine orbits',
                        'Standard (40-70): Typical operational density',
                        'Dense (80+): Rich data, enables high-precision orbit determination',
                      ]}
                      learnMore="More observations generally enable better orbit determination, but there are diminishing returns. Real-world sensor tasking must balance coverage across thousands of objects. Your algorithm should perform well even with lower density data."
                      variant="info"
                    />
                  </div>
                  <span className="text-sm font-mono bg-white/5 border border-white/10 px-3 py-1.5 rounded-lg text-cosmic-cyan">
                    {config.observationDensity} obs/sat/3d
                  </span>
                </div>
                <Slider
                  value={[config.observationDensity]}
                  onValueChange={([value]) => updateConfig('observationDensity', value)}
                  min={10}
                  max={150}
                  step={5}
                  className="py-4"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Sparse (10)</span>
                  <span>Standard (50)</span>
                  <span>Dense (150)</span>
                </div>
              </div>

              <Separator className="bg-white/5" />

              {/* Track Gap Target */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <Label className="text-base font-medium">Track Gap Target</Label>
                  <InfoPopover
                    title="Track Gap Target"
                    description="The maximum gap between consecutive observation tracks, measured in orbital periods."
                    details={[
                      '1 period: Adjacent passes observed \u2014 easiest for association',
                      '2 periods: One missed pass \u2014 standard difficulty',
                      '3+ periods: Multiple missed passes \u2014 tests track-to-track correlation',
                    ]}
                    learnMore="When a satellite passes over a sensor, it creates a 'track' of several observations spanning minutes. The gap between tracks (measured in orbital periods) determines how far the satellite moves between observations. Larger gaps make it harder to associate tracks to the same object because the orbital uncertainty grows with time."
                    variant="info"
                  />
                </div>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((gap) => (
                    <Button
                      key={gap}
                      variant={config.trackGapTarget === gap ? 'default' : 'outline'}
                      className={cn(
                        'flex-1 transition-all duration-200',
                        config.trackGapTarget === gap
                          ? 'bg-cosmic-cyan/15 text-cosmic-cyan border-cosmic-cyan/30 hover:bg-cosmic-cyan/20'
                          : 'border-white/10 hover:border-white/20',
                      )}
                      onClick={() => updateConfig('trackGapTarget', gap)}
                    >
                      {gap}{gap === 5 ? '+' : ''} {gap === 1 ? 'rev' : 'revs'}
                    </Button>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground bg-white/[0.03] rounded-lg px-3 py-2 border border-white/5">
                  <Orbit className="h-3 w-3 inline mr-1.5 text-cosmic-cyan" />
                  <span className="font-medium text-foreground/80">{config.trackGapTarget} orbital period{config.trackGapTarget > 1 ? 's' : ''}</span>
                  {' \u2014 '}
                  {config.trackGapTarget <= 1 ? 'adjacent passes observed, easiest for track association.' :
                   config.trackGapTarget <= 2 ? 'standard difficulty, one missed pass between observations.' :
                   config.trackGapTarget <= 3 ? 'challenging scenario with multiple missed passes.' :
                   'very challenging \u2014 tests long-gap track-to-track correlation.'}
                </p>
              </div>
            </CardContent>
          </>
        )}

        {/* ─── Step 4: Object Selection ──────────────────────────── */}
        {currentStep === 4 && (
          <>
            <CardHeader>
              <div className="flex items-center gap-3">
                <CardTitle className="flex-1">Object Selection</CardTitle>
                <InfoPopover
                  title="Object Selection"
                  description="Configure how many satellites to include and the observation time window. More objects increase dataset complexity and processing requirements."
                  variant="info"
                  size="md"
                />
              </div>
              <CardDescription>
                Specify the number of objects, time window, and special object types
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-8">
              {/* Object Count */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Number of Objects</Label>
                    <InfoPopover
                      title="Object Count"
                      description="The number of distinct space objects (satellites, debris) included in the benchmark dataset."
                      details={[
                        '10-20: Quick testing and debugging',
                        '30-50: Standard benchmark size',
                        '100+: Stress-tests scalability',
                        '200: Maximum \u2014 simulates a dense observation environment',
                      ]}
                      variant="info"
                    />
                  </div>
                  <span className="text-sm font-mono bg-white/5 border border-white/10 px-3 py-1.5 rounded-lg text-cosmic-cyan">
                    {config.objectCount} satellites
                  </span>
                </div>
                <Slider
                  value={[config.objectCount]}
                  onValueChange={([value]) => updateConfig('objectCount', value)}
                  min={10}
                  max={200}
                  step={5}
                  className="py-4"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>10</span>
                  <span>50</span>
                  <span>100</span>
                  <span>150</span>
                  <span>200</span>
                </div>
              </div>

              <Separator className="bg-white/5" />

              {/* Date Range */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <Label className="text-base font-medium">Date Range</Label>
                  <InfoPopover
                    title="Observation Window"
                    description={`Select the time window for observation data. Maximum span is ${MAX_TIMEFRAME_DAYS} days. Only past dates are valid since we pull real observation data.`}
                    details={[
                      'Shorter windows (1-3 days): Less data but faster generation',
                      'Longer windows: More observation tracks for richer datasets',
                      'End date must be in the past (real data only)',
                    ]}
                    variant="info"
                  />
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="startDate" className="text-xs text-muted-foreground">Start Date</Label>
                    <Input
                      id="startDate"
                      type="date"
                      value={config.startDate}
                      max={config.endDate}
                      onChange={(e) => updateConfig('startDate', e.target.value)}
                      className={cn(
                        'border-white/10 bg-white/5',
                        timeframeError && 'border-destructive',
                      )}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="endDate" className="text-xs text-muted-foreground">End Date</Label>
                    <Input
                      id="endDate"
                      type="date"
                      value={config.endDate}
                      max={new Date().toISOString().split('T')[0]}
                      onChange={(e) => updateConfig('endDate', e.target.value)}
                      className={cn(
                        'border-white/10 bg-white/5',
                        timeframeError && 'border-destructive',
                      )}
                    />
                  </div>
                </div>
                {timeframeError ? (
                  <div className="flex items-center gap-2 text-destructive text-sm bg-destructive/5 border border-destructive/20 rounded-lg px-3 py-2.5">
                    <AlertCircle className="h-4 w-4 flex-shrink-0" />
                    {timeframeError}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground bg-white/[0.03] rounded-lg px-3 py-2 border border-white/5">
                    <Clock className="h-3 w-3 inline mr-1.5 text-cosmic-cyan" />
                    <span className="font-medium text-foreground/80">{calculatedTimeframe} day{calculatedTimeframe !== 1 ? 's' : ''}</span>
                    {' '}selected (max {MAX_TIMEFRAME_DAYS})
                  </p>
                )}
              </div>

              <Separator className="bg-white/5" />

              {/* HAMR Toggle */}
              <div className="flex items-start justify-between gap-4 rounded-xl border border-white/10 p-4 bg-white/[0.02]">
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Include HAMR Objects</Label>
                    <InfoPopover
                      title="HAMR Objects"
                      description="High Area-to-Mass Ratio objects are space debris with large surface area relative to their mass, causing significant atmospheric drag and solar radiation pressure effects."
                      details={[
                        'Examples: tumbling rocket bodies, shattered solar panels, MLI blankets',
                        'HAMR objects deviate from standard orbital mechanics models',
                        'Including HAMR tests your algorithm\'s robustness to non-standard dynamics',
                        'Requires UCS/GCAT metadata for identification',
                      ]}
                      learnMore="HAMR objects are one of the hardest challenges in space surveillance. Their orbits can decay or shift unpredictably due to solar radiation pressure, making standard orbit propagation models inaccurate. Algorithms must detect these objects and apply special handling \u2014 or at least avoid false associations caused by unexpected motion."
                      variant="warning"
                    />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Include tumbling debris and objects with non-standard dynamics
                  </p>
                </div>
                <Switch
                  checked={config.includeHamr}
                  onCheckedChange={(checked) => updateConfig('includeHamr', checked)}
                />
              </div>
            </CardContent>
          </>
        )}

        {/* ─── Step 5: Advanced Options ──────────────────────────── */}
        {currentStep === 5 && (
          <>
            <CardHeader>
              <div className="flex items-center gap-3">
                <CardTitle className="flex-1">Advanced Options</CardTitle>
                <InfoPopover
                  title="Advanced Configuration"
                  description="Fine-tune how observation data is fetched, manipulated, and augmented. These options let you simulate specific data conditions."
                  variant="info"
                  size="md"
                />
              </div>
              <CardDescription>
                Configure data fetching strategy, downsampling, and simulation settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-8">
              {/* Search Strategy */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <Label className="text-base font-medium">Data Fetching Strategy</Label>
                  <InfoPopover
                    title="Data Fetching Strategy"
                    description="Controls how observation data is retrieved from the UDL API. Different strategies balance speed vs. data completeness."
                    details={[
                      'Fast: Single API query per satellite \u2014 may hit row limits',
                      'Hybrid: Checks data volume first, chunks if needed \u2014 best balance',
                      'Windowed: Fixed time windows like reference implementation \u2014 guaranteed complete',
                    ]}
                    variant="info"
                  />
                </div>

                <RadioGroup
                  value={config.searchStrategy}
                  onValueChange={(value) => updateConfig('searchStrategy', value as SearchStrategy)}
                  className="grid gap-3"
                >
                  {([
                    {
                      value: 'fast' as const,
                      icon: Zap,
                      label: 'Fast Search',
                      badge: 'Fastest',
                      badgeVariant: 'outline' as const,
                      desc: 'Single query per satellite. May hit API limits for large time ranges.',
                      color: 'nova-orange',
                    },
                    {
                      value: 'hybrid' as const,
                      icon: Settings2,
                      label: 'Hybrid Search',
                      badge: 'Recommended',
                      badgeVariant: 'default' as const,
                      desc: 'Checks data volume first, chunks if needed. Best balance of speed and completeness.',
                      color: 'cosmic-cyan',
                    },
                    {
                      value: 'windowed' as const,
                      icon: Clock,
                      label: 'Windowed Search',
                      badge: 'Reference-Compatible',
                      badgeVariant: 'secondary' as const,
                      desc: 'Uses fixed time windows like reference code. Guaranteed complete but slower.',
                      color: 'stellar-purple',
                    },
                  ]).map((opt) => (
                    <Label
                      key={opt.value}
                      htmlFor={`strategy-${opt.value}`}
                      className={cn(
                        'flex items-start gap-4 rounded-xl border p-4 cursor-pointer transition-all duration-200',
                        config.searchStrategy === opt.value
                          ? `border-${opt.color}/40 bg-${opt.color}/5`
                          : 'border-white/10 hover:border-white/20 hover:bg-white/[0.02]',
                      )}
                    >
                      <RadioGroupItem value={opt.value} id={`strategy-${opt.value}`} className="mt-1" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <opt.icon className="h-4 w-4" />
                          <span className="font-medium">{opt.label}</span>
                          <Badge variant={opt.badgeVariant} className="text-[10px]">{opt.badge}</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">{opt.desc}</p>
                      </div>
                    </Label>
                  ))}
                </RadioGroup>

                {/* Window size slider */}
                {config.searchStrategy === 'windowed' && (
                  <div className="ml-6 pl-6 border-l-2 border-stellar-purple/20 space-y-3">
                    <div className="flex justify-between items-center">
                      <Label className="text-sm">Window Size</Label>
                      <span className="text-sm font-mono bg-white/5 border border-white/10 px-2 py-1 rounded-lg text-stellar-purple">
                        {config.windowSizeMinutes || 10} min
                      </span>
                    </div>
                    <Slider
                      value={[config.windowSizeMinutes || 10]}
                      onValueChange={([v]) => updateConfig('windowSizeMinutes', v)}
                      min={5}
                      max={60}
                      step={5}
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>5 min (more queries)</span>
                      <span>60 min (fewer queries)</span>
                    </div>
                  </div>
                )}
              </div>

              <Separator className="bg-white/5" />

              {/* Downsampling */}
              <div className="space-y-4">
                <div className="flex items-start justify-between gap-4 rounded-xl border border-white/10 p-4 bg-white/[0.02]">
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <Label className="text-base font-medium">Enable Downsampling</Label>
                      <InfoPopover
                        title="Downsampling"
                        description="Reduces observation quality by removing observations while preserving track structure. This simulates sparse data scenarios."
                        details={[
                          'Target Coverage: Percentage of observations to retain',
                          'Target Gap: Gap size between observation tracks in orbital periods',
                          'Max Obs/Sat: Hard cap on observations per satellite',
                          'Preserve Tracks: Keep first/last observations of each track for realistic arcs',
                        ]}
                        learnMore="Downsampling is essential for creating datasets that test algorithm robustness under data-sparse conditions. Real-world sensors often miss passes due to weather, maintenance, or tasking conflicts. By downsampling, you simulate these gaps in a controlled way while maintaining the physical structure of observation tracks."
                        variant="info"
                      />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Reduce observation density to simulate challenging data conditions
                    </p>
                  </div>
                  <Switch
                    checked={config.downsampling?.enabled ?? false}
                    onCheckedChange={(checked) => updateDownsampling('enabled', checked)}
                  />
                </div>

                {config.downsampling?.enabled && (
                  <div className="ml-6 space-y-6 border-l-2 pl-6 border-cosmic-cyan/20">
                    {/* Target Coverage */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Label className="text-sm">Target Coverage</Label>
                        <span className="text-sm font-mono bg-white/5 border border-white/10 px-2 py-1 rounded-lg text-cosmic-cyan">
                          {((config.downsampling?.targetCoverage ?? 0.05) * 100).toFixed(0)}%
                        </span>
                      </div>
                      <Slider
                        value={[(config.downsampling?.targetCoverage ?? 0.05) * 100]}
                        onValueChange={([value]) => updateDownsampling('targetCoverage', value / 100)}
                        min={1}
                        max={100}
                        step={1}
                      />
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>Sparse (1%)</span>
                        <span>Full (100%)</span>
                      </div>
                    </div>

                    {/* Target Gap */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Label className="text-sm">Target Gap (orbital periods)</Label>
                        <span className="text-sm font-mono bg-white/5 border border-white/10 px-2 py-1 rounded-lg text-cosmic-cyan">
                          {(config.downsampling?.targetGap ?? 2.0).toFixed(1)}
                        </span>
                      </div>
                      <Slider
                        value={[(config.downsampling?.targetGap ?? 2.0) * 10]}
                        onValueChange={([value]) => updateDownsampling('targetGap', value / 10)}
                        min={5}
                        max={100}
                        step={5}
                      />
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>Small (0.5)</span>
                        <span>Large (10)</span>
                      </div>
                    </div>

                    {/* Max Obs Per Satellite */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Label className="text-sm">Max Observations Per Satellite</Label>
                        <span className="text-sm font-mono bg-white/5 border border-white/10 px-2 py-1 rounded-lg text-cosmic-cyan">
                          {config.downsampling?.maxObsPerSat ?? 50}
                        </span>
                      </div>
                      <Slider
                        value={[config.downsampling?.maxObsPerSat ?? 50]}
                        onValueChange={([value]) => updateDownsampling('maxObsPerSat', value)}
                        min={5}
                        max={200}
                        step={5}
                      />
                    </div>

                    {/* Preserve Tracks */}
                    <div className="flex items-center justify-between rounded-lg border border-white/10 p-3 bg-white/[0.02]">
                      <div className="space-y-0.5">
                        <Label className="text-sm">Preserve Track Boundaries</Label>
                        <p className="text-xs text-muted-foreground">
                          Keep first and last observations of each track arc
                        </p>
                      </div>
                      <Switch
                        checked={config.downsampling?.preserveTracks ?? true}
                        onCheckedChange={(checked) => updateDownsampling('preserveTracks', checked)}
                      />
                    </div>
                  </div>
                )}
              </div>

              <Separator className="bg-white/5" />

              {/* Simulation */}
              <div className="space-y-4">
                <div className="flex items-start justify-between gap-4 rounded-xl border border-white/10 p-4 bg-white/[0.02]">
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <Label className="text-base font-medium">Enable Gap-Filling Simulation</Label>
                      <InfoPopover
                        title="Gap-Filling Simulation"
                        description="Generates synthetic observations to fill gaps in the real observation data using physics-based orbital propagation."
                        details={[
                          'Uses real orbits as basis, then propagates to fill gaps',
                          'Applies realistic sensor noise based on selected sensor model',
                          'Max Synthetic Ratio caps how much data can be simulated',
                          'Useful for testing algorithms on denser data without all-real observations',
                        ]}
                        learnMore="Gap-filling simulation creates Tier 3 (T3) style data by propagating known orbits forward and simulating what a sensor would observe. The sensor noise models (GEODSS, SBSS, Commercial EO) add realistic measurement uncertainty. This is useful when you need dense data but only have sparse real observations \u2014 common in algorithm development."
                        variant="info"
                      />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Fill observation gaps with physics-based simulated data
                    </p>
                  </div>
                  <Switch
                    checked={config.simulation?.enabled ?? false}
                    onCheckedChange={(checked) => updateSimulation('enabled', checked)}
                  />
                </div>

                {config.simulation?.enabled && (
                  <div className="ml-6 space-y-6 border-l-2 pl-6 border-stellar-purple/20">
                    {/* Sensor Model */}
                    <div className="space-y-3">
                      <div className="flex items-center gap-2">
                        <Label className="text-sm">Sensor Noise Model</Label>
                        <InfoPopover
                          title="Sensor Noise Models"
                          description="Each sensor type has different measurement characteristics and noise profiles."
                          details={[
                            'GEODSS: Ground-based Electro-Optical Deep Space Surveillance. High-precision optical for deep space.',
                            'SBSS: Space-Based Space Surveillance satellite. Observes from orbit with different noise.',
                            'Commercial EO: Commercial electro-optical sensors with typical industry noise levels.',
                          ]}
                          variant="info"
                        />
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        {(['GEODSS', 'SBSS', 'Commercial_EO'] as const).map((model) => (
                          <Button
                            key={model}
                            variant={config.simulation?.sensorModel === model ? 'default' : 'outline'}
                            size="sm"
                            className={cn(
                              'transition-all duration-200',
                              config.simulation?.sensorModel === model
                                ? 'bg-stellar-purple/15 text-stellar-purple border-stellar-purple/30'
                                : 'border-white/10',
                            )}
                            onClick={() => updateSimulation('sensorModel', model)}
                          >
                            {model.replace('_', ' ')}
                          </Button>
                        ))}
                      </div>
                    </div>

                    {/* Max Synthetic Ratio */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Label className="text-sm">Max Synthetic Ratio</Label>
                        <span className="text-sm font-mono bg-white/5 border border-white/10 px-2 py-1 rounded-lg text-stellar-purple">
                          {((config.simulation?.maxSyntheticRatio ?? 0.5) * 100).toFixed(0)}%
                        </span>
                      </div>
                      <Slider
                        value={[(config.simulation?.maxSyntheticRatio ?? 0.5) * 100]}
                        onValueChange={([value]) => updateSimulation('maxSyntheticRatio', value / 100)}
                        min={10}
                        max={90}
                        step={5}
                      />
                      <p className="text-xs text-muted-foreground">
                        Maximum percentage of observations that can be synthetic
                      </p>
                    </div>

                    {/* Apply Noise */}
                    <div className="flex items-center justify-between rounded-lg border border-white/10 p-3 bg-white/[0.02]">
                      <div className="space-y-0.5">
                        <Label className="text-sm">Apply Realistic Noise</Label>
                        <p className="text-xs text-muted-foreground">
                          Add sensor-specific measurement noise to simulated observations
                        </p>
                      </div>
                      <Switch
                        checked={config.simulation?.applyNoise ?? true}
                        onCheckedChange={(checked) => updateSimulation('applyNoise', checked)}
                      />
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </>
        )}

        {/* ─── Step 6: Review & Generate ─────────────────────────── */}
        {currentStep === 6 && (
          <>
            <CardHeader>
              <CardTitle>Review Configuration</CardTitle>
              <CardDescription>
                Verify your dataset configuration before generation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {isGenerating ? (
                <div className="space-y-6 py-8">
                  <div className="flex flex-col items-center gap-4">
                    <div className="relative">
                      <div className="w-16 h-16 rounded-full border-2 border-cosmic-cyan/20 flex items-center justify-center">
                        <Loader2 className="h-8 w-8 animate-spin text-cosmic-cyan" />
                      </div>
                      <div className="absolute inset-0 rounded-full border-2 border-cosmic-cyan/10 animate-ping" />
                    </div>
                    <span className="text-lg font-display font-semibold">Generating dataset...</span>
                    <p className="text-sm text-muted-foreground text-center max-w-md">
                      {jobStatus?.stage || 'Initializing pipeline...'}
                    </p>
                  </div>
                  <Progress value={generationProgress} className="w-full max-w-md mx-auto" />
                  <p className="text-center text-xs text-muted-foreground">
                    {generationProgress}% complete
                  </p>
                </div>
              ) : (
                <>
                  {/* Config Summary Grid */}
                  <div className="grid sm:grid-cols-2 gap-3">
                    <ReviewCard
                      label="Orbital Regime"
                      value={config.regime}
                      subtitle={
                        config.regime === 'LEO' ? 'Low Earth Orbit' :
                        config.regime === 'MEO' ? 'Medium Earth Orbit' :
                        config.regime === 'GEO' ? 'Geostationary Orbit' : 'Highly Elliptical Orbit'
                      }
                      color={
                        config.regime === 'LEO' ? 'cyan' :
                        config.regime === 'MEO' ? 'green' :
                        config.regime === 'GEO' ? 'orange' : 'red'
                      }
                    />
                    <ReviewCard label="Coverage" value={config.coverage} capitalize color="cyan" />
                    <ReviewCard label="Observation Density" value={`${config.observationDensity}`} subtitle="obs/satellite/3-days" color="purple" />
                    <ReviewCard label="Track Gap Target" value={`${config.trackGapTarget}`} subtitle="orbital periods" color="blue" />
                    <ReviewCard label="Objects" value={`${config.objectCount}`} subtitle={config.includeHamr ? 'Including HAMR objects' : 'Standard objects only'} color="cyan" />
                    <ReviewCard
                      label="Date Range"
                      value={`${calculatedTimeframe}d`}
                      subtitle={`${config.startDate} \u2192 ${config.endDate}`}
                      color="purple"
                    />
                    <ReviewCard
                      label="Search Strategy"
                      value={config.searchStrategy === 'fast' ? 'Fast' : config.searchStrategy === 'hybrid' ? 'Hybrid' : 'Windowed'}
                      subtitle={config.searchStrategy === 'windowed' ? `${config.windowSizeMinutes || 10} min windows` : undefined}
                      color="blue"
                    />
                    <ReviewCard
                      label="Downsampling"
                      value={config.downsampling?.enabled ? 'Enabled' : 'Disabled'}
                      subtitle={config.downsampling?.enabled ? `${((config.downsampling?.targetCoverage ?? 0.05) * 100).toFixed(0)}% coverage, ${config.downsampling?.maxObsPerSat ?? 50} max obs/sat` : undefined}
                      color={config.downsampling?.enabled ? 'green' : 'muted'}
                    />
                    <ReviewCard
                      label="Simulation"
                      value={config.simulation?.enabled ? 'Enabled' : 'Disabled'}
                      subtitle={config.simulation?.enabled ? `${config.simulation?.sensorModel}, max ${((config.simulation?.maxSyntheticRatio ?? 0.5) * 100).toFixed(0)}% synthetic` : undefined}
                      color={config.simulation?.enabled ? 'green' : 'muted'}
                    />
                  </div>

                  {/* Data Sources Summary */}
                  <div className="rounded-xl border border-cosmic-cyan/20 p-4 space-y-3 bg-cosmic-cyan/5">
                    <div className="flex items-center gap-2">
                      <Database className="h-5 w-5 text-cosmic-cyan" />
                      <h4 className="font-semibold text-sm">Data Sources</h4>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge className="bg-cosmic-cyan/15 text-cosmic-cyan border-cosmic-cyan/30">UDL</Badge>
                      <Badge className="bg-cosmic-cyan/15 text-cosmic-cyan border-cosmic-cyan/30">ESA</Badge>
                      {config.openSource?.enableEnrichment && (
                        <>
                          <Badge variant="secondary">UCS</Badge>
                          <Badge variant="secondary">GCAT</Badge>
                        </>
                      )}
                      {(config.openSource?.sensorMode === 'MX' || config.openSource?.sensorMode === 'RF') && (
                        <Badge variant="secondary">SatNOGS</Badge>
                      )}
                      {config.openSource?.includeIlrsValidation && (
                        <Badge className="bg-aurora-green/15 text-aurora-green border-aurora-green/30">ILRS</Badge>
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-sm mt-2">
                      <div>
                        <span className="text-muted-foreground text-xs">Tier: </span>
                        <span className="font-medium">{config.tier}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground text-xs">Sensor: </span>
                        <span className="font-medium">
                          {config.openSource?.sensorMode === 'EO' ? 'Optical Only' :
                           config.openSource?.sensorMode === 'RF' ? 'RF Only' : 'Multi-Phenom'}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground text-xs">Enrichment: </span>
                        <span className="font-medium">{config.openSource?.enableEnrichment ? 'Yes' : 'No'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Validation */}
                  {timeframeError && (
                    <div className="flex items-center gap-3 p-4 rounded-xl bg-destructive/5 border border-destructive/20 text-destructive">
                      <AlertCircle className="h-5 w-5 flex-shrink-0" />
                      <div>
                        <p className="font-medium text-sm">Invalid Configuration</p>
                        <p className="text-sm opacity-80">{timeframeError}</p>
                      </div>
                    </div>
                  )}

                  {/* Estimated Output */}
                  <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                    <h4 className="font-medium text-sm mb-3 flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-cosmic-cyan" />
                      Estimated Output
                    </h4>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground text-xs">Observations</p>
                        <p className="font-display font-bold text-lg">~{(config.objectCount * config.observationDensity).toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground text-xs">File Size</p>
                        <p className="font-display font-bold text-lg">~{(config.objectCount * 0.05).toFixed(1)} MB</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground text-xs">Format</p>
                        <p className="font-display font-bold text-lg">JSON</p>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </>
        )}

        {/* ── Navigation Buttons ─────────────────────────────────── */}
        <div className="flex justify-between p-6 pt-0">
          <Button
            variant="outline"
            onClick={prevStep}
            disabled={currentStep === 1 || isGenerating}
            className="gap-2 border-white/10"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
          {currentStep < 6 ? (
            <Button
              onClick={nextStep}
              className="gap-2 bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity"
              disabled={(currentStep === 1 && !selectedPreset) || (currentStep === 4 && !isTimeframeValid)}
            >
              Next
              <ArrowRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              onClick={handleGenerate}
              disabled={isGenerating || !isTimeframeValid}
              className="gap-2 bg-gradient-to-r from-cosmic-cyan via-cosmic-blue to-stellar-purple hover:opacity-90 transition-opacity"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Generate Dataset
                </>
              )}
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ReviewCard  –  Summary card for the review step                     */
/* ------------------------------------------------------------------ */

function ReviewCard({ label, value, subtitle, color, capitalize }: {
  label: string;
  value: string;
  subtitle?: string;
  color: string;
  capitalize?: boolean;
}) {
  const colorMap: Record<string, string> = {
    cyan: 'border-cosmic-cyan/20 bg-cosmic-cyan/5',
    purple: 'border-stellar-purple/20 bg-stellar-purple/5',
    blue: 'border-cosmic-blue/20 bg-cosmic-blue/5',
    green: 'border-aurora-green/20 bg-aurora-green/5',
    orange: 'border-nova-orange/20 bg-nova-orange/5',
    red: 'border-red-400/20 bg-red-400/5',
    muted: 'border-white/10 bg-white/[0.02]',
  };

  return (
    <div className={cn('rounded-xl border p-4 space-y-1', colorMap[color] || colorMap.muted)}>
      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">{label}</p>
      <p className={cn('text-xl font-display font-bold', capitalize && 'capitalize')}>{value}</p>
      {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
    </div>
  );
}
