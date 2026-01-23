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
import type { OrbitalRegime, DatasetGenerationConfig, DownsamplingOptions, SimulationOptions, SearchStrategy } from '@/types';

const steps = [
  { id: 1, name: 'Regime', icon: Satellite },
  { id: 2, name: 'Quality', icon: Settings2 },
  { id: 3, name: 'Objects', icon: Zap },
  { id: 4, name: 'Advanced', icon: Settings2 },
  { id: 5, name: 'Review', icon: FileCheck },
];

// Calculate timeframe in days from start and end dates
function calculateTimeframeDays(startDate: string, endDate: string): number {
  const start = new Date(startDate);
  const end = new Date(endDate);
  if (isNaN(start.getTime()) || isNaN(end.getTime())) {
    return 0;
  }
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
};

export function DatasetGeneratorPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [config, setConfig] = useState<DatasetGenerationConfig>(defaultConfig);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);

  const generateDatasetMutation = useGenerateDataset();
  const { data: jobStatus } = useJobStatus(jobId);

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

  const nextStep = () => setCurrentStep((prev) => Math.min(prev + 1, 5));
  const prevStep = () => setCurrentStep((prev) => Math.max(prev - 1, 1));

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
    console.log('=== handleGenerate called ===');
    console.log('Current config state:', JSON.stringify(config, null, 2));

    setIsGenerating(true);
    setGenerationProgress(0);

    console.log('Generating dataset with config:', config);

    try {
      const result = await generateDatasetMutation.mutateAsync(config);
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
    } catch (error: any) {
      console.error('Failed to generate dataset:', error);
      console.error('Error response:', error?.response?.data);

      // Handle Pydantic validation errors which return an array of error details
      let errorMessage = 'Unknown error';
      const detail = error?.response?.data?.detail;
      if (Array.isArray(detail)) {
        // Pydantic validation error - format each error
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

  return (
    <TooltipProvider>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Generate Dataset</h1>
          <p className="text-muted-foreground mt-1">
            Configure parameters to generate a custom benchmark dataset
          </p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-between mb-8">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-full transition-colors',
                  currentStep === step.id
                    ? 'bg-primary text-primary-foreground'
                    : currentStep > step.id
                    ? 'bg-primary/20 text-primary'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {currentStep > step.id ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <step.icon className="h-4 w-4" />
                )}
                <span className="font-medium text-sm hidden sm:inline">{step.name}</span>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={cn(
                    'h-0.5 w-8 sm:w-16 mx-2',
                    currentStep > step.id ? 'bg-primary' : 'bg-muted'
                  )}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step Content */}
        <Card>
          {/* Step 1: Regime Selection */}
          {currentStep === 1 && (
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
                    { value: 'LEO', label: 'Low Earth Orbit', desc: '200-2000 km altitude, fast-moving satellites', color: 'bg-orbital-leo' },
                    { value: 'MEO', label: 'Medium Earth Orbit', desc: '2000-35,786 km, navigation satellites', color: 'bg-orbital-meo' },
                    { value: 'GEO', label: 'Geostationary Orbit', desc: '35,786 km, stationary position', color: 'bg-orbital-geo' },
                    { value: 'HEO', label: 'Highly Elliptical Orbit', desc: 'Variable altitude, challenging tracking', color: 'bg-orbital-heo' },
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
              </CardContent>
            </>
          )}

          {/* Step 2: Quality Parameters */}
          {currentStep === 2 && (
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
                        <p>Percentage of the orbital arc covered by observations. Lower coverage simulates sparse observation scenarios.</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <RadioGroup
                    value={config.coverage}
                    onValueChange={(value) => updateConfig('coverage', value as typeof config.coverage)}
                    className="grid grid-cols-2 sm:grid-cols-4 gap-2"
                  >
                    {[
                      { value: 'high', label: 'High (>70%)' },
                      { value: 'standard', label: 'Standard (30-70%)' },
                      { value: 'low', label: 'Low (<30%)' },
                      { value: 'mixed', label: 'Mixed' },
                    ].map((opt) => (
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
              </CardContent>
            </>
          )}

          {/* Step 3: Object Selection */}
          {currentStep === 3 && (
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
              </CardContent>
            </>
          )}

          {/* Step 4: Advanced (Downsampling & Simulation) */}
          {currentStep === 4 && (
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
              </CardContent>
            </>
          )}

          {/* Step 5: Review */}
          {currentStep === 5 && (
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
                        <h4 className="font-medium">Objects</h4>
                        <p className="text-2xl font-semibold">{config.objectCount}</p>
                        <p className="text-xs text-muted-foreground">
                          {config.includeHamr ? 'Including HAMR objects' : 'Standard objects only'}
                        </p>
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
                  </>
                )}
              </CardContent>
            </>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between p-6 pt-0">
            <Button
              variant="outline"
              onClick={prevStep}
              disabled={currentStep === 1 || isGenerating}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            {currentStep < 5 ? (
              <Button
                onClick={nextStep}
                className="gap-2"
                disabled={currentStep === 3 && !isTimeframeValid}
              >
                Next
                <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                onClick={handleGenerate}
                disabled={isGenerating || !isTimeframeValid}
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
            )}
          </div>
        </Card>
      </div>
    </TooltipProvider>
  );
}
