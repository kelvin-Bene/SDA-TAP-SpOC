import { useInView } from '@/hooks/useInView';
import { SectionLabel } from './components/SectionLabel';
import { TierCard } from './components/TierCard';

const TIERS = [
  {
    tier: 'T1',
    title: 'Light Downsampling',
    description: 'Minimal data reduction. High-fidelity observations with controlled sparsity.',
    color: 'green',
  },
  {
    tier: 'T2',
    title: 'Heavy Downsampling',
    description: 'Aggressive temporal thinning. Tests algorithm robustness under data scarcity.',
    color: 'blue',
  },
  {
    tier: 'T3',
    title: 'Observation Simulation',
    description: 'Synthetic observations generated from truth ephemerides with realistic noise models.',
    color: 'amber',
  },
  {
    tier: 'T4',
    title: 'Object Simulation',
    description: 'Fully synthetic object populations with configurable orbital characteristics.',
    color: 'red',
  },
  {
    tier: 'T5',
    title: 'Impossible Criteria',
    description: 'Adversarial scenarios designed to stress-test algorithm failure boundaries.',
    color: 'purple',
  },
];

export function TiersSection() {
  const { ref, isInView } = useInView();

  return (
    <section className="py-24 sm:py-32 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" ref={ref}>
        <div className="text-center mb-16">
          <SectionLabel>Processing Taxonomy</SectionLabel>
          <h2 className="font-display font-bold text-3xl sm:text-4xl mt-6 mb-4">Data Tiers</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Five tiers of increasing processing complexity, from light downsampling to adversarial scenarios.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {TIERS.map((tier, i) => (
            <TierCard key={tier.tier} {...tier} delay={i * 100} isInView={isInView} />
          ))}
        </div>
      </div>
    </section>
  );
}
