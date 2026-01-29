import { useState } from 'react';
import { Brain, Plus, Sparkles, Cpu, Layers, Settings2, Database, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUCTPModels, useTrainUCTPModel } from '@/hooks/useUCTPModels';
import { ModelCard } from '@/components/uctp/ModelCard';
import { InfoPopover, StepExplainer } from '@/components/ui/info-popover';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { UCTPModelType } from '@/types/uctp';

const MODEL_TYPE_META: Record<
  UCTPModelType,
  { label: string; icon: typeof Brain; color: string; bg: string; border: string }
> = {
  clustering_nn: {
    label: 'Clustering NN',
    icon: Sparkles,
    color: 'text-stellar-purple',
    bg: 'bg-stellar-purple/10',
    border: 'border-stellar-purple/30',
  },
  propagation_ml: {
    label: 'Propagation ML',
    icon: Cpu,
    color: 'text-cosmic-cyan',
    bg: 'bg-cosmic-cyan/10',
    border: 'border-cosmic-cyan/30',
  },
  hybrid: {
    label: 'Hybrid',
    icon: Layers,
    color: 'text-aurora-green',
    bg: 'bg-aurora-green/10',
    border: 'border-aurora-green/30',
  },
};

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
      {/* ── Gradient Hero Header ── */}
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-stellar-purple/5 via-transparent to-cosmic-cyan/5 p-6 sm:p-8">
        <div className="absolute top-0 right-0 w-72 h-72 bg-stellar-purple/8 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="relative z-10 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-stellar-purple text-sm font-medium mb-2">
              <Brain className="h-4 w-4" />
              ML Training Studio
            </div>
            <h1 className="text-3xl font-display font-bold tracking-tight">
              Train <span className="text-gradient-cosmic">ML Models</span>
            </h1>
            <p className="text-muted-foreground mt-2 max-w-2xl">
              Train machine learning models to enhance UCT processing accuracy for clustering, propagation, and orbit refinement.
            </p>
          </div>
          <Button
            onClick={() => setShowForm(!showForm)}
            className="gap-2 bg-gradient-to-r from-stellar-purple to-cosmic-blue hover:opacity-90 shrink-0 self-start"
          >
            <Plus className="h-4 w-4" />
            Train New Model
          </Button>
        </div>
      </div>

      {/* ── Step Explainer ── */}
      <StepExplainer
        title="ML Training Workflow"
        description="Train models to improve your algorithm's performance on specific dataset types."
        tips={[
          'Start with a Clustering NN model trained on your target orbital regime',
          'Use multiple datasets for training to improve generalization',
          'Monitor training loss to detect overfitting',
          'Deploy trained models in the Algorithm Workbench to compare performance',
        ]}
        variant="concept"
        defaultOpen={false}
      />

      {/* ── Training Form ── */}
      {showForm && (
        <div className="rounded-2xl border border-stellar-purple/20 bg-card/80 backdrop-blur-sm overflow-hidden">
          {/* Form Header */}
          <div className="border-b border-white/5 bg-gradient-to-r from-stellar-purple/5 to-transparent px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-stellar-purple/10">
                <Play className="h-4 w-4 text-stellar-purple" />
              </div>
              <div>
                <h2 className="text-sm font-semibold">New Training Job</h2>
                <p className="text-xs text-muted-foreground">Configure and launch a model training run</p>
              </div>
            </div>
          </div>

          <div className="p-6 space-y-6">
            {/* Section 1: Model Identity */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                <Brain className="h-3.5 w-3.5" />
                Model Identity
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground block">
                    Model Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-stellar-purple/50 focus:outline-none focus:ring-1 focus:ring-stellar-purple/20 transition-all"
                    placeholder="e.g., ClusterNet-v1"
                  />
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center gap-1.5">
                    <label className="text-xs font-medium text-muted-foreground">
                      Model Type
                    </label>
                    <InfoPopover
                      title="Model Types"
                      description="Choose the type of ML model based on which pipeline stage you want to improve."
                      details={[
                        'Clustering NN -- Best for improving observation-to-track association',
                        'Propagation ML -- Best for enhancing orbit prediction accuracy',
                        'Hybrid -- Combines ML clustering with classical orbit determination',
                      ]}
                      variant="info"
                      size="sm"
                    />
                  </div>
                  <select
                    value={modelType}
                    onChange={(e) => setModelType(e.target.value as UCTPModelType)}
                    className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-stellar-purple/50 focus:outline-none focus:ring-1 focus:ring-stellar-purple/20 transition-all"
                  >
                    <option value="clustering_nn">Clustering Neural Network</option>
                    <option value="propagation_ml">ML-Enhanced Propagation</option>
                    <option value="hybrid">Hybrid Model</option>
                  </select>
                </div>
              </div>

              {/* Model Type Info Cards */}
              <div className="grid gap-3 sm:grid-cols-3">
                {(Object.entries(MODEL_TYPE_META) as [UCTPModelType, typeof MODEL_TYPE_META[UCTPModelType]][]).map(
                  ([key, meta]) => {
                    const Icon = meta.icon;
                    const isActive = modelType === key;
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setModelType(key)}
                        className={`relative flex items-center gap-3 rounded-xl border p-3 text-left transition-all duration-200 ${
                          isActive
                            ? `${meta.border} ${meta.bg} ring-1 ring-inset ${meta.border}`
                            : 'border-white/5 bg-white/[0.02] hover:border-white/10 hover:bg-white/[0.04]'
                        }`}
                      >
                        <div className={`p-2 rounded-lg ${meta.bg}`}>
                          <Icon className={`h-4 w-4 ${meta.color}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <span className={`text-xs font-semibold ${isActive ? meta.color : 'text-foreground'}`}>
                            {meta.label}
                          </span>
                          <div className="flex items-center gap-1 mt-0.5">
                            {key === 'clustering_nn' && (
                              <InfoPopover
                                title="Clustering Neural Network"
                                description="Neural network that learns observation-to-track associations. Improves on traditional DBSCAN by learning spatial patterns from training data."
                                details={[
                                  'Learns complex spatial and temporal clustering boundaries',
                                  'Adapts to specific sensor and orbital regime characteristics',
                                  'Typically outperforms hand-tuned DBSCAN parameters after sufficient training',
                                ]}
                                learnMore="Clustering NNs use learned embeddings to compute observation similarity scores. During inference, observations with high similarity are grouped into candidate tracks. The network can handle variable observation densities and sensor-specific noise patterns that are difficult to capture with fixed DBSCAN parameters."
                                variant="concept"
                                size="sm"
                              />
                            )}
                            {key === 'propagation_ml' && (
                              <InfoPopover
                                title="ML-Enhanced Propagation"
                                description="ML-enhanced orbit propagation that learns corrections to analytical models. Accounts for atmospheric drag, solar radiation, and other perturbations."
                                details={[
                                  'Learns residual corrections on top of physics-based propagators',
                                  'Captures hard-to-model perturbations like atmospheric drag variability',
                                  'Reduces propagation errors, especially in LEO regimes',
                                ]}
                                learnMore="Propagation ML models typically use a residual learning approach: a classical propagator (e.g., SGP4 or numerical integrator) provides the baseline prediction, and the ML model learns the systematic error pattern. This physics-informed approach ensures physical plausibility while improving accuracy."
                                variant="concept"
                                size="sm"
                              />
                            )}
                            {key === 'hybrid' && (
                              <InfoPopover
                                title="Hybrid Model"
                                description="Combined approach using ML for initial clustering and classical methods for orbit determination. Best of both worlds."
                                details={[
                                  'ML-driven clustering feeds into classical IOD and OD pipelines',
                                  'Preserves well-understood orbit mechanics while improving association',
                                  'Good starting point when you want ML benefits with interpretable outputs',
                                ]}
                                learnMore="Hybrid models provide a pragmatic middle ground. The ML component handles the combinatorially challenging clustering step where neural networks excel, while classical Gauss/Laplace IOD and batch least-squares refinement handle the orbit determination where physics-based methods are well-established and trustworthy."
                                variant="concept"
                                size="sm"
                              />
                            )}
                          </div>
                        </div>
                        {isActive && (
                          <div className={`absolute top-2 right-2 h-2 w-2 rounded-full ${meta.bg.replace('/10', '')}`} />
                        )}
                      </button>
                    );
                  }
                )}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground block">
                  Description
                </label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-stellar-purple/50 focus:outline-none focus:ring-1 focus:ring-stellar-purple/20 transition-all"
                  placeholder="Brief description of the model's purpose or target regime..."
                />
              </div>
            </div>

            {/* Divider */}
            <div className="border-t border-white/5" />

            {/* Section 2: Training Data */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                <Database className="h-3.5 w-3.5" />
                Training Data
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <label className="text-xs font-medium text-muted-foreground">
                    Select Datasets
                  </label>
                  <InfoPopover
                    title="Training Datasets"
                    description="Select one or more datasets to use for training. Using diverse datasets improves model generalization."
                    details={[
                      'Multiple datasets from different sensors/regimes improve robustness',
                      'Ensure datasets have verified ground-truth labels for supervised learning',
                      'Larger datasets generally produce better models but take longer to train',
                    ]}
                    variant="tip"
                    size="sm"
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  {datasets?.map((ds) => {
                    const id = parseInt(ds.id);
                    const isSelected = selectedDatasets.includes(id);
                    return (
                      <button
                        key={ds.id}
                        onClick={() =>
                          setSelectedDatasets(
                            isSelected
                              ? selectedDatasets.filter((d) => d !== id)
                              : [...selectedDatasets, id]
                          )
                        }
                        className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-all duration-200 ${
                          isSelected
                            ? 'border-stellar-purple/50 bg-stellar-purple/10 text-stellar-purple shadow-sm shadow-stellar-purple/10'
                            : 'border-white/10 bg-white/5 text-muted-foreground hover:border-white/20 hover:bg-white/[0.08]'
                        }`}
                      >
                        {ds.name}
                      </button>
                    );
                  })}
                  {(!datasets || datasets.length === 0) && (
                    <div className="w-full rounded-lg border border-dashed border-white/10 p-4 text-center">
                      <Database className="h-5 w-5 text-muted-foreground mx-auto mb-1.5" />
                      <span className="text-xs text-muted-foreground">No available datasets</span>
                    </div>
                  )}
                </div>
                {selectedDatasets.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {selectedDatasets.length} dataset{selectedDatasets.length !== 1 ? 's' : ''} selected
                  </p>
                )}
              </div>
            </div>

            {/* Divider */}
            <div className="border-t border-white/5" />

            {/* Section 3: Training Parameters */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                <Settings2 className="h-3.5 w-3.5" />
                Training Parameters
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1.5">
                    <label className="text-xs font-medium text-muted-foreground">
                      Epochs
                    </label>
                    <InfoPopover
                      title="Training Epochs"
                      description="Number of complete passes through the training dataset. More epochs = better fitting, but risk of overfitting."
                      details={[
                        'Start with 50 epochs for initial experiments',
                        'Increase to 100-200 for final training runs',
                        'Watch validation loss -- if it starts increasing, the model is overfitting',
                        'Use early stopping in production to automatically find the optimal epoch count',
                      ]}
                      learnMore="Each epoch processes every sample in the dataset once. Early epochs show rapid loss reduction (high learning signal), while later epochs show diminishing returns. Overfitting occurs when the model memorizes training data instead of learning generalizable patterns -- validation loss will diverge from training loss."
                      variant="info"
                      size="sm"
                    />
                  </div>
                  <input
                    type="number"
                    value={epochs}
                    onChange={(e) => setEpochs(parseInt(e.target.value) || 50)}
                    min={1}
                    max={500}
                    className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-mono focus:border-stellar-purple/50 focus:outline-none focus:ring-1 focus:ring-stellar-purple/20 transition-all"
                  />
                  <p className="text-[11px] text-muted-foreground">Range: 1 - 500</p>
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center gap-1.5">
                    <label className="text-xs font-medium text-muted-foreground">
                      Learning Rate
                    </label>
                    <InfoPopover
                      title="Learning Rate"
                      description="Controls how aggressively the model updates weights. Smaller = more stable but slower convergence."
                      details={[
                        '0.001 is a good default for most models (Adam optimizer)',
                        'Try 0.0001 for fine-tuning or if training is unstable',
                        'Too high causes divergence; too low wastes compute time',
                        'Consider using learning rate schedulers for longer training runs',
                      ]}
                      learnMore="The learning rate is arguably the most important hyperparameter. It multiplies the gradient to determine the step size in parameter space. With Adam optimizer (used here), the effective learning rate is adapted per-parameter, but the base rate still sets the overall scale. A common strategy is to start with 0.001 and reduce by 10x if training loss plateaus."
                      variant="info"
                      size="sm"
                    />
                  </div>
                  <input
                    type="number"
                    value={learningRate}
                    onChange={(e) => setLearningRate(parseFloat(e.target.value) || 0.001)}
                    min={0.00001}
                    max={1}
                    step={0.0001}
                    className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-mono focus:border-stellar-purple/50 focus:outline-none focus:ring-1 focus:ring-stellar-purple/20 transition-all"
                  />
                  <p className="text-[11px] text-muted-foreground">Range: 0.00001 - 1.0</p>
                </div>
              </div>
            </div>

            {/* Divider */}
            <div className="border-t border-white/5" />

            {/* Actions */}
            <div className="flex items-center gap-3">
              <Button
                onClick={handleTrain}
                disabled={!name || selectedDatasets.length === 0 || trainModel.isPending}
                className="gap-2 bg-gradient-to-r from-stellar-purple to-cosmic-blue hover:opacity-90 disabled:opacity-50"
              >
                {trainModel.isPending ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Starting Training...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    Start Training
                  </>
                )}
              </Button>
              <Button variant="ghost" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
              {(!name || selectedDatasets.length === 0) && (
                <p className="text-xs text-muted-foreground ml-auto">
                  {!name && selectedDatasets.length === 0
                    ? 'Enter a model name and select at least one dataset'
                    : !name
                      ? 'Enter a model name to continue'
                      : 'Select at least one training dataset'}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Trained Models Grid ── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold tracking-tight">Trained Models</h2>
            {models && models.length > 0 && (
              <span className="rounded-full bg-white/5 border border-white/10 px-2.5 py-0.5 text-xs text-muted-foreground font-medium">
                {models.length}
              </span>
            )}
          </div>
        </div>

        {models && models.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {models.map((model) => (
              <ModelCard key={model.id} model={model} />
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.01] p-12 text-center">
            <div className="mx-auto w-fit p-3 rounded-2xl bg-stellar-purple/5 mb-4">
              <Brain className="h-8 w-8 text-muted-foreground" />
            </div>
            <p className="text-sm font-medium text-muted-foreground">No trained models yet</p>
            <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
              Train your first ML model to enhance UCT processing accuracy. Click "Train New Model" above to get started.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
