import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import {
  Upload,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  FileJson,
  X,
} from 'lucide-react';
import { cn, formatFileSize } from '@/lib/utils';
import { useDatasets } from '@/hooks/useDatasets';
import { useCreateSubmission } from '@/hooks/useSubmissions';
import { useToast } from '@/hooks/use-toast';

interface ValidationStep {
  id: string;
  label: string;
  status: 'pending' | 'checking' | 'passed' | 'failed';
  message?: string;
}

export function SubmitPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [file, setFile] = useState<File | null>(null);
  const [datasetId, setDatasetId] = useState('');
  const [algorithmName, setAlgorithmName] = useState('');
  const [version, setVersion] = useState('');
  const [description, setDescription] = useState('');
  const [organization, setOrganization] = useState('');
  const [submitAttempted, setSubmitAttempted] = useState(false);

  // Prefill form from URL search params (e.g. re-submit from failed submission)
  useEffect(() => {
    const prefillDataset = searchParams.get('dataset');
    const prefillAlgorithm = searchParams.get('algorithm');
    const prefillVersion = searchParams.get('version');
    if (prefillDataset) setDatasetId(prefillDataset);
    if (prefillAlgorithm) setAlgorithmName(prefillAlgorithm);
    if (prefillVersion) setVersion(prefillVersion);
  }, [searchParams]);
  const [isValidating, setIsValidating] = useState(false);
  const [validationSteps, setValidationSteps] = useState<ValidationStep[]>([
    { id: 'format', label: 'File format (valid JSON)', status: 'pending' },
    { id: 'schema', label: 'UCTP schema (required fields)', status: 'pending' },
    { id: 'references', label: 'Observation ID references (sourcedData)', status: 'pending' },
    { id: 'state', label: 'State vector / TLE value check', status: 'pending' },
    { id: 'covariance', label: 'Covariance format (if present)', status: 'pending' },
  ]);

  const { toast } = useToast();

  // Use real API hooks
  const { data: datasets = [], isLoading: loadingDatasets } = useDatasets({ regime: 'all', tier: 'all' });
  const createSubmission = useCreateSubmission();

  // Gate the Submit dropdown on the authoritative eval-readiness signal
  // (`has_reference_orbits` from the backend). This replaces the earlier
  // date-based heuristic — some post-Apr-9 datasets still failed generation's
  // reference-persistence step, so date alone was insufficient
  // (QA_PROD_RUN_2026-04-17 C1).
  const availableDatasets = datasets.filter((d) => d.id && d.hasReferenceOrbits);

  const runValidation = async (uploadedFile: File) => {
    setIsValidating(true);

    // Reset all steps to pending
    setValidationSteps((steps) =>
      steps.map((step) => ({ ...step, status: 'pending' }))
    );

    // Helper to update step status
    const updateStep = (id: string, status: 'checking' | 'passed' | 'failed', message?: string) => {
      setValidationSteps((steps) =>
        steps.map((step) => (step.id === id ? { ...step, status, message } : step))
      );
    };

    // Helper to add delay for visual feedback
    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    try {
      // Step 1: File format validation
      updateStep('format', 'checking');
      await delay(300);

      const fileText = await uploadedFile.text();
      let parsedJson: unknown;

      try {
        parsedJson = JSON.parse(fileText);
        updateStep('format', 'passed');
      } catch {
        updateStep('format', 'failed', 'Invalid JSON format');
        setIsValidating(false);
        return;
      }

      // Step 2: Schema validation
      // UCTP output is a JSON array of orbit records, each with required fields.
      // State-vector format: sourcedData, epoch, xpos, ypos, zpos, xvel, yvel, zvel
      // TLE format: sourcedData, line1, line2
      updateStep('schema', 'checking');
      await delay(400);

      // The UCTP output must be an array of orbit record objects
      let records: Record<string, unknown>[];
      if (Array.isArray(parsedJson)) {
        records = parsedJson as Record<string, unknown>[];
      } else if (parsedJson && typeof parsedJson === 'object') {
        // Support legacy wrapper formats: { satellites: [...], tracks: [...], results: [...], ucds: [...] }
        const wrapper = parsedJson as Record<string, unknown>;
        const inner = wrapper.satellites || wrapper.tracks || wrapper.results || wrapper.ucds;
        if (Array.isArray(inner)) {
          records = inner as Record<string, unknown>[];
        } else {
          updateStep('schema', 'failed', 'Expected a JSON array of orbit records, or an object with a satellites/tracks/results array');
          setIsValidating(false);
          return;
        }
      } else {
        updateStep('schema', 'failed', 'Expected a JSON array of orbit records');
        setIsValidating(false);
        return;
      }

      if (records.length === 0) {
        updateStep('schema', 'failed', 'File contains an empty array (no orbit records)');
        setIsValidating(false);
        return;
      }

      // Detect format from first record
      const first = records[0];
      if (typeof first !== 'object' || first === null) {
        updateStep('schema', 'failed', 'Each orbit record must be a JSON object');
        setIsValidating(false);
        return;
      }

      const isTLE = 'line1' in first && 'line2' in first;
      const requiredFields = isTLE
        ? ['sourcedData', 'line1', 'line2']
        : ['sourcedData', 'epoch', 'xpos', 'ypos', 'zpos', 'xvel', 'yvel', 'zvel'];

      // Also accept common aliases for state-vector field names
      // Must stay in sync with uct_benchmark/utils/field_mapping.py FIELD_ALIASES
      const fieldAliases: Record<string, string[]> = {
        sourcedData: ['grouped_ops', 'sourced_data', 'grouped_observations', 'obs_ids', 'observation_ids'],
        epoch: ['Epoch', 'time', 'datetime', 'timestamp'],
        xpos: ['X', 'x', 'posX', 'x_pos', 'pos_x', 'position_x'],
        ypos: ['Y', 'y', 'posY', 'y_pos', 'pos_y', 'position_y'],
        zpos: ['Z', 'z', 'posZ', 'z_pos', 'pos_z', 'position_z'],
        xvel: ['VX', 'vx', 'velX', 'Xdot', 'x_vel', 'vel_x', 'velocity_x', 'xdot', 'x_dot'],
        yvel: ['VY', 'vy', 'velY', 'Ydot', 'y_vel', 'vel_y', 'velocity_y', 'ydot', 'y_dot'],
        zvel: ['VZ', 'vz', 'velZ', 'Zdot', 'z_vel', 'vel_z', 'velocity_z', 'zdot', 'z_dot'],
      };

      const missingFields: string[] = [];
      for (const field of requiredFields) {
        const hasField = field in first;
        const hasAlias = (fieldAliases[field] || []).some((alias) => alias in first);
        if (!hasField && !hasAlias) {
          missingFields.push(field);
        }
      }

      if (missingFields.length > 0) {
        const formatLabel = isTLE ? 'TLE' : 'state-vector';
        updateStep(
          'schema',
          'failed',
          `Missing required ${formatLabel} fields in first record: ${missingFields.join(', ')}`
        );
        setIsValidating(false);
        return;
      }

      updateStep('schema', 'passed');

      // Step 3: Observation ID references (sourcedData should contain observation IDs)
      updateStep('references', 'checking');
      await delay(350);

      let hasValidReferences = true;
      let refErrorMsg = '';
      for (let i = 0; i < Math.min(records.length, 10); i++) {
        const rec = records[i];
        const sourced = rec.sourcedData ?? rec.grouped_ops ?? rec.sourced_data;
        if (!Array.isArray(sourced) || sourced.length === 0) {
          hasValidReferences = false;
          refErrorMsg = `Record ${i}: sourcedData must be a non-empty array of observation IDs`;
          break;
        }
      }

      if (hasValidReferences) {
        updateStep('references', 'passed');
      } else {
        updateStep('references', 'failed', refErrorMsg);
        setIsValidating(false);
        return;
      }

      // Step 4: State vector / TLE value reasonableness
      updateStep('state', 'checking');
      await delay(500);

      let stateValid = true;
      let stateErrorMsg = '';
      if (isTLE) {
        // TLE lines should be strings of ~69 characters
        for (let i = 0; i < Math.min(records.length, 10); i++) {
          const rec = records[i];
          if (typeof rec.line1 !== 'string' || typeof rec.line2 !== 'string') {
            stateValid = false;
            stateErrorMsg = `Record ${i}: line1 and line2 must be strings`;
            break;
          }
        }
      } else {
        // State-vector: numeric fields should be finite numbers
        const numericFields = ['xpos', 'ypos', 'zpos', 'xvel', 'yvel', 'zvel'];
        const numericAliases: Record<string, string[]> = fieldAliases;
        for (let i = 0; i < Math.min(records.length, 10); i++) {
          const rec = records[i];
          for (const field of numericFields) {
            const val = rec[field] ?? (numericAliases[field] || []).reduce<unknown>(
              (found, alias) => found ?? rec[alias], undefined
            );
            if (val !== undefined && (typeof val !== 'number' || !Number.isFinite(val))) {
              stateValid = false;
              stateErrorMsg = `Record ${i}: '${field}' must be a finite number, got ${typeof val}`;
              break;
            }
          }
          if (!stateValid) break;
        }
      }

      if (stateValid) {
        updateStep('state', 'passed');
      } else {
        updateStep('state', 'failed', stateErrorMsg);
        setIsValidating(false);
        return;
      }

      // Step 5: Covariance check (optional but validate format if present)
      updateStep('covariance', 'checking');
      await delay(400);

      let covarianceValid = true;
      let covErrorMsg = '';
      if (!isTLE) {
        for (let i = 0; i < Math.min(records.length, 10); i++) {
          const rec = records[i];
          const cov = rec.covariance ?? rec.cov;
          if (cov !== undefined) {
            if (!Array.isArray(cov)) {
              covarianceValid = false;
              covErrorMsg = `Record ${i}: 'cov' must be an array, got ${typeof cov}`;
              break;
            }
            if ((cov as unknown[]).length !== 21) {
              covarianceValid = false;
              covErrorMsg = `Record ${i}: 'cov' should have 21 lower-triangular elements, got ${(cov as unknown[]).length}`;
              break;
            }
          }
        }
      }

      if (covarianceValid) {
        updateStep('covariance', 'passed');
      } else {
        updateStep('covariance', 'failed', covErrorMsg);
      }
    } catch (err) {
      console.error('Validation error:', err);
      updateStep('format', 'failed', 'Error reading file');
    }

    setIsValidating(false);
  };

  const onDrop = (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const uploadedFile = acceptedFiles[0];
      setFile(uploadedFile);
      runValidation(uploadedFile);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/json': ['.json'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: false,
  });

  const clearFile = () => {
    setFile(null);
    setValidationSteps((steps) =>
      steps.map((step) => ({ ...step, status: 'pending' }))
    );
  };

  const scrollToFirstError = useCallback(() => {
    // Wait for React to render the error messages, then scroll to the first one.
    // Use block: 'start' + CSS scroll-margin (scroll-mt-20) so the sticky header
    // doesn't cover the error target on mobile.
    requestAnimationFrame(() => {
      const firstError = document.querySelector('.text-destructive');
      if (firstError) {
        firstError.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }, []);

  const handleSubmit = async () => {
    setSubmitAttempted(true);
    if (!file || !datasetId || !algorithmName || !version) {
      scrollToFirstError();
      return;
    }
    if (!canSubmit) return;

    try {
      await createSubmission.mutateAsync({
        datasetId,
        algorithmName,
        version,
        description: description || undefined,
        classificationMarking: organization || undefined,
        file,
      });

      // Navigate to submissions page
      navigate('/submit/my-submissions');
    } catch (error: unknown) {
      console.error('Submission failed:', error);
      // U6: Distinguish validation errors from network/server failures
      const axiosError = error as {
        response?: {
          status?: number;
          data?: { detail?: string | { message?: string; errors?: string[]; hint?: string } };
        };
      };
      const status = axiosError?.response?.status;
      const detail = axiosError?.response?.data?.detail;
      let toastDescription = 'Failed to submit your algorithm results. Please try again.';
      if (status === 422 && detail && typeof detail === 'object') {
        // Backend returns structured validation errors
        const schemaErrors = detail.errors || [];
        const hint = detail.hint || '';
        toastDescription = detail.message || 'UCTP schema validation failed';
        if (schemaErrors.length > 0) {
          toastDescription += ': ' + schemaErrors.slice(0, 3).join('; ');
          if (schemaErrors.length > 3) {
            toastDescription += ` (and ${schemaErrors.length - 3} more)`;
          }
        }
        if (hint) {
          toastDescription += '. ' + hint;
        }
      } else if (status === 422) {
        toastDescription = typeof detail === 'string'
          ? detail
          : 'Validation error — please check your file format matches the UCTP schema.';
      } else if (status === 413) {
        toastDescription = 'File too large — maximum upload size is 50MB.';
      } else if (!status) {
        toastDescription = 'Network error — check your connection and try again.';
      }
      toast({
        title: 'Submission failed',
        description: toastDescription,
        variant: 'destructive',
      });
    }
  };

  // U10: Memoize validation check to avoid recomputing on every keystroke
  const allValidationsPassed = useMemo(
    () => validationSteps.every((step) => step.status === 'passed'),
    [validationSteps]
  );
  const canSubmit =
    file &&
    datasetId &&
    algorithmName &&
    version &&
    allValidationsPassed &&
    !createSubmission.isPending;

  const getStepIcon = (status: ValidationStep['status']) => {
    switch (status) {
      case 'pending':
        return <div className="h-4 w-4 rounded-full border-2 border-muted" />;
      case 'checking':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case 'passed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Submit Algorithm Results</h1>
        <p className="text-muted-foreground mt-1">
          Upload your UCT algorithm results for evaluation against benchmark datasets
        </p>
      </div>

      {/* File Upload */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Submission File</CardTitle>
          <CardDescription>
            Upload your algorithm output in JSON format (max 50MB)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!file ? (
            <div
              {...getRootProps()}
              className={cn(
                'border-2 border-dashed rounded-lg p-6 sm:p-12 text-center cursor-pointer transition-colors',
                isDragActive
                  ? 'border-primary bg-primary/5'
                  : 'border-muted hover:border-primary/50 hover:bg-muted/50'
              )}
            >
              <input {...getInputProps()} />
              <div className="flex flex-col items-center gap-4">
                <div className="rounded-full bg-muted p-4">
                  <Upload className="h-8 w-8 text-muted-foreground" />
                </div>
                <div>
                  <p className="font-medium">
                    {isDragActive ? (
                      'Drop your file here'
                    ) : (
                      <>
                        <span className="hidden sm:inline">Drag &amp; drop your submission file here</span>
                        <span className="sm:hidden">Tap to choose file</span>
                      </>
                    )}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1 hidden sm:block">
                    or <span className="text-primary">browse files</span>
                  </p>
                </div>
                <p className="text-xs text-muted-foreground">
                  Accepts: .json (max 50MB)
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* File Info */}
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-primary/10 p-2">
                    <FileJson className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">{file.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                </div>
                <Button variant="ghost" size="icon" onClick={clearFile}>
                  <X className="h-4 w-4" />
                </Button>
              </div>

              {/* Validation Status */}
              <div className="rounded-lg border p-4 space-y-3">
                <h4 className="font-medium">Validation Status</h4>
                <div className="space-y-2">
                  {validationSteps.map((step) => (
                    <div key={step.id} className="flex items-start gap-3">
                      <div className="mt-0.5">{getStepIcon(step.status)}</div>
                      <div>
                        <span
                          className={cn(
                            'text-sm',
                            step.status === 'passed' && 'text-green-600',
                            step.status === 'failed' && 'text-red-600',
                            step.status === 'pending' && 'text-muted-foreground'
                          )}
                        >
                          {step.label}
                          {step.status === 'passed' && ' — passed'}
                          {step.status === 'failed' && ' — failed'}
                        </span>
                        {step.status === 'failed' && step.message && (
                          <p className="text-xs text-red-500 mt-0.5">{step.message}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                {isValidating && (
                  <Progress
                    value={
                      (validationSteps.filter((s) => s.status === 'passed').length /
                        validationSteps.length) *
                      100
                    }
                    className="h-2"
                  />
                )}
              </div>
            </div>
          )}
          {submitAttempted && !file && (
            <p className="text-sm text-destructive mt-1 scroll-mt-20">This field is required</p>
          )}
        </CardContent>
      </Card>

      {/* Submission Details */}
      <Card>
        <CardHeader>
          <CardTitle>Submission Details</CardTitle>
          <CardDescription>
            Provide information about your algorithm and select the target dataset
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Dataset Selection */}
          <div className="space-y-2">
            <Label htmlFor="dataset">Target Dataset</Label>
            <Select value={datasetId} onValueChange={setDatasetId} disabled={loadingDatasets}>
              <SelectTrigger id="dataset">
                <SelectValue placeholder={loadingDatasets ? 'Loading datasets...' : 'Select a dataset...'} />
              </SelectTrigger>
              <SelectContent>
                {availableDatasets.map((dataset) => (
                  <SelectItem key={dataset.id} value={dataset.id}>
                    {dataset.name}
                  </SelectItem>
                ))}
                {availableDatasets.length === 0 && !loadingDatasets && (
                  <SelectItem value="__none__" disabled>
                    No datasets available
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
            {submitAttempted && !datasetId && (
              <p className="text-sm text-destructive mt-1 scroll-mt-20">This field is required</p>
            )}
          </div>

          {/* Algorithm Name */}
          <div className="space-y-2">
            <Label htmlFor="algorithmName">Algorithm Name</Label>
            <Input
              id="algorithmName"
              placeholder="e.g., MyUCTP"
              value={algorithmName}
              onChange={(e) => setAlgorithmName(e.target.value)}
              autoComplete="off"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
            />
            {submitAttempted && !algorithmName && (
              <p className="text-sm text-destructive mt-1 scroll-mt-20">This field is required</p>
            )}
          </div>

          {/* Version */}
          <div className="space-y-2">
            <Label htmlFor="version">Version</Label>
            <Input
              id="version"
              placeholder="e.g., v2.1"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              autoComplete="off"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
            />
            {submitAttempted && !version && (
              <p className="text-sm text-destructive mt-1 scroll-mt-20">This field is required</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description (optional)</Label>
            <Textarea
              id="description"
              placeholder="Brief description of this submission or changes from previous version..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>

          {/* Organization */}
          <div className="space-y-2">
            <Label htmlFor="organization">Organization (optional)</Label>
            <Input
              id="organization"
              placeholder="e.g., DMR Lab, TAP Lab"
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Classification marking label for your organization
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Submit Button */}
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={() => navigate(-1)}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={createSubmission.isPending}
          className="gap-2"
        >
          {createSubmission.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Submitting...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" />
              Submit for Evaluation
            </>
          )}
        </Button>
      </div>

      {/* Guidelines Link */}
      <Card className="bg-muted/50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div>
              <p className="font-medium">Submission Guidelines</p>
              <p className="text-sm text-muted-foreground mt-1">
                Make sure your submission file follows the required JSON schema.
                See the <a href="/docs" className="text-primary hover:underline">documentation</a> for
                detailed format specifications and examples.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
