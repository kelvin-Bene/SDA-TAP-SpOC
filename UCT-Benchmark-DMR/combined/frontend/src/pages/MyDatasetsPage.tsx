import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Plus, Download, Trash2, Copy, Eye, Loader2, History, AlertCircle } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn, formatDate, formatFileSize } from '@/lib/utils';
import { downloadBlob } from '@/lib/downloadUtils';
import { useDatasets, useDeleteDataset, useDownloadDataset, transformDataset } from '@/hooks/useDatasets';
import { api } from '@/api/client';
import { useAuthStore } from '@/stores/authStore';
import { useToast } from '@/hooks/use-toast';
import type { Dataset } from '@/types';

export function MyDatasetsPage() {
  const { data: datasets, isLoading, error, refetch } = useDatasets({ mine: true });
  const deleteDataset = useDeleteDataset();
  const downloadMutation = useDownloadDataset();
  const isAdmin = useAuthStore((s) => s.isAdmin);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { toast } = useToast();
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [datasetToDelete, setDatasetToDelete] = useState<Dataset | null>(null);
  const [versionHistory, setVersionHistory] = useState<Dataset[] | null>(null);
  const [versionDataset, setVersionDataset] = useState<Dataset | null>(null);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const userDatasets = datasets ?? [];

  // Read highlight param from URL (set after successful generation)
  useEffect(() => {
    const id = searchParams.get('highlight');
    if (id) {
      setHighlightId(id);
      refetch();
      // Remove the param from the URL so it doesn't persist on refresh
      searchParams.delete('highlight');
      setSearchParams(searchParams, { replace: true });
      // Clear the highlight after the animation plays
      const timer = setTimeout(() => setHighlightId(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [searchParams, setSearchParams, refetch]);

  const handleShowVersions = async (dataset: Dataset) => {
    setVersionDataset(dataset);
    setLoadingVersions(true);
    try {
      const response = await api.getDatasetVersions(dataset.id);
      setVersionHistory((response.data ?? []).map((d: any) => transformDataset(d)));
    } catch {
      setVersionHistory([]);
      toast({
        title: 'Version history unavailable',
        description: 'Could not load version history for this dataset.',
        variant: 'destructive',
      });
    } finally {
      setLoadingVersions(false);
    }
  };

  const handleView = (dataset: Dataset) => {
    navigate(`/datasets/${dataset.id}`);
  };

  const handleDownload = async (dataset: Dataset) => {
    setDownloadingId(dataset.id);
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
          : status === 400
            ? serverDetail || 'This dataset is not available for download.'
            : 'Failed to download dataset. The server may be unavailable.',
        variant: 'destructive',
      });
    } finally {
      setDownloadingId(null);
    }
  };

  const handleCopyId = (dataset: Dataset) => {
    navigator.clipboard.writeText(dataset.id).then(() => {
      toast({
        title: 'Copied',
        description: `Dataset ID "${dataset.id}" copied to clipboard.`,
      });
    }).catch(() => {
      toast({
        title: 'Copy failed',
        description: 'Could not copy dataset ID to clipboard.',
        variant: 'destructive',
      });
    });
  };

  const handleDeleteClick = (dataset: Dataset) => {
    setDatasetToDelete(dataset);
  };

  const handleDeleteConfirm = async () => {
    if (!datasetToDelete) return;
    try {
      await deleteDataset.mutateAsync(datasetToDelete.id);
      toast({
        title: 'Dataset Deleted',
        description: `"${datasetToDelete.name}" has been permanently deleted.`,
      });
    } catch (err: unknown) {
      const detail = (err as any)?.response?.data?.detail;
      toast({
        title: 'Delete Failed',
        description: detail || 'Failed to delete dataset. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setDatasetToDelete(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
        <div>
          <h1 className="text-xl sm:text-3xl font-bold tracking-tight">My Datasets</h1>
          <p className="text-muted-foreground mt-1">
            Manage your generated and saved datasets
          </p>
        </div>
        <Link to="/datasets/generate" className="w-full sm:w-auto">
          <Button className="gap-2 w-full sm:w-auto">
            <Plus className="h-4 w-4" />
            Generate New
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Datasets</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{userDatasets.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Objects</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {userDatasets.filter((d) => d.status !== 'failed').reduce((acc, d) => acc + d.objectCount, 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Storage Used</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {formatFileSize(userDatasets.reduce((acc, d) => acc + d.sizeBytes, 0))}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Datasets Table */}
      <Card>
        <CardHeader>
          <CardTitle>Your Datasets</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>Unable to load datasets</p>
            </div>
          ) : userDatasets.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>No datasets yet. Generate one to get started.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Name</TableHead>
                  <TableHead scope="col">Status</TableHead>
                  <TableHead scope="col">Version</TableHead>
                  <TableHead scope="col">Regime</TableHead>
                  <TableHead scope="col">Tier</TableHead>
                  <TableHead scope="col">Objects</TableHead>
                  <TableHead scope="col">Size</TableHead>
                  <TableHead scope="col">Created</TableHead>
                  <TableHead scope="col" className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {userDatasets.map((dataset) => (
                  <TableRow
                    key={dataset.id}
                    className={cn(
                      dataset.status === 'failed' && 'opacity-70',
                      highlightId === dataset.id && 'animate-highlight-pulse'
                    )}
                  >
                    <TableCell className="font-medium">{dataset.name}</TableCell>
                    <TableCell>
                      {dataset.status === 'failed' ? (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Badge variant="destructive" className="gap-1 cursor-help">
                                <AlertCircle className="h-3 w-3" />
                                Failed
                              </Badge>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                              <p>{dataset.errorMessage || 'Dataset generation failed.'}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      ) : dataset.status === 'generating' ? (
                        <Badge variant="secondary" className="gap-1">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Generating
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-green-600 border-green-600/30">
                          Available
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono">
                        v{dataset.version ?? 1}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={dataset.regime === 'LEO' ? 'leo' : dataset.regime === 'MEO' ? 'meo' : dataset.regime === 'GEO' ? 'geo' : 'heo'}>
                        {dataset.regime}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={dataset.tier === 'T1' ? 'tier1' : dataset.tier === 'T2' ? 'tier2' : dataset.tier === 'T3' ? 'tier3' : 'tier4'}>
                        {dataset.tier}
                      </Badge>
                    </TableCell>
                    <TableCell>{dataset.status === 'failed' ? '-' : dataset.objectCount}</TableCell>
                    <TableCell>{dataset.status === 'failed' ? '-' : dataset.sizeBytes > 0 ? formatFileSize(dataset.sizeBytes) : '-'}</TableCell>
                    <TableCell>{formatDate(dataset.createdAt)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          title={dataset.status === 'failed' ? 'Dataset generation failed' : 'View dataset'}
                          onClick={() => handleView(dataset)}
                          disabled={dataset.status === 'failed'}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Version history"
                          onClick={() => handleShowVersions(dataset)}
                        >
                          <History className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          title={dataset.status === 'failed' ? 'Dataset generation failed' : 'Download dataset'}
                          onClick={() => handleDownload(dataset)}
                          disabled={downloadingId === dataset.id || dataset.status === 'failed'}
                        >
                          {downloadingId === dataset.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Download className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Copy dataset ID"
                          onClick={() => handleCopyId(dataset)}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                        {isAdmin && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive"
                            onClick={() => handleDeleteClick(dataset)}
                            disabled={deleteDataset.isPending}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Version History Dialog */}
      <Dialog open={!!versionDataset} onOpenChange={() => { setVersionDataset(null); setVersionHistory(null); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Version History: {versionDataset?.name}</DialogTitle>
            <DialogDescription>
              View all versions of this dataset to compare old and new generations.
            </DialogDescription>
          </DialogHeader>
          {loadingVersions ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : versionHistory && versionHistory.length > 0 ? (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {versionHistory.map((v) => (
                <div
                  key={v.id}
                  className={`flex items-center justify-between rounded-lg border p-3 ${v.id === versionDataset?.id ? 'border-primary bg-primary/5' : ''}`}
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="font-mono">v{v.version ?? 1}</Badge>
                      <span className="font-medium text-sm">{v.name}</span>
                      {v.id === versionDataset?.id && (
                        <Badge variant="secondary" className="text-xs">current</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {v.objectCount} objects &middot; {v.observationCount} obs &middot; {formatDate(v.createdAt)}
                    </p>
                  </div>
                  <Link to={`/datasets/${v.id}`}>
                    <Button variant="ghost" size="sm">
                      <Eye className="h-3 w-3 mr-1" /> View
                    </Button>
                  </Link>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-4 text-muted-foreground text-sm">
              No other versions found for this dataset.
            </p>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!datasetToDelete} onOpenChange={() => setDatasetToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Dataset</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{datasetToDelete?.name}"? This action cannot be undone
              and will permanently remove the dataset and all associated observations.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
            <Button variant="outline" onClick={() => setDatasetToDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteDataset.isPending}
            >
              {deleteDataset.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
