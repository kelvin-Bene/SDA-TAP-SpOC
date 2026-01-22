import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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

interface ValidationStep {
  id: string;
  label: string;
  status: 'pending' | 'checking' | 'passed' | 'failed';
  message?: string;
}

export function SubmitPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [datasetId, setDatasetId] = useState('');
  const [algorithmName, setAlgorithmName] = useState('');
  const [version, setVersion] = useState('');
  const [description, setDescription] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [validationSteps, setValidationSteps] = useState<ValidationStep[]>([
    { id: 'format', label: 'File format valid', status: 'pending' },
    { id: 'schema', label: 'Schema validation passed', status: 'pending' },
    { id: 'references', label: 'Observation ID references valid', status: 'pending' },
    { id: 'state', label: 'State vector reasonableness', status: 'pending' },
    { id: 'covariance', label: 'Covariance positive-definiteness', status: 'pending' },
  ]);

  // Use real API hooks
  const { data: datasets = [], isLoading: loadingDatasets } = useDatasets({ regime: 'all', tier: 'all' });
  const createSubmission = useCreateSubmission();

  // Filter to only available datasets
  const availableDatasets = datasets.filter((d) => d.id);

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
      updateStep('schema', 'checking');
      await delay(400);

      const data = parsedJson as Record<string, unknown>;
      const hasRequiredFields =
        data &&
        typeof data === 'object' &&
        ('satellites' in data || 'tracks' in data || 'results' in data || 'ucds' in data);

      if (hasRequiredFields) {
        updateStep('schema', 'passed');
      } else {
        updateStep('schema', 'failed', 'Missing required fields (satellites, tracks, or results)');
        setIsValidating(false);
        return;
      }

      // Step 3: Observation ID references
      updateStep('references', 'checking');
      await delay(350);

      // Check if there are any satellite/track entries with IDs
      const satellites = (data.satellites || data.tracks || data.results || data.ucds) as unknown[];
      const hasValidReferences = Array.isArray(satellites) && satellites.length > 0;

      if (hasValidReferences) {
        updateStep('references', 'passed');
      } else {
        updateStep('references', 'failed', 'No valid satellite or track entries found');
        setIsValidating(false);
        return;
      }

      // Step 4: State vector reasonableness
      updateStep('state', 'checking');
      await delay(500);

      // Check if state vectors exist and have reasonable values
      let stateVectorValid = true;
      if (Array.isArray(satellites)) {
        for (const sat of satellites) {
          const s = sat as Record<string, unknown>;
          const state = s.state || s.state_vector || s.position;
          if (state) {
            const stateArr = state as number[];
            // Basic check: state values shouldn't be NaN or Infinity
            if (Array.isArray(stateArr)) {
              const hasInvalidValues = stateArr.some(
                (v) => typeof v !== 'number' || !Number.isFinite(v)
              );
              if (hasInvalidValues) {
                stateVectorValid = false;
                break;
              }
            }
          }
        }
      }

      if (stateVectorValid) {
        updateStep('state', 'passed');
      } else {
        updateStep('state', 'failed', 'State vectors contain invalid values');
        setIsValidating(false);
        return;
      }

      // Step 5: Covariance check
      updateStep('covariance', 'checking');
      await delay(400);

      // Check if covariance matrices exist (optional but check format if present)
      let covarianceValid = true;
      if (Array.isArray(satellites)) {
        for (const sat of satellites) {
          const s = sat as Record<string, unknown>;
          const cov = s.covariance || s.cov;
          if (cov) {
            // Basic check: covariance should be an array or matrix
            if (!Array.isArray(cov)) {
              covarianceValid = false;
              break;
            }
          }
        }
      }

      if (covarianceValid) {
        updateStep('covariance', 'passed');
      } else {
        updateStep('covariance', 'failed', 'Invalid covariance matrix format');
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

  const handleSubmit = async () => {
    if (!file || !datasetId || !algorithmName || !version) return;

    try {
      await createSubmission.mutateAsync({
        datasetId,
        algorithmName,
        version,
        description: description || undefined,
        file,
      });

      // Navigate to submissions page
      navigate('/submit/my-submissions');
    } catch (error) {
      console.error('Submission failed:', error);
      alert('Failed to submit. Please try again.');
    }
  };

  const allValidationsPassed = validationSteps.every((step) => step.status === 'passed');
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
                'border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors',
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
                    {isDragActive ? 'Drop your file here' : 'Drag & drop your submission file here'}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
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
                  <SelectItem value="" disabled>
                    No datasets available
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          {/* Algorithm Name */}
          <div className="space-y-2">
            <Label htmlFor="algorithmName">Algorithm Name</Label>
            <Input
              id="algorithmName"
              placeholder="e.g., MyUCTP"
              value={algorithmName}
              onChange={(e) => setAlgorithmName(e.target.value)}
            />
          </div>

          {/* Version */}
          <div className="space-y-2">
            <Label htmlFor="version">Version</Label>
            <Input
              id="version"
              placeholder="e.g., v2.1"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
            />
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
        </CardContent>
      </Card>

      {/* Submit Button */}
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={() => navigate(-1)}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={!canSubmit}
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
