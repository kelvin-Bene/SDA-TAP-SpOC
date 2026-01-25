import { useState } from 'react';
import { Link } from 'react-router-dom';
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
import { Plus, Download, Trash2, Copy, Eye, Loader2 } from 'lucide-react';
import { formatDate, formatFileSize } from '@/lib/utils';
import { useDatasets, useDeleteDataset } from '@/hooks/useDatasets';
import type { Dataset } from '@/types';

export function MyDatasetsPage() {
  const { data: datasets, isLoading, error } = useDatasets();
  const deleteDataset = useDeleteDataset();
  const [datasetToDelete, setDatasetToDelete] = useState<Dataset | null>(null);
  const userDatasets = datasets ?? [];

  const handleDeleteClick = (dataset: Dataset) => {
    setDatasetToDelete(dataset);
  };

  const handleDeleteConfirm = () => {
    if (datasetToDelete) {
      deleteDataset.mutate(datasetToDelete.id);
      setDatasetToDelete(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My Datasets</h1>
          <p className="text-muted-foreground mt-1">
            Manage your generated and saved datasets
          </p>
        </div>
        <Link to="/datasets/generate">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Generate New
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
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
              {userDatasets.reduce((acc, d) => acc + d.objectCount, 0)}
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
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Regime</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead>Objects</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {userDatasets.map((dataset) => (
                  <TableRow key={dataset.id}>
                    <TableCell className="font-medium">{dataset.name}</TableCell>
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
                    <TableCell>{dataset.objectCount}</TableCell>
                    <TableCell>{dataset.sizeBytes > 0 ? formatFileSize(dataset.sizeBytes) : '-'}</TableCell>
                    <TableCell>{formatDate(dataset.createdAt)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon">
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon">
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon">
                          <Copy className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive"
                          onClick={() => handleDeleteClick(dataset)}
                          disabled={deleteDataset.isPending}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

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
          <DialogFooter>
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
