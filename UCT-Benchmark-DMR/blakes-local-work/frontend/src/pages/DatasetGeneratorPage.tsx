import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  Info,
  Satellite,
  Zap,
  Settings2,
  FileCheck,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { OrbitalRegime, DatasetGenerationConfig } from '@/types';

const steps = [
  { id: 1, name: 'Regime', icon: Satellite },
  { id: 2, name: 'Quality', icon: Settings2 },
  { id: 3, name: 'Objects', icon: Zap },
  { id: 4, name: 'Review', icon: FileCheck },
];

const defaultConfig: DatasetGenerationConfig = {
  regime: 'LEO',
  coverage: 'standard',
  observationDensity: 50,
  trackGapTarget: 2,
  objectCount: 40,
  includeHamr: false,
  startDate: new Date().toISOString().split('T')[0],
  endDate: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  sensors: ['optical'],
};

const presets = [
  { name: 'Easy', description: 'High coverage, dense observations', config: { coverage: 'high' as const, observationDensity: 100, trackGapTarget: 1 } },
  { name: 'Standard', description: 'Moderate difficulty', config: { coverage: 'standard' as const, observationDensity: 50, trackGapTarget: 2 } },
  { name: 'Challenging', description: 'Sparse data, large gaps', config: { coverage: 'low' as const, observationDensity: 20, trackGapTarget: 4 } },
];

export function DatasetGeneratorPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [config, setConfig] = useState<DatasetGenerationConfig>(defaultConfig);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);

  const updateConfig = <K extends keyof DatasetGenerationConfig>(
    key: K,
    value: DatasetGenerationConfig[K]
  ) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const applyPreset = (preset: typeof presets[0]) => {
    setConfig((prev) => ({ ...prev, ...preset.config }));
  };

  const nextStep = () => setCurrentStep((prev) => Math.min(prev + 1, 4));
  const prevStep = () => setCurrentStep((prev) => Math.max(prev - 1, 1));

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerationProgress(0);

    // Simulate generation progress
    const interval = setInterval(() => {
      setGenerationProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          return 100;
        }
        return prev + 10;
      });
    }, 500);

    // Simulate completion after 5 seconds
    setTimeout(() => {
      clearInterval(interval);
      setGenerationProgress(100);
      setTimeout(() => {
        setIsGenerating(false);
        navigate('/datasets/my-datasets');
      }, 500);
    }, 5000);
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

                {/* Quick Presets */}
                <div className="pt-4 border-t">
                  <p className="text-sm font-medium mb-3">Quick Presets</p>
                  <div className="flex gap-2">
                    {presets.map((preset) => (
                      <Button
                        key={preset.name}
                        variant="outline"
                        size="sm"
                        onClick={() => applyPreset(preset)}
                        className="flex-1"
                      >
                        {preset.name}
                      </Button>
                    ))}
                  </div>
                </div>
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
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="startDate">Start Date</Label>
                    <Input
                      id="startDate"
                      type="date"
                      value={config.startDate}
                      onChange={(e) => updateConfig('startDate', e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="endDate">End Date</Label>
                    <Input
                      id="endDate"
                      type="date"
                      value={config.endDate}
                      onChange={(e) => updateConfig('endDate', e.target.value)}
                    />
                  </div>
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

          {/* Step 4: Review */}
          {currentStep === 4 && (
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
                      {generationProgress < 30 && 'Initializing data pipeline...'}
                      {generationProgress >= 30 && generationProgress < 60 && 'Fetching observation data...'}
                      {generationProgress >= 60 && generationProgress < 90 && 'Processing truth catalog...'}
                      {generationProgress >= 90 && 'Finalizing dataset...'}
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
                      </div>
                    </div>

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
            {currentStep < 4 ? (
              <Button onClick={nextStep} className="gap-2">
                Next
                <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button onClick={handleGenerate} disabled={isGenerating} className="gap-2">
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
