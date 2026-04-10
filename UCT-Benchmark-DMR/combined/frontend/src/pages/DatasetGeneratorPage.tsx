import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGenerateDataset, useJobStatus, useDatasetConfig, MAX_TIMEFRAME_DAYS } from '@/hooks/useDatasets';
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Clock,
  Info,
  Satellite,
  Zap,
  Settings2,
  FileCheck,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { ToastAction } from '@/components/ui/toast';
import { DataSourceStatusIndicator } from '@/components/generator/DataSourceStatusIndicator';
import { api, apiClient } from '@/api/client';
import type {
  OrbitalRegime,
  DatasetGenerationConfig,
  DownsamplingOptions,
  SimulationOptions,
  SearchStrategy,
  LegacyDatasetCodeConfig,
  LegacyObjectType,
  TargetPercentage,
  LegacyEventType,
  LegacySensorType,
  QualityLevel,
  ObjectCountLevel,
} from '@/types';
import {
  LEGACY_OBJECT_TYPES,
  TARGET_PERCENTAGES,
  LEGACY_EVENT_TYPES,
  LEGACY_SENSOR_TYPES,
  QUALITY_LEVELS,
  OBJECT_COUNT_LEVELS,
  generateLegacyCode,
  parseLegacyCode,
  validateLegacyCode,
} from '@/types';
import {
  Tabs,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// Fallback coverage thresholds in case backend config endpoint is unavailable
// Combo regimes use the most permissive (largest) threshold of their constituents
// so a satellite only qualifies as "low" if it's low for ALL regimes in the combo.
const DEFAULT_COVERAGE_THRESHOLDS: Record<OrbitalRegime, { low: number; display: string }> = {
  LEO: { low: 0.000213, display: '<0.02%' },
  MEO: { low: 0.000449, display: '<0.05%' },
  GEO: { low: 0.41656, display: '<42%' },
  HEO: { low: 0.20, display: '<20%' },
  ALL: { low: 0.10, display: '<10%' },
  // 2-regime combos
  LMO: { low: 0.000331, display: '<0.03%' },  // LEO+MEO
  LGO: { low: 0.20843, display: '<21%' },     // LEO+GEO
  LHO: { low: 0.10011, display: '<10%' },     // LEO+HEO
  MGO: { low: 0.20850, display: '<21%' },     // MEO+GEO
  MHO: { low: 0.10022, display: '<10%' },     // MEO+HEO
  GHO: { low: 0.30828, display: '<31%' },     // GEO+HEO
  // 3-regime combos
  LMG: { low: 0.14, display: '<14%' },        // LEO+MEO+GEO
  LMH: { low: 0.06689, display: '<7%' },      // LEO+MEO+HEO
  LGH: { low: 0.20559, display: '<21%' },     // LEO+GEO+HEO
  MGH: { low: 0.20, display: '<20%' },        // MEO+GEO+HEO
};

function buildThresholds(
  backendThresholds?: Record<string, number>
): Record<OrbitalRegime, { low: number; display: string }> {
  if (!backendThresholds) return DEFAULT_COVERAGE_THRESHOLDS;
  const result = { ...DEFAULT_COVERAGE_THRESHOLDS };
  for (const regime of ['LEO', 'MEO', 'GEO', 'HEO'] as OrbitalRegime[]) {
    if (regime in backendThresholds) {
      const val = backendThresholds[regime];
      const pct = val * 100;
      result[regime] = {
        low: val,
        display: pct < 1 ? `<${pct.toFixed(2)}%` : `<${Math.round(pct)}%`,
      };
    }
  }
  return result;
}

// Get coverage option labels based on selected regime
function getCoverageOptions(
  regime: OrbitalRegime,
  thresholds: Record<OrbitalRegime, { low: number; display: string }>
): { value: string; label: string }[] {
  const threshold = thresholds[regime] || thresholds.LEO;
  if (regime === 'GEO') {
    return [
      { value: 'high', label: 'High (>60%)' },
      { value: 'standard', label: `Standard (${threshold.display}-60%)` },
      { value: 'low', label: `Low (${threshold.display})` },
      { value: 'mixed', label: 'Mixed' },
    ];
  }
  return [
    { value: 'high', label: 'High (>5%)' },
    { value: 'standard', label: `Standard (${threshold.display}-5%)` },
    { value: 'low', label: `Low (${threshold.display})` },
    { value: 'mixed', label: 'Mixed' },
  ];
}

// Standard wizard steps
const steps = [
  { id: 1, name: 'Regime', icon: Satellite },
  { id: 2, name: 'Quality', icon: Settings2 },
  { id: 3, name: 'Objects', icon: Zap },
  { id: 4, name: 'Advanced', icon: Settings2 },
  { id: 5, name: 'Review', icon: FileCheck },
];

// Legacy code wizard steps
const legacySteps = [
  { id: 1, name: 'Object', icon: Satellite },
  { id: 2, name: 'Regime', icon: Satellite },
  { id: 3, name: 'Event', icon: Settings2 },
  { id: 4, name: 'Sensor', icon: Settings2 },
  { id: 5, name: 'Quality', icon: Zap },
  { id: 6, name: 'Objects', icon: Zap },
  { id: 7, name: 'Review', icon: FileCheck },
];

// Default legacy code config
const defaultLegacyConfig: LegacyDatasetCodeConfig = {
  objectType: 'U',
  targetPercentage: '50',
  orbitalRegime: 'LEO',
  event: 'NE',
  sensorType: 'OP',
  orbitCoverage: 'S',
  trackGap: 'S',
  observationCount: 'S',
  objectCount: 'S',
  fitspanDays: 7,
};

// Calculate timeframe in days from start and end dates
function calculateTimeframeDays(startDate: string, endDate: string): number {
  const start = new Date(startDate);
  const end = new Date(endDate);
  if (isNaN(start.getTime()) || isNaN(end.getTime())) {
    return 0;
  }
  return Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
}

// Generate a 16-character dataset code from the Standard Wizard config
// Maps user-friendly Standard Wizard values to legacy code positions
function generateStandardWizardCode(cfg: DatasetGenerationConfig): string {
  // Position 1: Object Type
  const objectType = cfg.objectTypeCode ?? 'U';

  // Positions 2-3: Target Percentage
  const targetPct = cfg.targetPercentage ?? 'UN';

  // Positions 4-6: Orbital Regime (direct map)
  const regime = cfg.regime; // LEO, MEO, GEO, HEO

  // Positions 7-8: Event Type
  const event = cfg.eventCode ?? 'NE';

  // Positions 9-10: Sensor Type
  const sensor = cfg.sensorTypeCode ?? 'OP';

  // Position 11: Coverage (map standard wizard values to A/S/N)
  const coverageMap: Record<string, string> = { high: 'N', standard: 'S', low: 'A', mixed: 'S' };
  const coverage = coverageMap[cfg.coverage] ?? 'S';

  // Position 12: Track Gap (map gap target to A/S/N)
  const trackGap = cfg.trackGapTarget <= 1 ? 'N' : cfg.trackGapTarget <= 2 ? 'S' : 'A';

  // Position 13: Observation Density (map obs count to A/S/N)
  const obsDensity = cfg.observationDensity > 100 ? 'N' : cfg.observationDensity >= 30 ? 'S' : 'A';

  // Position 14: Object Count (map count to H/S/L)
  const objCount = cfg.objectCount > 60 ? 'H' : cfg.objectCount >= 20 ? 'S' : 'L';

  // Positions 15-16: Fitspan Days (zero-padded)
  const fitspan = (cfg.fitspanDays ?? 7).toString().padStart(2, '0');

  return objectType + targetPct + regime + event + sensor + coverage + trackGap + obsDensity + objCount + fitspan;
}

// Describe each position of the 16-character code for tooltips
const CODE_POSITION_LABELS: { pos: string; label: string }[] = [
  { pos: '1', label: 'Object Type' },
  { pos: '2-3', label: 'Target %' },
  { pos: '4-6', label: 'Regime' },
  { pos: '7-8', label: 'Event' },
  { pos: '9-10', label: 'Sensor' },
  { pos: '11', label: 'Coverage' },
  { pos: '12', label: 'Track Gap' },
  { pos: '13', label: 'Obs Density' },
  { pos: '14', label: 'Object Count' },
  { pos: '15-16', label: 'Fitspan' },
];

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

const defaultConfig: DatasetGenerationConfig = {
  regime: 'LEO',
  coverage: 'standard',
  observationDensity: 50,
  trackGapTarget: 2,
  objectCount: 40,
  includeHamr: false,
  // Use past dates: end date is yesterday, start date is 3 days before that
  startDate: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  endDate: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  sensors: ['optical'],
  downsampling: defaultDownsampling,
  simulation: defaultSimulation,
  searchStrategy: 'hybrid',
  windowSizeMinutes: 10,
  // Dataset code positions (all 16 positions exposed)
  objectTypeCode: 'U',
  targetPercentage: 'UN',
  eventCode: 'NE',
  sensorTypeCode: 'OP',
  fitspanDays: 7,
};

export function DatasetGeneratorPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [currentStep, setCurrentStep] = useState(1);
  const [config, setConfig] = useState<DatasetGenerationConfig>(defaultConfig);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);

  // Token availability check
  const [hasUdlToken, setHasUdlToken] = useState<boolean | null>(null);

  useEffect(() => {
    // Check credentials table first (new system), fall back to legacy profile token
    api.getCredential('udl').then((res) => {
      setHasUdlToken(res.data.is_configured);
    }).catch(() => {
      api.getCurrentUser().then((res) => {
        setHasUdlToken(!!res.data.udl_token);
      }).catch(() => {
        setHasUdlToken(false);
      });
    });
  }, []);

  // Optional user-provided dataset name
  const [customName, setCustomName] = useState('');

  // Legacy code mode state
  const [mode, setMode] = useState<'standard' | 'legacy'>('standard');
  const [legacyConfig, setLegacyConfig] = useState<LegacyDatasetCodeConfig>(defaultLegacyConfig);
  const [legacyStep, setLegacyStep] = useState(1);
  const [directCodeInput, setDirectCodeInput] = useState('');
  const [codeInputMode, setCodeInputMode] = useState<'wizard' | 'direct'>('wizard');

  const generateDatasetMutation = useGenerateDataset();
  const { data: jobStatus } = useJobStatus(jobId);
  const { data: datasetConfig } = useDatasetConfig();
  const coverageThresholds = buildThresholds(datasetConfig?.coverage_thresholds);

  // Generate the legacy code from current config
  const currentLegacyCode = generateLegacyCode(legacyConfig);
  const legacyCodeValidation = validateLegacyCode(codeInputMode === 'direct' ? directCodeInput : currentLegacyCode);

  // Calculate and validate the timeframe
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

  // Track job progress
  useEffect(() => {
    if (jobStatus) {
      setGenerationProgress(jobStatus.progress);
      if (jobStatus.status === 'completed') {
        setIsGenerating(false);
        // Extract dataset info from job result for the notification
        const result = jobStatus.result as { dataset_id?: string } | undefined;
        const datasetId = result?.dataset_id;
        const datasetName = customName.trim() || `${config.regime}-${config.coverage}`;
        toast({
          title: 'Dataset generated',
          description: `Your dataset "${datasetName}" was successfully generated!`,
          action: datasetId ? (
            <ToastAction altText="View dataset" onClick={() => navigate(`/datasets/${datasetId}`)}>
              View Dataset
            </ToastAction>
          ) : undefined,
        });
        // Navigate to my-datasets with highlight param so the new row pulses
        navigate(datasetId ? `/datasets/my-datasets?highlight=${datasetId}` : '/datasets/my-datasets');
      } else if (jobStatus.status === 'failed') {
        let errorMessage = jobStatus.error || 'Dataset generation failed. Please try different parameters.';
        if (errorMessage.includes('No observation data returned') || errorMessage.includes('No observations found')) {
          errorMessage = 'No observation data is available for the selected parameters. Try a different orbital regime, date range, or sensor type.';
        } else if (errorMessage.includes('Missing required environment variable') || errorMessage.includes('API credential')) {
          errorMessage = 'The dataset generation service is temporarily unavailable. Please try again later or contact support.';
        }
        toast({
          title: 'Dataset generation failed',
          description: errorMessage,
          variant: 'destructive',
        });
        setIsGenerating(false);
        setJobId(null);
      }
    }
  }, [jobStatus, navigate, toast, customName, config.regime, config.coverage]);

  const updateConfig = <K extends keyof DatasetGenerationConfig>(
    key: K,
    value: DatasetGenerationConfig[K]
  ) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const nextStep = () => setCurrentStep((prev) => Math.min(prev + 1, 5));
  const prevStep = () => setCurrentStep((prev) => Math.max(prev - 1, 1));

  // Legacy mode navigation
  const nextLegacyStep = () => setLegacyStep((prev) => Math.min(prev + 1, 7));
  const prevLegacyStep = () => setLegacyStep((prev) => Math.max(prev - 1, 1));

  // Update legacy config
  const updateLegacyConfig = <K extends keyof LegacyDatasetCodeConfig>(
    key: K,
    value: LegacyDatasetCodeConfig[K]
  ) => {
    setLegacyConfig((prev) => ({ ...prev, [key]: value }));
  };

  // Handle direct code input
  const handleDirectCodeInput = (code: string) => {
    setDirectCodeInput(code.toUpperCase());
    if (code.length === 16) {
      const parsed = parseLegacyCode(code.toUpperCase());
      if (parsed) {
        setLegacyConfig(parsed);
      }
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

    // Use custom name if provided, otherwise auto-generate
    const datasetName = customName.trim() || `${config.regime}-${config.coverage}`;

    try {
      const result = await generateDatasetMutation.mutateAsync({
        ...config,
        name: datasetName,
      });
      console.log('Generation result:', result);
      // The API returns a job_id for tracking progress
      if (result?.job_id) {
        setJobId(result.job_id);
      } else {
        // If no job tracking, navigate after a short delay
        setTimeout(() => {
          setIsGenerating(false);
          navigate('/datasets/my-datasets');
        }, 1000);
      }
    } catch (error: unknown) {
      const axiosErr = error as { response?: { data?: { detail?: string | Array<{ loc?: string[]; msg?: string }> } }; message?: string };
      console.error('Failed to generate dataset:', error);
      console.error('Error response:', axiosErr?.response?.data);

      // Handle Pydantic validation errors which return an array of error details
      let errorMessage = 'An unexpected error occurred. Please try again.';
      const detail = axiosErr?.response?.data?.detail;
      if (Array.isArray(detail)) {
        // Pydantic validation error - format each error
        errorMessage = detail.map((e) =>
          `${e.loc?.join(' -> ')}: ${e.msg}`
        ).join('\n');
      } else if (typeof detail === 'string') {
        errorMessage = detail;
        // Only mark token as missing for genuinely-missing-token errors,
        // not for validation failures like "token validation failed"
        if (detail.toLowerCase().includes('token required') ||
            detail.toLowerCase().includes('re-enter your token')) {
          setHasUdlToken(false);
        }
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }

      // Map technical errors to user-friendly messages
      if (errorMessage.includes('No observation data returned')) {
        errorMessage = 'No observation data is available for the selected parameters. Try a different orbital regime, date range, or sensor type.';
      } else if (errorMessage.includes('network') || errorMessage.includes('Network') || errorMessage.includes('ECONNREFUSED')) {
        errorMessage = 'Unable to reach the server. Please check your connection and try again.';
      } else if (errorMessage.includes('timeout') || errorMessage.includes('Timeout')) {
        errorMessage = 'The request timed out. The server may be under heavy load — please try again in a few minutes.';
      }

      toast({
        title: 'Dataset generation failed',
        description: errorMessage,
        variant: 'destructive',
      });
      setIsGenerating(false);
    }
  };

  // Handle legacy code generation
  const handleLegacyGenerate = async () => {
    const code = codeInputMode === 'direct' ? directCodeInput : currentLegacyCode;
    const validation = validateLegacyCode(code);

    if (!validation.valid) {
      toast({
        title: 'Invalid legacy code',
        description: validation.errors.join(', '),
        variant: 'destructive',
      });
      return;
    }

    setIsGenerating(true);
    setGenerationProgress(0);

    try {
      // Call the legacy endpoint via apiClient (includes auth token)
      const { data: result } = await apiClient.post('/datasets/legacy', {
        legacy_code: code,
        object_type: legacyConfig.objectType,
        target_percentage: legacyConfig.targetPercentage,
        orbital_regime: legacyConfig.orbitalRegime,
        event: legacyConfig.event,
        sensor_type: legacyConfig.sensorType,
        orbit_coverage: legacyConfig.orbitCoverage,
        track_gap: legacyConfig.trackGap,
        observation_count: legacyConfig.observationCount,
        object_count_level: legacyConfig.objectCount,
        fitspan_days: legacyConfig.fitspanDays,
      });

      if (result?.job_id) {
        setJobId(result.job_id);
      } else {
        setTimeout(() => {
          setIsGenerating(false);
          navigate('/datasets/my-datasets');
        }, 1000);
      }
    } catch (error: unknown) {
      console.error('Failed to generate dataset from legacy code:', error);
      const axiosErr = error as { response?: { data?: { detail?: string } }; message?: string };
      const detail = axiosErr?.response?.data?.detail;
      const message = typeof detail === 'string' ? detail : (error instanceof Error ? error.message : 'An unexpected error occurred');
      toast({
        title: 'Dataset generation failed',
        description: message,
        variant: 'destructive',
      });
      setIsGenerating(false);
    }
  };

  // Get current steps based on mode
  const activeSteps = mode === 'legacy' ? legacySteps : steps;
  const activeStep = mode === 'legacy' ? legacyStep : currentStep;
  return (
    <TooltipProvider>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Generate Dataset</h1>
          <p className="text-muted-foreground mt-1">
            Configure parameters to generate a custom benchmark dataset
          </p>
          <DataSourceStatusIndicator selectedPreset={null} />
          {hasUdlToken === false && (
            <div className="mt-4 rounded-lg border border-destructive/50 bg-destructive/10 p-4 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
              <div>
                <p className="font-medium text-destructive">UDL API Token Required</p>
                <p className="text-sm text-muted-foreground mt-1">
                  You need a UDL API token to generate datasets. Generation is disabled until a token is configured.
                </p>
                <Button variant="link" className="h-auto p-0 mt-1 text-primary" onClick={() => navigate('/settings')}>
                  Go to Settings &rarr;
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Mode Tabs */}
        <Tabs value={mode} onValueChange={(v) => setMode(v as 'standard' | 'legacy')}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="standard">Standard Wizard</TabsTrigger>
            <TabsTrigger value="legacy">Legacy Code (16-char)</TabsTrigger>
          </TabsList>
        </Tabs>

        {/* Live Code Preview for Legacy Mode */}
        {mode === 'legacy' && (
          <Card className="bg-muted/50">
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-sm text-muted-foreground">Current Dataset Code</Label>
                  <div className="font-mono text-2xl tracking-wider mt-1">
                    {codeInputMode === 'direct' ? (
                      <Input
                        value={directCodeInput}
                        onChange={(e) => handleDirectCodeInput(e.target.value)}
                        placeholder="H50LEONEOPSSSS07"
                        className="font-mono text-xl tracking-wider w-48"
                        maxLength={16}
                      />
                    ) : (
                      <span className="text-primary">{currentLegacyCode}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant={codeInputMode === 'wizard' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setCodeInputMode('wizard')}
                  >
                    Use Wizard
                  </Button>
                  <Button
                    variant={codeInputMode === 'direct' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setCodeInputMode('direct')}
                  >
                    Enter Code
                  </Button>
                </div>
              </div>
              {!legacyCodeValidation.valid && codeInputMode === 'direct' && directCodeInput.length > 0 && (
                <div className="mt-2 text-sm text-destructive">
                  {legacyCodeValidation.errors[0]}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Progress Steps */}
        <div className="flex items-center justify-between mb-8 overflow-x-auto">
          {activeSteps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div
                className={cn(
                  'flex items-center gap-2 px-3 py-2 rounded-full transition-colors',
                  activeStep === step.id
                    ? 'bg-primary text-primary-foreground'
                    : activeStep > step.id
                    ? 'bg-primary/20 text-primary'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {activeStep > step.id ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <step.icon className="h-4 w-4" />
                )}
                <span className="font-medium text-xs hidden sm:inline">{step.name}</span>
              </div>
              {index < activeSteps.length - 1 && (
                <div
                  className={cn(
                    'h-0.5 w-4 sm:w-8 mx-1',
                    activeStep > step.id ? 'bg-primary' : 'bg-muted'
                  )}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step Content */}
        <Card className={cn(hasUdlToken === false && 'relative')}>
          {hasUdlToken === false && (
            <div className="absolute inset-0 z-10 bg-background/60 backdrop-blur-[1px] rounded-lg flex items-center justify-center">
              <div className="text-center p-6">
                <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-2" />
                <p className="font-medium text-destructive">UDL API Token Required</p>
                <Button variant="outline" size="sm" className="mt-2" onClick={() => navigate('/settings')}>
                  Go to Settings
                </Button>
              </div>
            </div>
          )}
          {/* ============ LEGACY MODE STEPS ============ */}
          {mode === 'legacy' && codeInputMode === 'wizard' && (
            <>
              {/* Legacy Step 1: Object Type */}
              {legacyStep === 1 && (
                <>
                  <CardHeader>
                    <CardTitle>Select Object Type</CardTitle>
                    <CardDescription>
                      Choose the type of objects to include in the dataset
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <RadioGroup
                      value={legacyConfig.objectType}
                      onValueChange={(v) => updateLegacyConfig('objectType', v as LegacyObjectType)}
                      className="grid gap-3"
                    >
                      {(Object.entries(LEGACY_OBJECT_TYPES) as [LegacyObjectType, string][]).map(([value, label]) => (
                        <Label
                          key={value}
                          className={cn(
                            'flex items-center gap-4 rounded-lg border p-4 cursor-pointer transition-all hover:bg-accent',
                            legacyConfig.objectType === value && 'border-primary bg-primary/5'
                          )}
                        >
                          <RadioGroupItem value={value} />
                          <span>{label}</span>
                        </Label>
                      ))}
                    </RadioGroup>
                    <Separator />
                    <div className="space-y-3">
                      <Label>Target Percentage</Label>
                      <RadioGroup
                        value={legacyConfig.targetPercentage}
                        onValueChange={(v) => updateLegacyConfig('targetPercentage', v as TargetPercentage)}
                        className="grid grid-cols-2 sm:grid-cols-4 gap-2"
                      >
                        {(Object.entries(TARGET_PERCENTAGES) as [TargetPercentage, string][]).map(([value, _label]) => (
                          <Label
                            key={value}
                            className={cn(
                              'flex items-center gap-2 rounded-lg border p-3 cursor-pointer hover:bg-accent text-sm',
                              legacyConfig.targetPercentage === value && 'border-primary bg-primary/5'
                            )}
                          >
                            <RadioGroupItem value={value} />
                            <span className="font-mono">{value}</span>
                          </Label>
                        ))}
                      </RadioGroup>
                    </div>
                  </CardContent>
                </>
              )}

              {/* Legacy Step 2: Orbital Regime */}
              {legacyStep === 2 && (
                <>
                  <CardHeader>
                    <CardTitle>Select Orbital Regime</CardTitle>
                    <CardDescription>
                      Choose the orbital regime for the dataset
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <RadioGroup
                      value={legacyConfig.orbitalRegime}
                      onValueChange={(v) => updateLegacyConfig('orbitalRegime', v as OrbitalRegime)}
                      className="grid grid-cols-2 gap-4"
                    >
                      {[
                        { value: 'LEO', label: 'Low Earth Orbit', desc: 'a ≤ 8378 km (alt < 2000 km)' },
                        { value: 'MEO', label: 'Medium Earth Orbit', desc: '8378 < a < 42164 km' },
                        { value: 'GEO', label: 'Geosynchronous Orbit', desc: 'a ≥ 42164 km' },
                        { value: 'HEO', label: 'Highly Elliptical Orbit', desc: 'Eccentricity ≥ 0.7' },
                        { value: 'ALL', label: 'All Regimes', desc: 'LEO + MEO + GEO + HEO' },
                        // 2-regime combos
                        { value: 'LMO', label: 'LEO + MEO', desc: 'Combined low/medium orbits' },
                        { value: 'LGO', label: 'LEO + GEO', desc: 'Low + geostationary' },
                        { value: 'LHO', label: 'LEO + HEO', desc: 'Low + highly elliptical' },
                        { value: 'MGO', label: 'MEO + GEO', desc: 'Medium + geostationary' },
                        { value: 'MHO', label: 'MEO + HEO', desc: 'Medium + highly elliptical' },
                        { value: 'GHO', label: 'GEO + HEO', desc: 'Geostationary + highly elliptical' },
                        // 3-regime combos
                        { value: 'LMG', label: 'LEO + MEO + GEO', desc: 'All except HEO' },
                        { value: 'LMH', label: 'LEO + MEO + HEO', desc: 'All except GEO' },
                        { value: 'LGH', label: 'LEO + GEO + HEO', desc: 'All except MEO' },
                        { value: 'MGH', label: 'MEO + GEO + HEO', desc: 'All except LEO' },
                      ].map((regime) => (
                        <Label
                          key={regime.value}
                          className={cn(
                            'flex items-start gap-4 rounded-lg border p-4 cursor-pointer hover:bg-accent',
                            legacyConfig.orbitalRegime === regime.value && 'border-primary bg-primary/5'
                          )}
                        >
                          <RadioGroupItem value={regime.value} />
                          <div>
                            <span className="font-medium">{regime.label}</span>
                            <p className="text-sm text-muted-foreground">{regime.desc}</p>
                          </div>
                        </Label>
                      ))}
                    </RadioGroup>
                  </CardContent>
                </>
              )}

              {/* Legacy Step 3: Event Type */}
              {legacyStep === 3 && (
                <>
                  <CardHeader>
                    <CardTitle>Select Event Type</CardTitle>
                    <CardDescription>
                      Choose whether to include specific events in the dataset
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <RadioGroup
                      value={legacyConfig.event}
                      onValueChange={(v) => updateLegacyConfig('event', v as LegacyEventType)}
                      className="grid gap-3"
                    >
                      {(Object.entries(LEGACY_EVENT_TYPES) as [LegacyEventType, string][]).map(([value, label]) => (
                        <Label
                          key={value}
                          className={cn(
                            'flex items-center gap-4 rounded-lg border p-4 cursor-pointer hover:bg-accent',
                            legacyConfig.event === value && 'border-primary bg-primary/5'
                          )}
                        >
                          <RadioGroupItem value={value} />
                          <div>
                            <span className="font-mono text-lg mr-2">{value}</span>
                            <span>{label}</span>
                          </div>
                        </Label>
                      ))}
                    </RadioGroup>
                    {(legacyConfig.event && legacyConfig.event !== 'NE') && (
                      <p className="text-sm text-amber-500 flex items-center gap-1.5 mt-2">
                        <AlertCircle className="h-4 w-4 shrink-0" />
                        Event detection is not yet integrated into the pipeline. Selecting an event type records the intent but does not filter data by events.
                      </p>
                    )}
                  </CardContent>
                </>
              )}

              {/* Legacy Step 4: Sensor Type */}
              {legacyStep === 4 && (
                <>
                  <CardHeader>
                    <CardTitle>Select Sensor Type</CardTitle>
                    <CardDescription>
                      Choose the sensor types to include in observations
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <RadioGroup
                      value={legacyConfig.sensorType}
                      onValueChange={(v) => updateLegacyConfig('sensorType', v as LegacySensorType)}
                      className="grid gap-3"
                    >
                      {(Object.entries(LEGACY_SENSOR_TYPES) as [LegacySensorType, string][]).map(([value, label]) => (
                        <Label
                          key={value}
                          className={cn(
                            'flex items-center gap-4 rounded-lg border p-4 cursor-pointer hover:bg-accent',
                            legacyConfig.sensorType === value && 'border-primary bg-primary/5'
                          )}
                        >
                          <RadioGroupItem value={value} />
                          <span>{label}</span>
                        </Label>
                      ))}
                    </RadioGroup>
                    {(legacyConfig.sensorType && legacyConfig.sensorType !== 'OP') && (
                      <p className="text-sm text-amber-500 flex items-center gap-1.5 mt-2">
                        <AlertCircle className="h-4 w-4 shrink-0" />
                        Only optical (EO) data is currently available from UDL. Non-optical sensor types will still generate optical observations.
                      </p>
                    )}
                  </CardContent>
                </>
              )}

              {/* Legacy Step 5: Quality Metrics (A/S/N for coverage, gap, obs count) */}
              {legacyStep === 5 && (
                <>
                  <CardHeader>
                    <CardTitle>Quality Metrics</CardTitle>
                    <CardDescription>
                      Set quality levels for coverage, track gaps, and observation count
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-8">
                    {/* Orbit Coverage */}
                    <div className="space-y-3">
                      <Label className="text-base font-medium">Orbit Coverage Level</Label>
                      <RadioGroup
                        value={legacyConfig.orbitCoverage}
                        onValueChange={(v) => updateLegacyConfig('orbitCoverage', v as QualityLevel)}
                        className="grid grid-cols-3 gap-2"
                      >
                        {(Object.entries(QUALITY_LEVELS) as [QualityLevel, string][]).map(([value, label]) => (
                          <Label
                            key={value}
                            className={cn(
                              'flex flex-col items-center gap-1 rounded-lg border p-4 cursor-pointer hover:bg-accent',
                              legacyConfig.orbitCoverage === value && 'border-primary bg-primary/5'
                            )}
                          >
                            <RadioGroupItem value={value} />
                            <span className="font-mono text-xl">{value}</span>
                            <span className="text-xs text-muted-foreground">{label}</span>
                          </Label>
                        ))}
                      </RadioGroup>
                    </div>

                    <Separator />

                    {/* Track Gap */}
                    <div className="space-y-3">
                      <Label className="text-base font-medium">Track Gap Level</Label>
                      <RadioGroup
                        value={legacyConfig.trackGap}
                        onValueChange={(v) => updateLegacyConfig('trackGap', v as QualityLevel)}
                        className="grid grid-cols-3 gap-2"
                      >
                        {(Object.entries(QUALITY_LEVELS) as [QualityLevel, string][]).map(([value, label]) => (
                          <Label
                            key={value}
                            className={cn(
                              'flex flex-col items-center gap-1 rounded-lg border p-4 cursor-pointer hover:bg-accent',
                              legacyConfig.trackGap === value && 'border-primary bg-primary/5'
                            )}
                          >
                            <RadioGroupItem value={value} />
                            <span className="font-mono text-xl">{value}</span>
                            <span className="text-xs text-muted-foreground">{label}</span>
                          </Label>
                        ))}
                      </RadioGroup>
                    </div>

                    <Separator />

                    {/* Observation Count */}
                    <div className="space-y-3">
                      <Label className="text-base font-medium">Observation Count Level</Label>
                      <RadioGroup
                        value={legacyConfig.observationCount}
                        onValueChange={(v) => updateLegacyConfig('observationCount', v as QualityLevel)}
                        className="grid grid-cols-3 gap-2"
                      >
                        {(Object.entries(QUALITY_LEVELS) as [QualityLevel, string][]).map(([value, label]) => (
                          <Label
                            key={value}
                            className={cn(
                              'flex flex-col items-center gap-1 rounded-lg border p-4 cursor-pointer hover:bg-accent',
                              legacyConfig.observationCount === value && 'border-primary bg-primary/5'
                            )}
                          >
                            <RadioGroupItem value={value} />
                            <span className="font-mono text-xl">{value}</span>
                            <span className="text-xs text-muted-foreground">{label}</span>
                          </Label>
                        ))}
                      </RadioGroup>
                    </div>
                  </CardContent>
                </>
              )}

              {/* Legacy Step 6: Object Count & Fitspan */}
              {legacyStep === 6 && (
                <>
                  <CardHeader>
                    <CardTitle>Object Count & Fitspan</CardTitle>
                    <CardDescription>
                      Set the number of objects and observation window duration
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-8">
                    {/* Object Count */}
                    <div className="space-y-3">
                      <Label className="text-base font-medium">Object Count</Label>
                      <RadioGroup
                        value={legacyConfig.objectCount}
                        onValueChange={(v) => updateLegacyConfig('objectCount', v as ObjectCountLevel)}
                        className="grid grid-cols-3 gap-4"
                      >
                        {(Object.entries(OBJECT_COUNT_LEVELS) as [ObjectCountLevel, { label: string; count: number; tolerance: number }][]).map(
                          ([value, { label, count, tolerance }]) => (
                            <Label
                              key={value}
                              className={cn(
                                'flex flex-col items-center gap-2 rounded-lg border p-4 cursor-pointer hover:bg-accent',
                                legacyConfig.objectCount === value && 'border-primary bg-primary/5'
                              )}
                            >
                              <RadioGroupItem value={value} />
                              <span className="font-mono text-2xl">{value}</span>
                              <span className="text-sm">{label}</span>
                              <span className="text-muted-foreground">{count} &plusmn; {tolerance} objects</span>
                            </Label>
                          )
                        )}
                      </RadioGroup>
                    </div>

                    <Separator />

                    {/* Fitspan Days */}
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <Label className="text-base font-medium">Fitspan (Days)</Label>
                        <span className="font-mono text-lg bg-muted px-3 py-1 rounded">
                          {legacyConfig.fitspanDays.toString().padStart(2, '0')}
                        </span>
                      </div>
                      <Slider
                        value={[legacyConfig.fitspanDays]}
                        onValueChange={([v]) => updateLegacyConfig('fitspanDays', v)}
                        min={1}
                        max={14}
                        step={1}
                        className="py-4"
                      />
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>1 day</span>
                        <span>7 days</span>
                        <span>14 days</span>
                      </div>
                    </div>
                  </CardContent>
                </>
              )}

              {/* Legacy Step 7: Review */}
              {legacyStep === 7 && (
                <>
                  <CardHeader>
                    <CardTitle>Review Configuration</CardTitle>
                    <CardDescription>
                      Verify your dataset code before generation
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {isGenerating ? (
                      <div className="space-y-4 py-8">
                        <div className="flex items-center justify-center gap-3">
                          <Loader2 className="h-6 w-6 animate-spin text-primary" />
                          <span className="text-lg font-medium">Generating dataset...</span>
                        </div>
                        <Progress value={generationProgress} className="w-full" />
                        <p className="text-center text-sm text-muted-foreground">
                          {jobStatus?.stage || 'Initializing...'}
                        </p>
                      </div>
                    ) : (
                      <>
                        {/* Code Display */}
                        <div className="text-center py-6 bg-muted/50 rounded-lg">
                          <p className="text-sm text-muted-foreground mb-2">Your Dataset Code</p>
                          <p className="font-mono text-4xl tracking-widest text-primary">{currentLegacyCode}</p>
                        </div>

                        {/* Code Breakdown */}
                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                          <div className="rounded-lg border p-3 text-center">
                            <p className="font-mono text-lg">{legacyConfig.objectType}</p>
                            <p className="text-xs text-muted-foreground">Object Type</p>
                          </div>
                          <div className="rounded-lg border p-3 text-center">
                            <p className="font-mono text-lg">{legacyConfig.targetPercentage}</p>
                            <p className="text-xs text-muted-foreground">Target %</p>
                          </div>
                          <div className="rounded-lg border p-3 text-center">
                            <p className="font-mono text-lg">{legacyConfig.orbitalRegime}</p>
                            <p className="text-xs text-muted-foreground">Regime</p>
                          </div>
                          <div className="rounded-lg border p-3 text-center">
                            <p className="font-mono text-lg">{legacyConfig.event}</p>
                            <p className="text-xs text-muted-foreground">Event</p>
                          </div>
                          <div className="rounded-lg border p-3 text-center">
                            <p className="font-mono text-lg">{legacyConfig.sensorType}</p>
                            <p className="text-xs text-muted-foreground">Sensor</p>
                          </div>
                          <div className="rounded-lg border p-3 text-center">
                            <p className="font-mono text-lg">{legacyConfig.orbitCoverage}</p>
                            <p className="text-xs text-muted-foreground">Coverage</p>
                          </div>
                          <div className="rounded-lg border p-3 text-center">
                            <p className="font-mono text-lg">{legacyConfig.trackGap}</p>
                            <p className="text-xs text-muted-foreground">Track Gap</p>
                          </div>
                          <div className="rounded-lg border p-3 text-center">
                            <p className="font-mono text-lg">{legacyConfig.observationCount}</p>
                            <p className="text-xs text-muted-foreground">Obs Count</p>
                          </div>
                          <div className="rounded-lg border p-3 text-center">
                            <p className="font-mono text-lg">{legacyConfig.objectCount}</p>
                            <p className="text-xs text-muted-foreground">Obj Count</p>
                          </div>
                          <div className="rounded-lg border p-3 text-center">
                            <p className="font-mono text-lg">{legacyConfig.fitspanDays.toString().padStart(2, '0')}</p>
                            <p className="text-xs text-muted-foreground">Fitspan</p>
                          </div>
                        </div>

                        {/* Summary */}
                        <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                          <h4 className="font-medium">Summary</h4>
                          <ul className="text-sm space-y-1 text-muted-foreground">
                            <li>Object Type: {LEGACY_OBJECT_TYPES[legacyConfig.objectType]}</li>
                            <li>Regime: {legacyConfig.orbitalRegime}</li>
                            <li>Event: {LEGACY_EVENT_TYPES[legacyConfig.event]}</li>
                            <li>Sensor: {LEGACY_SENSOR_TYPES[legacyConfig.sensorType]}</li>
                            <li>Objects: {OBJECT_COUNT_LEVELS[legacyConfig.objectCount].count}</li>
                            <li>Duration: {legacyConfig.fitspanDays} days</li>
                          </ul>
                        </div>
                      </>
                    )}
                  </CardContent>
                </>
              )}
            </>
          )}

          {/* Legacy Mode - Direct Code Input Review */}
          {mode === 'legacy' && codeInputMode === 'direct' && (
            <>
              <CardHeader>
                <CardTitle>Direct Code Entry</CardTitle>
                <CardDescription>
                  Enter a 16-character dataset code directly
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {isGenerating ? (
                  <div className="space-y-4 py-8">
                    <div className="flex items-center justify-center gap-3">
                      <Loader2 className="h-6 w-6 animate-spin text-primary" />
                      <span className="text-lg font-medium">Generating dataset...</span>
                    </div>
                    <Progress value={generationProgress} className="w-full" />
                  </div>
                ) : (
                  <>
                    <div className="text-center py-6">
                      <Input
                        value={directCodeInput}
                        onChange={(e) => handleDirectCodeInput(e.target.value)}
                        placeholder="H50LEONEOPSSSS07"
                        className={cn(
                          'font-mono text-3xl tracking-widest text-center max-w-xs mx-auto h-14',
                          legacyCodeValidation.valid ? 'border-green-500' : directCodeInput.length > 0 ? 'border-destructive' : ''
                        )}
                        maxLength={16}
                      />
                      <p className="text-sm text-muted-foreground mt-2">
                        {directCodeInput.length}/16 characters
                      </p>
                    </div>

                    {legacyCodeValidation.valid && directCodeInput.length === 16 && (
                      <div className="bg-green-50 dark:bg-green-950 rounded-lg p-4">
                        <p className="text-green-700 dark:text-green-300 font-medium">Valid code!</p>
                        <ul className="text-sm mt-2 space-y-1 text-green-600 dark:text-green-400">
                          <li>Object Type: {LEGACY_OBJECT_TYPES[legacyConfig.objectType]}</li>
                          <li>Regime: {legacyConfig.orbitalRegime}</li>
                          <li>Event: {LEGACY_EVENT_TYPES[legacyConfig.event]}</li>
                          <li>Sensor: {LEGACY_SENSOR_TYPES[legacyConfig.sensorType]}</li>
                        </ul>
                      </div>
                    )}

                    {!legacyCodeValidation.valid && directCodeInput.length > 0 && (
                      <div className="bg-destructive/10 rounded-lg p-4">
                        <p className="text-destructive font-medium">Invalid code</p>
                        <ul className="text-sm mt-2 space-y-1 text-destructive">
                          {legacyCodeValidation.errors.map((err, i) => (
                            <li key={i}>{err}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </>
          )}

          {/* ============ STANDARD MODE STEPS ============ */}
          {/* Step 1: Regime Selection */}
          {mode === 'standard' && currentStep === 1 && (
            <>
              <CardHeader>
                <CardTitle>Select Orbital Regime</CardTitle>
                <CardDescription>
                  Choose the orbital regime for your benchmark dataset
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <RadioGroup
                  value={config.regime}
                  onValueChange={(value) => updateConfig('regime', value as OrbitalRegime)}
                  className="grid grid-cols-2 gap-4"
                >
                  {[
                    { value: 'LEO', label: 'Low Earth Orbit', desc: 'a ≤ 8378 km (alt < 2000 km)', color: 'bg-orbital-leo' },
                    { value: 'MEO', label: 'Medium Earth Orbit', desc: '8378 < a < 42164 km', color: 'bg-orbital-meo' },
                    { value: 'GEO', label: 'Geosynchronous Orbit', desc: 'a ≥ 42164 km', color: 'bg-orbital-geo' },
                    { value: 'HEO', label: 'Highly Elliptical Orbit', desc: 'Eccentricity ≥ 0.7', color: 'bg-orbital-heo' },
                    { value: 'ALL', label: 'All Regimes', desc: 'LEO + MEO + GEO + HEO', color: 'bg-gray-400' },
                    // 2-regime combos
                    { value: 'LMO', label: 'LEO + MEO', desc: 'Combined low/medium orbits', color: 'bg-orbital-leo' },
                    { value: 'LGO', label: 'LEO + GEO', desc: 'Low + geostationary', color: 'bg-orbital-leo' },
                    { value: 'LHO', label: 'LEO + HEO', desc: 'Low + highly elliptical', color: 'bg-orbital-leo' },
                    { value: 'MGO', label: 'MEO + GEO', desc: 'Medium + geostationary', color: 'bg-orbital-meo' },
                    { value: 'MHO', label: 'MEO + HEO', desc: 'Medium + highly elliptical', color: 'bg-orbital-meo' },
                    { value: 'GHO', label: 'GEO + HEO', desc: 'Geostationary + highly elliptical', color: 'bg-orbital-geo' },
                    // 3-regime combos
                    { value: 'LMG', label: 'LEO + MEO + GEO', desc: 'All except HEO', color: 'bg-orbital-meo' },
                    { value: 'LMH', label: 'LEO + MEO + HEO', desc: 'All except GEO', color: 'bg-orbital-meo' },
                    { value: 'LGH', label: 'LEO + GEO + HEO', desc: 'All except MEO', color: 'bg-orbital-geo' },
                    { value: 'MGH', label: 'MEO + GEO + HEO', desc: 'All except LEO', color: 'bg-orbital-geo' },
                  ].map((regime) => (
                    <Label
                      key={regime.value}
                      htmlFor={regime.value}
                      className={cn(
                        'flex items-start gap-4 rounded-lg border p-4 cursor-pointer transition-all hover:bg-accent',
                        config.regime === regime.value && 'border-primary bg-primary/5'
                      )}
                    >
                      <RadioGroupItem value={regime.value} id={regime.value} className="mt-1" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <div className={cn('w-3 h-3 rounded-full', regime.color)} />
                          <span className="font-medium">{regime.label}</span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">{regime.desc}</p>
                      </div>
                    </Label>
                  ))}
                </RadioGroup>

                <Separator />

                {/* Target Object Percentage (Positions 2-3) */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Target Object Percentage</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-4 w-4 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p>Percentage of objects designated as targets for detection. Maps to positions 2-3 of the 16-character dataset code.</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <RadioGroup
                    value={config.targetPercentage ?? 'UN'}
                    onValueChange={(v) => updateConfig('targetPercentage', v as TargetPercentage)}
                    className="grid grid-cols-2 sm:grid-cols-4 gap-2"
                  >
                    {([
                      { value: '50', label: '50%' },
                      { value: '10', label: '10%' },
                      { value: '01', label: '1%' },
                      { value: 'UN', label: 'Unspecified' },
                    ] as const).map((opt) => (
                      <Label
                        key={opt.value}
                        htmlFor={`target-pct-${opt.value}`}
                        className={cn(
                          'flex items-center gap-2 rounded-lg border p-3 cursor-pointer transition-all hover:bg-accent text-sm',
                          (config.targetPercentage ?? 'UN') === opt.value && 'border-primary bg-primary/5'
                        )}
                      >
                        <RadioGroupItem value={opt.value} id={`target-pct-${opt.value}`} />
                        <span>{opt.label}</span>
                      </Label>
                    ))}
                  </RadioGroup>
                </div>
              </CardContent>
            </>
          )}

          {/* Step 2: Quality Parameters */}
          {mode === 'standard' && currentStep === 2 && (
            <>
              <CardHeader>
                <CardTitle>Data Quality Parameters</CardTitle>
                <CardDescription>
                  Configure observation coverage, density, and gap characteristics
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                {/* Coverage */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Orbital Coverage</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-4 w-4 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p>Percentage of the orbital arc covered by observations. Thresholds are regime-specific (e.g., GEO has higher visibility than LEO). Lower coverage simulates sparse observation scenarios.</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <RadioGroup
                    value={config.coverage}
                    onValueChange={(value) => updateConfig('coverage', value as typeof config.coverage)}
                    className="grid grid-cols-2 sm:grid-cols-4 gap-2"
                  >
                    {getCoverageOptions(config.regime, coverageThresholds).map((opt) => (
                      <Label
                        key={opt.value}
                        htmlFor={`coverage-${opt.value}`}
                        className={cn(
                          'flex items-center gap-2 rounded-lg border p-3 cursor-pointer transition-all hover:bg-accent text-sm',
                          config.coverage === opt.value && 'border-primary bg-primary/5'
                        )}
                      >
                        <RadioGroupItem value={opt.value} id={`coverage-${opt.value}`} />
                        {opt.label}
                      </Label>
                    ))}
                  </RadioGroup>
                  <p className="text-sm text-muted-foreground">
                    Selected: {config.coverage.charAt(0).toUpperCase() + config.coverage.slice(1)} coverage simulates {config.coverage === 'low' ? 'sparse observation scenarios where algorithms must work with incomplete data' : config.coverage === 'high' ? 'well-observed conditions' : 'typical operational conditions'}.
                  </p>
                </div>

                <Separator />

                {/* Observation Density */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Label className="text-base font-medium">Observation Density</Label>
                      <Tooltip>
                        <TooltipTrigger>
                          <Info className="h-4 w-4 text-muted-foreground" />
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                          <p>Target number of observations per satellite over a 3-day period.</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
                      {config.observationDensity} obs/sat/3-days
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

                <Separator />

                {/* Track Gap Target */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Track Gap Target</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-4 w-4 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p>Maximum gap between observation tracks, measured in orbital periods.</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map((gap) => (
                      <Button
                        key={gap}
                        variant={config.trackGapTarget === gap ? 'default' : 'outline'}
                        className="flex-1"
                        onClick={() => updateConfig('trackGapTarget', gap)}
                      >
                        {gap}{gap === 5 ? '+' : ''}
                      </Button>
                    ))}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {config.trackGapTarget} orbital period{config.trackGapTarget > 1 ? 's' : ''} selected
                  </p>
                </div>

                <Separator />

                {/* Sensor Type (Positions 9-10) */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Sensor Type</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-4 w-4 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p>Type of sensor observations in the dataset. Maps to positions 9-10 of the 16-character dataset code.</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <RadioGroup
                    value={config.sensorTypeCode ?? 'OP'}
                    onValueChange={(v) => updateConfig('sensorTypeCode', v as LegacySensorType)}
                    className="grid grid-cols-2 sm:grid-cols-3 gap-2"
                  >
                    {([
                      { value: 'OP', label: 'Optical' },
                      { value: 'RA', label: 'Radar' },
                      { value: 'RF', label: 'RF' },
                      { value: 'FU', label: 'Fusion (All)' },
                      { value: 'OR', label: 'Optical + Radar' },
                      { value: 'RR', label: 'Radar + RF' },
                    ] as const).map((opt) => (
                      <Label
                        key={opt.value}
                        htmlFor={`sensor-type-${opt.value}`}
                        className={cn(
                          'flex items-center gap-2 rounded-lg border p-3 cursor-pointer transition-all hover:bg-accent text-sm',
                          (config.sensorTypeCode ?? 'OP') === opt.value && 'border-primary bg-primary/5'
                        )}
                      >
                        <RadioGroupItem value={opt.value} id={`sensor-type-${opt.value}`} />
                        <span>{opt.label}</span>
                      </Label>
                    ))}
                  </RadioGroup>
                  {(config.sensorTypeCode && config.sensorTypeCode !== 'OP') && (
                    <p className="text-sm text-amber-500 flex items-center gap-1.5 mt-2">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      Only optical (EO) data is currently available from UDL. Non-optical sensor types will still generate optical observations.
                    </p>
                  )}
                </div>

                <Separator />

                {/* Event Type (Positions 7-8) */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Event Type</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-4 w-4 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p>Whether to include specific orbital events in the dataset. Maps to positions 7-8 of the 16-character dataset code.</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <RadioGroup
                    value={config.eventCode ?? 'NE'}
                    onValueChange={(v) => updateConfig('eventCode', v as LegacyEventType)}
                    className="grid grid-cols-2 gap-2"
                  >
                    {([
                      { value: 'NE', label: 'No Events (Normal)' },
                      { value: 'MB', label: 'Maneuver Between' },
                      { value: 'BU', label: 'Breakup Event' },
                      { value: 'LL', label: 'Long-thrust Low-thrust' },
                    ] as const).map((opt) => (
                      <Label
                        key={opt.value}
                        htmlFor={`event-type-${opt.value}`}
                        className={cn(
                          'flex items-center gap-2 rounded-lg border p-3 cursor-pointer transition-all hover:bg-accent text-sm',
                          (config.eventCode ?? 'NE') === opt.value && 'border-primary bg-primary/5'
                        )}
                      >
                        <RadioGroupItem value={opt.value} id={`event-type-${opt.value}`} />
                        <div>
                          <span className="font-mono mr-1">{opt.value}</span>
                          <span>{opt.label}</span>
                        </div>
                      </Label>
                    ))}
                  </RadioGroup>
                  {(config.eventCode && config.eventCode !== 'NE') && (
                    <p className="text-sm text-amber-500 flex items-center gap-1.5 mt-2">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      Event detection is not yet integrated into the pipeline. Selecting an event type records the intent but does not filter data by events.
                    </p>
                  )}
                </div>
              </CardContent>
            </>
          )}

          {/* Step 3: Object Selection */}
          {mode === 'standard' && currentStep === 3 && (
            <>
              <CardHeader>
                <CardTitle>Object Selection</CardTitle>
                <CardDescription>
                  Specify the number and types of objects to include
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                {/* Object Count */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label className="text-base font-medium">Number of Objects</Label>
                    <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
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

                <Separator />

                {/* Date Range */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Date Range</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-4 w-4 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p>Maximum date range is {MAX_TIMEFRAME_DAYS} days. Select start and end dates for the observation window.</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="startDate">Start Date</Label>
                      <Input
                        id="startDate"
                        type="date"
                        value={config.startDate}
                        max={config.endDate}
                        onChange={(e) => updateConfig('startDate', e.target.value)}
                        className={timeframeError ? 'border-destructive' : ''}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="endDate">End Date</Label>
                      <Input
                        id="endDate"
                        type="date"
                        value={config.endDate}
                        max={new Date().toISOString().split('T')[0]}
                        onChange={(e) => updateConfig('endDate', e.target.value)}
                        className={timeframeError ? 'border-destructive' : ''}
                      />
                    </div>
                  </div>
                  {timeframeError ? (
                    <div className="flex items-center gap-2 text-destructive text-sm">
                      <AlertCircle className="h-4 w-4" />
                      {timeframeError}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Selected: {calculatedTimeframe} day{calculatedTimeframe !== 1 ? 's' : ''} (max {MAX_TIMEFRAME_DAYS})
                    </p>
                  )}
                </div>

                <Separator />

                {/* Object Type (Position 1) */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Object Type</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-4 w-4 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p>Type of objects to include in the dataset. Maps to position 1 of the 16-character dataset code.</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <Select
                    value={config.objectTypeCode ?? 'U'}
                    onValueChange={(value) => updateConfig('objectTypeCode', value as 'H' | 'C' | 'A' | 'U' | 'N')}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select object type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="U">Unspecified (All objects)</SelectItem>
                      <SelectItem value="H">HAMR (High Area-to-Mass Ratio)</SelectItem>
                      <SelectItem value="C">Close (Physical proximity)</SelectItem>
                      <SelectItem value="A">Apparent (Angular proximity)</SelectItem>
                      <SelectItem value="N">Calibration satellites</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Separator />

                {/* HAMR Toggle */}
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label className="text-base font-medium">Include HAMR Objects</Label>
                    <p className="text-sm text-muted-foreground">
                      High Area-to-Mass Ratio objects (tumbling debris, rocket bodies)
                    </p>
                  </div>
                  <Switch
                    checked={config.includeHamr}
                    onCheckedChange={(checked) => updateConfig('includeHamr', checked)}
                  />
                </div>

                <Separator />

                {/* Fitspan Days (Positions 15-16) */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Observation Window (Fitspan)</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-4 w-4 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p>Duration of the observation window in days. Maps to positions 15-16 of the 16-character dataset code.</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Fitspan duration</span>
                    <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
                      {config.fitspanDays ?? 7} days
                    </span>
                  </div>
                  <Slider
                    value={[config.fitspanDays ?? 7]}
                    onValueChange={([v]) => updateConfig('fitspanDays', v)}
                    min={1}
                    max={14}
                    step={1}
                    className="py-4"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>1 day</span>
                    <span>7 days</span>
                    <span>14 days</span>
                  </div>
                </div>
              </CardContent>
            </>
          )}

          {/* Step 4: Advanced (Downsampling & Simulation) */}
          {mode === 'standard' && currentStep === 4 && (
            <>
              <CardHeader>
                <CardTitle>Advanced Options</CardTitle>
                <CardDescription>
                  Configure data fetching strategy, downsampling, and simulation settings
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                {/* Search Strategy Section */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Data Fetching Strategy</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-4 w-4 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p>Choose how observation data is fetched from the UDL API. Different strategies balance speed vs. data completeness.</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>

                  <RadioGroup
                    value={config.searchStrategy}
                    onValueChange={(value) => updateConfig('searchStrategy', value as SearchStrategy)}
                    className="grid gap-3"
                  >
                    {/* Fast option */}
                    <Label
                      htmlFor="strategy-fast"
                      className={cn(
                        'flex items-start gap-4 rounded-lg border p-4 cursor-pointer transition-all hover:bg-accent',
                        config.searchStrategy === 'fast' && 'border-primary bg-primary/5'
                      )}
                    >
                      <RadioGroupItem value="fast" id="strategy-fast" className="mt-1" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Zap className="h-4 w-4" />
                          <span className="font-medium">Fast Search</span>
                          <Badge variant="outline">Fastest</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          Single query per satellite. May hit API limits for large time ranges.
                        </p>
                      </div>
                    </Label>

                    {/* Hybrid option */}
                    <Label
                      htmlFor="strategy-hybrid"
                      className={cn(
                        'flex items-start gap-4 rounded-lg border p-4 cursor-pointer transition-all hover:bg-accent',
                        config.searchStrategy === 'hybrid' && 'border-primary bg-primary/5'
                      )}
                    >
                      <RadioGroupItem value="hybrid" id="strategy-hybrid" className="mt-1" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Settings2 className="h-4 w-4" />
                          <span className="font-medium">Hybrid Search</span>
                          <Badge>Recommended</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          Checks data volume first, chunks if needed. Best balance of speed and completeness.
                        </p>
                      </div>
                    </Label>

                    {/* Windowed option */}
                    <Label
                      htmlFor="strategy-windowed"
                      className={cn(
                        'flex items-start gap-4 rounded-lg border p-4 cursor-pointer transition-all hover:bg-accent',
                        config.searchStrategy === 'windowed' && 'border-primary bg-primary/5'
                      )}
                    >
                      <RadioGroupItem value="windowed" id="strategy-windowed" className="mt-1" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Clock className="h-4 w-4" />
                          <span className="font-medium">Windowed Search</span>
                          <Badge variant="secondary">Reference-Compatible</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          Uses fixed time windows like reference code. Guaranteed complete but slower.
                        </p>
                      </div>
                    </Label>
                  </RadioGroup>

                  {/* Window size slider (only for windowed) */}
                  {config.searchStrategy === 'windowed' && (
                    <div className="ml-6 pl-6 border-l-2 border-muted space-y-3">
                      <div className="flex justify-between items-center">
                        <Label>Window Size</Label>
                        <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
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

                <Separator />

                {/* Downsampling Section */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Label className="text-base font-medium">Enable Downsampling</Label>
                        <Tooltip>
                          <TooltipTrigger>
                            <Info className="h-4 w-4 text-muted-foreground" />
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs">
                            <p>Reduces observation quality by removing observations while preserving track structure. Simulates sparse data scenarios.</p>
                          </TooltipContent>
                        </Tooltip>
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
                    <div className="ml-6 space-y-6 border-l-2 pl-6 border-muted">
                      {/* Target Coverage */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <Label>Target Coverage</Label>
                          <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
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
                          <Label>Target Gap (orbital periods)</Label>
                          <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
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
                          <Label>Max Observations Per Satellite</Label>
                          <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
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
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label>Preserve Track Boundaries</Label>
                          <p className="text-xs text-muted-foreground">
                            Keep first and last observations of each track
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

                <Separator />

                {/* Simulation Section */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Label className="text-base font-medium">Enable Gap-Filling Simulation</Label>
                        <Tooltip>
                          <TooltipTrigger>
                            <Info className="h-4 w-4 text-muted-foreground" />
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs">
                            <p>Generates synthetic observations to fill gaps in the observation data using physics-based propagation.</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Fill observation gaps with simulated data
                      </p>
                    </div>
                    <Switch
                      checked={config.simulation?.enabled ?? false}
                      onCheckedChange={(checked) => updateSimulation('enabled', checked)}
                    />
                  </div>

                  {config.simulation?.enabled && (
                    <div className="ml-6 space-y-6 border-l-2 pl-6 border-muted">
                      {/* Sensor Model */}
                      <div className="space-y-3">
                        <Label>Sensor Noise Model</Label>
                        <div className="grid grid-cols-3 gap-2">
                          {(['GEODSS', 'SBSS', 'Commercial_EO'] as const).map((model) => (
                            <Button
                              key={model}
                              variant={config.simulation?.sensorModel === model ? 'default' : 'outline'}
                              size="sm"
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
                          <Label>Max Synthetic Ratio</Label>
                          <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
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
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label>Apply Realistic Noise</Label>
                          <p className="text-xs text-muted-foreground">
                            Add sensor-specific noise to simulated observations
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

                <Separator />

                {/* Advanced Benchmark Options */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">Advanced Benchmark Settings</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-4 w-4 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p>Advanced options for comprehensive benchmark evaluation and dataset customization.</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>

                  {/* True Negative / Non-Reference Observations */}
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Label>Include Non-Reference Observations</Label>
                        <Badge variant="outline">True Negatives</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Add observations from satellites NOT in the reference set (for TN evaluation)
                      </p>
                    </div>
                    <Switch
                      checked={config.includeNonRefObs ?? false}
                      onCheckedChange={(checked) => updateConfig('includeNonRefObs', checked)}
                    />
                  </div>

                  {/* Window Selection Algorithm */}
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Label>Use Window Selection Algorithm</Label>
                        <Badge variant="outline">Bisecting Search</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Automatically find the optimal time window and tier classification
                      </p>
                    </div>
                    <Switch
                      checked={config.useWindowSelection ?? false}
                      onCheckedChange={(checked) => updateConfig('useWindowSelection', checked)}
                    />
                  </div>
                </div>
              </CardContent>
            </>
          )}

          {/* Step 5: Review */}
          {mode === 'standard' && currentStep === 5 && (
            <>
              <CardHeader>
                <CardTitle>Review Configuration</CardTitle>
                <CardDescription>
                  Verify your dataset configuration before generation
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {isGenerating ? (
                  <div className="space-y-4 py-8">
                    <div className="flex items-center justify-center gap-3">
                      <Loader2 className="h-6 w-6 animate-spin text-primary" />
                      <span className="text-lg font-medium">Generating dataset...</span>
                    </div>
                    <Progress value={generationProgress} className="w-full" />
                    <p className="text-center text-sm text-muted-foreground">
                      {jobStatus?.stage || 'Initializing...'}
                    </p>
                  </div>
                ) : (
                  <>
                    {/* Optional dataset name */}
                    <div className="space-y-2">
                      <Label htmlFor="dataset-name">Dataset Name (optional)</Label>
                      <Input
                        id="dataset-name"
                        placeholder={`e.g., My LEO test run — defaults to "${config.regime}-${config.coverage}"`}
                        value={customName}
                        onChange={(e) => setCustomName(e.target.value)}
                        maxLength={80}
                      />
                      <p className="text-xs text-muted-foreground">
                        A timestamp and unique ID will be appended automatically.
                      </p>
                    </div>

                    <div className="grid sm:grid-cols-2 gap-4">
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Orbital Regime</h4>
                        <div className="flex items-center gap-2">
                          <Badge variant={config.regime === 'LEO' ? 'leo' : config.regime === 'MEO' ? 'meo' : config.regime === 'GEO' ? 'geo' : 'heo'}>
                            {config.regime}
                          </Badge>
                          <span className="text-sm text-muted-foreground">
                            {config.regime === 'LEO' && 'Low Earth Orbit'}
                            {config.regime === 'MEO' && 'Medium Earth Orbit'}
                            {config.regime === 'GEO' && 'Geostationary Orbit'}
                            {config.regime === 'HEO' && 'Highly Elliptical Orbit'}
                          </span>
                        </div>
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Target %</h4>
                        <p className="text-2xl font-semibold">{TARGET_PERCENTAGES[config.targetPercentage ?? 'UN']}</p>
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Coverage</h4>
                        <p className="text-2xl font-semibold capitalize">{config.coverage}</p>
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Observation Density</h4>
                        <p className="text-2xl font-semibold">{config.observationDensity}</p>
                        <p className="text-xs text-muted-foreground">obs/satellite/3-days</p>
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Track Gap Target</h4>
                        <p className="text-2xl font-semibold">{config.trackGapTarget}</p>
                        <p className="text-xs text-muted-foreground">orbital periods</p>
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Sensor Type</h4>
                        <p className="text-lg font-semibold">{LEGACY_SENSOR_TYPES[(config.sensorTypeCode ?? 'OP') as LegacySensorType]}</p>
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Event Type</h4>
                        <p className="text-lg font-semibold">{LEGACY_EVENT_TYPES[(config.eventCode ?? 'NE') as LegacyEventType]}</p>
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Object Type</h4>
                        <p className="text-lg font-semibold">{LEGACY_OBJECT_TYPES[(config.objectTypeCode ?? 'U') as LegacyObjectType]}</p>
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Objects</h4>
                        <p className="text-2xl font-semibold">{config.objectCount}</p>
                        <p className="text-xs text-muted-foreground">
                          {config.includeHamr ? 'Including HAMR objects' : 'Standard objects only'}
                        </p>
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Fitspan</h4>
                        <p className="text-2xl font-semibold">{config.fitspanDays ?? 7}</p>
                        <p className="text-xs text-muted-foreground">days</p>
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Date Range</h4>
                        <p className="text-sm">
                          {config.startDate} to {config.endDate}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {calculatedTimeframe} day{calculatedTimeframe !== 1 ? 's' : ''}
                        </p>
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Search Strategy</h4>
                        <div className="flex items-center gap-2">
                          <Badge variant={config.searchStrategy === 'hybrid' ? 'default' : 'outline'}>
                            {config.searchStrategy === 'fast' && 'Fast'}
                            {config.searchStrategy === 'hybrid' && 'Hybrid'}
                            {config.searchStrategy === 'windowed' && 'Windowed'}
                          </Badge>
                          {config.searchStrategy === 'windowed' && (
                            <span className="text-xs text-muted-foreground">
                              ({config.windowSizeMinutes || 10} min windows)
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Downsampling</h4>
                        {config.downsampling?.enabled ? (
                          <>
                            <Badge variant="default">Enabled</Badge>
                            <p className="text-xs text-muted-foreground">
                              {((config.downsampling?.targetCoverage ?? 0.05) * 100).toFixed(0)}% coverage, {config.downsampling?.maxObsPerSat ?? 50} max obs/sat
                            </p>
                          </>
                        ) : (
                          <Badge variant="outline">Disabled</Badge>
                        )}
                      </div>
                      <div className="rounded-lg border p-4 space-y-3">
                        <h4 className="font-medium">Simulation</h4>
                        {config.simulation?.enabled ? (
                          <>
                            <Badge variant="default">Enabled</Badge>
                            <p className="text-xs text-muted-foreground">
                              {config.simulation?.sensorModel}, max {((config.simulation?.maxSyntheticRatio ?? 0.5) * 100).toFixed(0)}% synthetic
                            </p>
                          </>
                        ) : (
                          <Badge variant="outline">Disabled</Badge>
                        )}
                      </div>
                    </div>

                    {timeframeError && (
                      <div className="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 border border-destructive text-destructive">
                        <AlertCircle className="h-5 w-5 flex-shrink-0" />
                        <div>
                          <p className="font-medium">Invalid Configuration</p>
                          <p className="text-sm">{timeframeError}</p>
                        </div>
                      </div>
                    )}

                    <div className="bg-muted/50 rounded-lg p-4">
                      <h4 className="font-medium mb-2">Estimated Output</h4>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Observations</p>
                          <p className="font-semibold">~{(config.objectCount * config.observationDensity).toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">File Size</p>
                          <p className="font-semibold">~{(config.objectCount * 0.05).toFixed(1)} MB</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Format</p>
                          <p className="font-semibold">JSON</p>
                        </div>
                      </div>
                    </div>

                    {/* Dataset Code Preview (16-character code) */}
                    <div className="rounded-lg border p-4 space-y-4">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium">Dataset Code (16-character)</h4>
                        <Tooltip>
                          <TooltipTrigger>
                            <Info className="h-4 w-4 text-muted-foreground" />
                          </TooltipTrigger>
                          <TooltipContent className="max-w-sm">
                            <p className="mb-1">Positions in the 16-character dataset code:</p>
                            <ul className="text-xs space-y-0.5">
                              {CODE_POSITION_LABELS.map((p) => (
                                <li key={p.pos}>Pos {p.pos}: {p.label}</li>
                              ))}
                            </ul>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <div className="text-center py-3 bg-muted/50 rounded-lg">
                        <p className="font-mono text-3xl tracking-widest text-primary">
                          {generateStandardWizardCode(config)}
                        </p>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                        {(() => {
                          const code = generateStandardWizardCode(config);
                          const segments = [
                            { chars: code[0], label: 'Object Type' },
                            { chars: code.slice(1, 3), label: 'Target %' },
                            { chars: code.slice(3, 6), label: 'Regime' },
                            { chars: code.slice(6, 8), label: 'Event' },
                            { chars: code.slice(8, 10), label: 'Sensor' },
                            { chars: code[10], label: 'Coverage' },
                            { chars: code[11], label: 'Track Gap' },
                            { chars: code[12], label: 'Obs Density' },
                            { chars: code[13], label: 'Obj Count' },
                            { chars: code.slice(14, 16), label: 'Fitspan' },
                          ];
                          return segments.map((seg) => (
                            <div key={seg.label} className="rounded border p-2 text-center">
                              <p className="font-mono text-sm font-semibold">{seg.chars}</p>
                              <p className="text-[10px] text-muted-foreground">{seg.label}</p>
                            </div>
                          ));
                        })()}
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between p-6 pt-0">
            {/* Back Button */}
            <Button
              variant="outline"
              onClick={mode === 'legacy' ? prevLegacyStep : prevStep}
              disabled={activeStep === 1 || isGenerating || (mode === 'legacy' && codeInputMode === 'direct')}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>

            {/* Next / Generate Button */}
            {mode === 'standard' ? (
              // Standard mode navigation
              currentStep < 5 ? (
                <Button
                  onClick={nextStep}
                  className="gap-2"
                  disabled={mode === 'standard' && currentStep === 3 && !isTimeframeValid}
                >
                  Next
                  <ArrowRight className="h-4 w-4" />
                </Button>
              ) : (
                <Button
                  onClick={handleGenerate}
                  disabled={isGenerating || !isTimeframeValid || !hasUdlToken}
                  className="gap-2"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Check className="h-4 w-4" />
                      Generate Dataset
                    </>
                  )}
                </Button>
              )
            ) : (
              // Legacy mode navigation
              codeInputMode === 'wizard' ? (
                legacyStep < 7 ? (
                  <Button onClick={nextLegacyStep} className="gap-2">
                    Next
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                ) : (
                  <Button
                    onClick={handleLegacyGenerate}
                    disabled={isGenerating || !legacyCodeValidation.valid || !hasUdlToken}
                    className="gap-2"
                  >
                    {isGenerating ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Check className="h-4 w-4" />
                        Generate Dataset
                      </>
                    )}
                  </Button>
                )
              ) : (
                // Direct code entry mode
                <Button
                  onClick={handleLegacyGenerate}
                  disabled={isGenerating || !legacyCodeValidation.valid || directCodeInput.length !== 16 || !hasUdlToken}
                  className="gap-2"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Check className="h-4 w-4" />
                      Generate Dataset
                    </>
                  )}
                </Button>
              )
            )}
          </div>
        </Card>
      </div>
    </TooltipProvider>
  );
}
