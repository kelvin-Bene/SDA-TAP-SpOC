import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { AlgorithmOptions, UCTPRunCreate } from '@/types/uctp';

interface AlgorithmConfigPanelProps {
  datasetId: number;
  onSubmit: (config: UCTPRunCreate) => void;
  isSubmitting?: boolean;
}

export function AlgorithmConfigPanel({ datasetId, onSubmit, isSubmitting = false }: AlgorithmConfigPanelProps) {
  const { data: options } = useQuery({
    queryKey: ['uctp-algorithm-options'],
    queryFn: async () => {
      const res = await api.getAlgorithmOptions();
      return res.data as AlgorithmOptions;
    },
    staleTime: 1000 * 60 * 5,
  });

  const [algorithmName, setAlgorithmName] = useState('Custom Pipeline');
  const [clusteringMethod, setClusteringMethod] = useState('angular_dbscan');
  const [iodMethod, setIodMethod] = useState('gauss');
  const [refinementMethod, setRefinementMethod] = useState('none');
  const [epsDeg, setEpsDeg] = useState(0.5);
  const [minSamples, setMinSamples] = useState(3);

  const handleSubmit = () => {
    onSubmit({
      dataset_id: datasetId,
      algorithm_name: algorithmName,
      clustering: {
        method: clusteringMethod as UCTPRunCreate['clustering']['method'],
        eps_deg: epsDeg,
        min_samples: minSamples,
      },
      iod: {
        method: iodMethod as UCTPRunCreate['iod']['method'],
      },
      refinement: {
        method: refinementMethod as UCTPRunCreate['refinement']['method'],
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Algorithm Name */}
      <div>
        <label className="text-sm font-medium text-muted-foreground mb-1.5 block">Algorithm Name</label>
        <input
          type="text"
          value={algorithmName}
          onChange={(e) => setAlgorithmName(e.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-cosmic-cyan/50 focus:outline-none"
          placeholder="Name for this configuration..."
        />
      </div>

      {/* Clustering Method */}
      <div>
        <label className="text-sm font-medium text-muted-foreground mb-1.5 block">Clustering Method</label>
        <div className="grid grid-cols-1 gap-2">
          {(options?.clustering_methods || [
            { value: 'angular_dbscan', label: 'Angular DBSCAN', description: 'DBSCAN on angular features' },
            { value: 'stonesoup_mht', label: 'Stone Soup MHT', description: 'Multi-hypothesis tracking' },
            { value: 'stonesoup_gnn', label: 'Stone Soup GNN', description: 'Global nearest neighbor' },
          ]).map((opt) => (
            <button
              key={opt.value}
              onClick={() => setClusteringMethod(opt.value)}
              className={cn(
                'text-left rounded-lg border p-3 transition-all',
                clusteringMethod === opt.value
                  ? 'border-cosmic-cyan/50 bg-cosmic-cyan/10'
                  : 'border-white/10 bg-white/5 hover:border-white/20'
              )}
            >
              <p className="text-sm font-medium">{opt.label}</p>
              <p className="text-xs text-muted-foreground">{opt.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* DBSCAN Parameters */}
      {clusteringMethod === 'angular_dbscan' && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Epsilon (deg)</label>
            <input
              type="number"
              value={epsDeg}
              onChange={(e) => setEpsDeg(parseFloat(e.target.value) || 0.5)}
              min={0.01}
              max={10}
              step={0.1}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-cosmic-cyan/50 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Min Samples</label>
            <input
              type="number"
              value={minSamples}
              onChange={(e) => setMinSamples(parseInt(e.target.value) || 3)}
              min={2}
              max={50}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-cosmic-cyan/50 focus:outline-none"
            />
          </div>
        </div>
      )}

      {/* IOD Method */}
      <div>
        <label className="text-sm font-medium text-muted-foreground mb-1.5 block">IOD Method</label>
        <div className="grid grid-cols-1 gap-2">
          {(options?.iod_methods || [
            { value: 'gauss', label: 'Gauss IOD', description: 'Classical Gauss angles-only IOD' },
            { value: 'orbdetpy_laplace', label: 'orbdetpy Laplace', description: 'Laplace IOD (requires orbdetpy)' },
            { value: 'orekit_gooding', label: 'Orekit Gooding', description: 'Gooding IOD (requires Orekit)' },
          ]).map((opt) => (
            <button
              key={opt.value}
              onClick={() => setIodMethod(opt.value)}
              className={cn(
                'text-left rounded-lg border p-3 transition-all',
                iodMethod === opt.value
                  ? 'border-stellar-purple/50 bg-stellar-purple/10'
                  : 'border-white/10 bg-white/5 hover:border-white/20'
              )}
            >
              <p className="text-sm font-medium">{opt.label}</p>
              <p className="text-xs text-muted-foreground">{opt.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Refinement Method */}
      <div>
        <label className="text-sm font-medium text-muted-foreground mb-1.5 block">Refinement Method</label>
        <div className="grid grid-cols-2 gap-2">
          {(options?.refinement_methods || [
            { value: 'none', label: 'None', description: 'No refinement' },
            { value: 'batch_least_squares', label: 'Batch LS', description: 'Batch least-squares' },
            { value: 'ekf', label: 'EKF', description: 'Extended Kalman Filter' },
            { value: 'ukf', label: 'UKF', description: 'Unscented Kalman Filter' },
          ]).map((opt) => (
            <button
              key={opt.value}
              onClick={() => setRefinementMethod(opt.value)}
              className={cn(
                'text-left rounded-lg border p-2.5 transition-all',
                refinementMethod === opt.value
                  ? 'border-aurora-green/50 bg-aurora-green/10'
                  : 'border-white/10 bg-white/5 hover:border-white/20'
              )}
            >
              <p className="text-xs font-medium">{opt.label}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Submit */}
      <Button
        onClick={handleSubmit}
        disabled={isSubmitting || !datasetId}
        className="w-full bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity"
      >
        {isSubmitting ? 'Launching...' : 'Run Pipeline'}
      </Button>
    </div>
  );
}
