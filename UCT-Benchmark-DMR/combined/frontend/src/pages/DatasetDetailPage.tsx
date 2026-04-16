import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Download,
  Satellite,
  Database,
  Calendar,
  Globe,
  History,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { formatDate, formatFileSize } from '@/lib/utils';
import { downloadBlob } from '@/lib/downloadUtils';
import { useDataset, useDatasetObservations, useDatasetVersions, useDownloadDataset } from '@/hooks/useDatasets';
import { useDatasetReferenceOrbits } from '@/hooks/useDatasetReferenceOrbits';
import { CesiumGlobe } from '@/components/cesium/CesiumGlobe';
import { useToast } from '@/hooks/use-toast';

export function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  const { data: dataset, isLoading, error } = useDataset(id ?? '');
  const { data: observations, isLoading: obsLoading } = useDatasetObservations(id ?? '', { limit: 20 });
  const { data: versions = [] } = useDatasetVersions(id ?? '');
  const downloadMutation = useDownloadDataset();

  // 3D orbit preview: collapsed by default so Cesium chunk only loads on expand.
  // Hook fetch is gated on `orbitsOpen` to avoid calling the endpoint for users
  // who never open the section (403 non-owners would otherwise fire needlessly).
  const [orbitsOpen, setOrbitsOpen] = useState(false);
  const {
    data: referenceOrbits,
    isLoading: orbitsLoading,
    forbidden: orbitsForbidden,
  } = useDatasetReferenceOrbits(id, { enabled: orbitsOpen });

  const handleDownload = async () => {
    if (!dataset) return;
    try {
      const blob = await downloadMutation.mutateAsync(dataset.id);
      downloadBlob(blob, `${dataset.name}.json`);
    } catch (err: unknown) {
      console.error('Download failed:', err);
      const axiosErr = err as { response?: { status?: number; data?: unknown } };
      let serverDetail = '';
      if (axiosErr?.response?.data instanceof Blob) {
        try {
          const text = await axiosErr.response.data.text();
          const parsed = JSON.parse(text);
          serverDetail = parsed.detail || '';
        } catch { /* ignore */ }
      } else if (axiosErr?.response?.data && typeof axiosErr.response.data === 'object') {
        serverDetail = (axiosErr.response.data as { detail?: string }).detail || '';
      }
      const status = axiosErr?.response?.status;
      toast({
        title: 'Download failed',
        description: status === 404 && serverDetail
          ? serverDetail
          : status === 403
            ? "You don't own this dataset. Only the creator can download it."
            : status === 400
              ? serverDetail || 'This dataset is not available for download.'
              : 'Failed to download dataset. The server may be unavailable.',
        variant: 'destructive',
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !dataset) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl xs:text-3xl font-bold tracking-tight">Dataset Not Found</h1>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 gap-4">
            <AlertTriangle className="h-12 w-12 text-muted-foreground" />
            <p className="text-muted-foreground text-center">
              {(() => {
                const status = (error as { response?: { status?: number } } | null)?.response?.status;
                if (status === 404) {
                  return `No dataset exists with ID "${id}". It may have been deleted, or the link may be incorrect.`;
                }
                if (status === 403) {
                  return 'You do not have permission to view this dataset.';
                }
                return 'This dataset could not be loaded. Please try again later.';
              })()}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => navigate(-1)}>
                Go Back
              </Button>
              <Link to="/datasets">
                <Button>Browse Datasets</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl xs:text-3xl font-bold tracking-tight break-words">{dataset.name}</h1>
              <Badge variant={dataset.regime === 'LEO' ? 'leo' : dataset.regime === 'MEO' ? 'meo' : dataset.regime === 'GEO' ? 'geo' : 'heo'}>
                {dataset.regime}
              </Badge>
              <Badge variant={dataset.tier === 'T1' ? 'tier1' : dataset.tier === 'T2' ? 'tier2' : dataset.tier === 'T3' ? 'tier3' : 'tier4'}>
                {dataset.tier}
              </Badge>
              {dataset.version && dataset.version > 1 && (
                <Badge variant="outline" className="font-mono">v{dataset.version}</Badge>
              )}
            </div>
            {dataset.description && (
              <p className="text-muted-foreground mt-1">{dataset.description}</p>
            )}
          </div>
        </div>
        <Button
          onClick={handleDownload}
          disabled={downloadMutation.isPending}
          className="gap-2"
        >
          {downloadMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Downloading...
            </>
          ) : (
            <>
              <Download className="h-4 w-4" />
              Download Dataset
            </>
          )}
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Satellite className="h-4 w-4" />
              Objects
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{dataset.objectCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Database className="h-4 w-4" />
              Observations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{dataset.observationCount.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Coverage</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{(dataset.coverage * 100).toFixed(1)}%</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Size</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{formatFileSize(dataset.sizeBytes)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Dataset Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div>
              <dt className="text-muted-foreground">Created</dt>
              <dd className="font-medium">{formatDate(dataset.createdAt)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Regime</dt>
              <dd className="font-medium">{dataset.regime}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Tier</dt>
              <dd className="font-medium">{dataset.tier}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Sensor Types</dt>
              <dd className="font-medium">{dataset.sensorTypes.join(', ') || 'N/A'}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Observations Sample */}
      <Card>
        <CardHeader>
          <CardTitle>Observations (Sample)</CardTitle>
        </CardHeader>
        <CardContent>
          {obsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : observations && observations.observations.length > 0 ? (
            <>
              {/* Observations are a read-only preview — horizontal scroll is acceptable on mobile */}
              <div className="-mx-4 sm:mx-0 overflow-x-auto">
                <div className="min-w-[560px] sm:min-w-0 px-4 sm:px-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Time</TableHead>
                        <TableHead>RA</TableHead>
                        <TableHead>Declination</TableHead>
                        <TableHead>Sensor</TableHead>
                        <TableHead>Track ID</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {observations.observations.map((obs, idx) => (
                        <TableRow key={obs.id || idx}>
                          <TableCell className="font-mono text-xs">
                            {new Date(obs.ob_time).toISOString().replace('T', ' ').slice(0, 19)}
                          </TableCell>
                          <TableCell>{obs.ra.toFixed(4)}</TableCell>
                          <TableCell>{obs.declination.toFixed(4)}</TableCell>
                          <TableCell>{obs.sensor_name || '-'}</TableCell>
                          <TableCell className="font-mono text-xs">{obs.track_id || '-'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                Showing {observations.observations.length} of {observations.total_count.toLocaleString()} observations
              </p>
            </>
          ) : (
            <p className="text-center py-8 text-muted-foreground">
              No observation data available for preview.
            </p>
          )}
        </CardContent>
      </Card>

      {/* 3D Orbit Preview — reference orbits are the dataset answer key,
          so the backend gates this to the dataset owner + admins.
          Non-owners will see the header but get a polite note on expand. */}
      <Card>
        <CardHeader>
          <button
            type="button"
            onClick={() => setOrbitsOpen((v) => !v)}
            className="flex w-full items-center gap-2 text-left hover:opacity-80 transition-opacity"
            aria-expanded={orbitsOpen}
            aria-controls="orbits-panel"
          >
            {orbitsOpen ? (
              <ChevronDown className="h-4 w-4 shrink-0" />
            ) : (
              <ChevronRight className="h-4 w-4 shrink-0" />
            )}
            <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
              <Globe className="h-4 w-4" />
              3D Orbit Preview
            </CardTitle>
            <span className="text-xs text-muted-foreground ml-2">
              (owner + admin only)
            </span>
          </button>
        </CardHeader>
        {orbitsOpen && (
          <CardContent id="orbits-panel">
            {orbitsLoading ? (
              <div className="flex items-center justify-center h-[320px] sm:h-[400px] lg:h-[500px]">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : orbitsForbidden ? (
              <div className="flex flex-col items-center justify-center py-12 gap-2 text-center">
                <AlertTriangle className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground max-w-md">
                  Reference orbits are the dataset answer key. Only the dataset
                  owner or an admin can view the 3D preview.
                </p>
              </div>
            ) : referenceOrbits && referenceOrbits.satellites.length > 0 ? (
              <CesiumGlobe
                satellites={referenceOrbits.satellites}
                startTime={referenceOrbits.startTime}
                endTime={referenceOrbits.endTime}
                ariaLabel={`Reference orbits for dataset ${dataset.name}`}
                fallback={
                  <div className="flex items-center justify-center h-[320px] sm:h-[400px] text-sm text-muted-foreground">
                    3D view unavailable in this browser. Reference orbits are
                    still accessible via the API.
                  </div>
                }
              />
            ) : (
              <p className="text-center py-8 text-muted-foreground text-sm">
                No reference orbits are persisted for this dataset yet. If the
                dataset is still generating, check back once it is available.
              </p>
            )}
          </CardContent>
        )}
      </Card>

      {/* Version History */}
      {versions.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History className="h-4 w-4" />
              Version History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {versions.map((v) => (
                <div
                  key={v.id}
                  className={`flex items-center justify-between rounded-lg border p-3 ${v.id === dataset.id ? 'border-primary bg-primary/5' : ''}`}
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="font-mono">v{v.version ?? 1}</Badge>
                      <span className="font-medium text-sm">{v.name}</span>
                      {v.id === dataset.id && (
                        <Badge variant="secondary" className="text-xs">current</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {v.objectCount} objects &middot; {v.observationCount.toLocaleString()} obs &middot; {formatDate(v.createdAt)}
                    </p>
                  </div>
                  {v.id !== dataset.id && (
                    <Link to={`/datasets/${v.id}`}>
                      <Button variant="ghost" size="sm">View</Button>
                    </Link>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
