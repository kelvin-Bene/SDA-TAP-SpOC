import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Plus, Download, Trash2, Copy, Eye } from 'lucide-react';
import { formatDate, formatFileSize } from '@/lib/utils';

const mockUserDatasets = [
  {
    id: '1',
    name: 'LEO-T2-Custom-001',
    regime: 'LEO',
    tier: 'T2',
    createdAt: '2026-01-18T10:30:00Z',
    objectCount: 45,
    observationCount: 8234,
    sizeBytes: 2.1 * 1024 * 1024,
    status: 'ready',
  },
  {
    id: '2',
    name: 'MEO-T3-Challenging',
    regime: 'MEO',
    tier: 'T3',
    createdAt: '2026-01-17T14:00:00Z',
    objectCount: 32,
    observationCount: 5678,
    sizeBytes: 1.4 * 1024 * 1024,
    status: 'ready',
  },
  {
    id: '3',
    name: 'GEO-T1-Standard',
    regime: 'GEO',
    tier: 'T1',
    createdAt: '2026-01-16T09:00:00Z',
    objectCount: 28,
    observationCount: 7890,
    sizeBytes: 1.8 * 1024 * 1024,
    status: 'ready',
  },
  {
    id: '4',
    name: 'LEO-T4-Synthetic',
    regime: 'LEO',
    tier: 'T4',
    createdAt: '2026-01-19T08:00:00Z',
    objectCount: 60,
    observationCount: 0,
    sizeBytes: 0,
    status: 'generating',
  },
];

export function MyDatasetsPage() {
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
            <p className="text-2xl font-bold">{mockUserDatasets.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Objects</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {mockUserDatasets.reduce((acc, d) => acc + d.objectCount, 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Storage Used</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {formatFileSize(mockUserDatasets.reduce((acc, d) => acc + d.sizeBytes, 0))}
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
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Regime</TableHead>
                <TableHead>Tier</TableHead>
                <TableHead>Objects</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockUserDatasets.map((dataset) => (
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
                  <TableCell>
                    {dataset.status === 'ready' ? (
                      <Badge variant="success">Ready</Badge>
                    ) : (
                      <Badge variant="processing">Generating</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" disabled={dataset.status !== 'ready'}>
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" disabled={dataset.status !== 'ready'}>
                        <Download className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" disabled={dataset.status !== 'ready'}>
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="text-destructive">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
