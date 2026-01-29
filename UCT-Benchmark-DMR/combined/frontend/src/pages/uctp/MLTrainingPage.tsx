import { useState } from 'react';
import { Brain, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUCTPModels, useTrainUCTPModel } from '@/hooks/useUCTPModels';
import { ModelCard } from '@/components/uctp/ModelCard';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { UCTPModelType } from '@/types/uctp';

export function MLTrainingPage() {
  const { data: models } = useUCTPModels();
  const trainModel = useTrainUCTPModel();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [modelType, setModelType] = useState<UCTPModelType>('clustering_nn');
  const [description, setDescription] = useState('');
  const [selectedDatasets, setSelectedDatasets] = useState<number[]>([]);
  const [epochs, setEpochs] = useState(50);
  const [learningRate, setLearningRate] = useState(0.001);

  const { data: datasets } = useQuery({
    queryKey: ['datasets-for-training'],
    queryFn: async () => {
      const res = await api.getDatasets({ status: 'available' });
      return res.data as { id: string; name: string }[];
    },
    staleTime: 1000 * 60,
  });

  const handleTrain = () => {
    if (!name || selectedDatasets.length === 0) return;
    trainModel.mutate({
      name,
      model_type: modelType,
      description,
      training_dataset_ids: selectedDatasets,
      training_config: { epochs, learning_rate: learningRate, batch_size: 32 },
    });
    setShowForm(false);
    setName('');
    setDescription('');
    setSelectedDatasets([]);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-stellar-purple text-sm font-medium mb-1">
            <Brain className="h-4 w-4" />
            ML Training Studio
          </div>
          <h1 className="text-3xl font-display font-bold tracking-tight">Train & Manage Models</h1>
          <p className="text-muted-foreground mt-1">Train neural network models for enhanced UCTP pipeline performance.</p>
        </div>
        <Button
          onClick={() => setShowForm(!showForm)}
          className="gap-2 bg-gradient-to-r from-stellar-purple to-cosmic-blue hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          Train New Model
        </Button>
      </div>

      {/* Training Form */}
      {showForm && (
        <div className="rounded-xl border border-stellar-purple/30 bg-card p-6 space-y-4">
          <h2 className="text-sm font-semibold">New Training Job</h2>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Model Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-stellar-purple/50 focus:outline-none"
                placeholder="e.g., ClusterNet-v1"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Model Type</label>
              <select
                value={modelType}
                onChange={(e) => setModelType(e.target.value as UCTPModelType)}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-stellar-purple/50 focus:outline-none"
              >
                <option value="clustering_nn">Clustering Neural Network</option>
                <option value="propagation_ml">ML-Enhanced Propagation</option>
                <option value="hybrid">Hybrid Model</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-stellar-purple/50 focus:outline-none"
              placeholder="Brief description..."
            />
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Training Datasets</label>
            <div className="flex flex-wrap gap-2">
              {datasets?.map((ds) => {
                const id = parseInt(ds.id);
                const isSelected = selectedDatasets.includes(id);
                return (
                  <button
                    key={ds.id}
                    onClick={() => setSelectedDatasets(
                      isSelected ? selectedDatasets.filter((d) => d !== id) : [...selectedDatasets, id]
                    )}
                    className={`rounded-lg border px-3 py-1.5 text-xs transition-all ${
                      isSelected
                        ? 'border-stellar-purple/50 bg-stellar-purple/10 text-stellar-purple'
                        : 'border-white/10 bg-white/5 hover:border-white/20'
                    }`}
                  >
                    {ds.name}
                  </button>
                );
              })}
              {(!datasets || datasets.length === 0) && (
                <span className="text-xs text-muted-foreground">No available datasets</span>
              )}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Epochs</label>
              <input
                type="number"
                value={epochs}
                onChange={(e) => setEpochs(parseInt(e.target.value) || 50)}
                min={1}
                max={500}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-stellar-purple/50 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Learning Rate</label>
              <input
                type="number"
                value={learningRate}
                onChange={(e) => setLearningRate(parseFloat(e.target.value) || 0.001)}
                min={0.00001}
                max={1}
                step={0.0001}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-stellar-purple/50 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex gap-3">
            <Button
              onClick={handleTrain}
              disabled={!name || selectedDatasets.length === 0 || trainModel.isPending}
              className="bg-gradient-to-r from-stellar-purple to-cosmic-blue hover:opacity-90"
            >
              {trainModel.isPending ? 'Starting...' : 'Start Training'}
            </Button>
            <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </div>
      )}

      {/* Model List */}
      {models && models.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {models.map((model) => (
            <ModelCard key={model.id} model={model} />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
          <Brain className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">No trained models yet.</p>
          <p className="text-xs text-muted-foreground mt-1">Click "Train New Model" to get started.</p>
        </div>
      )}
    </div>
  );
}
