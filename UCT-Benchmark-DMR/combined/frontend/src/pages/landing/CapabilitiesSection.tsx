import {
  LayoutDashboard, Database, Plus, Upload, BarChart3, Trophy,
} from 'lucide-react';
import { useInView } from '@/hooks/useInView';
import { SectionLabel } from './components/SectionLabel';
import { FeatureCard } from './components/FeatureCard';

const CAPABILITIES = [
  {
    icon: LayoutDashboard,
    title: 'Dashboard',
    description: 'Real-time stats, submission tracking, leaderboard snapshots.',
    accentColor: 'cyan',
  },
  {
    icon: Database,
    title: 'Dataset Browser',
    description: 'Browse datasets filtered by regime, tier, and sensor type.',
    accentColor: 'blue',
  },
  {
    icon: Plus,
    title: 'Dataset Generator',
    description: 'Multi-step configuration with 16-character dataset codes.',
    accentColor: 'cyan',
  },
  {
    icon: Upload,
    title: 'Submission Pipeline',
    description: 'Upload results with automated 5-step validation.',
    accentColor: 'purple',
  },
  {
    icon: BarChart3,
    title: 'Evaluation Results',
    description: 'Binary metrics, state accuracy, residual analysis.',
    accentColor: 'green',
  },
  {
    icon: Trophy,
    title: 'Leaderboard',
    description: 'Rankings by regime and tier with performance trends.',
    accentColor: 'amber',
  },
];

export function CapabilitiesSection() {
  const { ref, isInView } = useInView();

  return (
    <section id="capabilities" className="py-16 sm:py-24 md:py-32 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" ref={ref}>
        <div className="text-center mb-10 sm:mb-16">
          <SectionLabel>Operational Capabilities</SectionLabel>
          <h2 className="font-display font-bold text-3xl sm:text-4xl mt-6 mb-4">
            Platform Capabilities
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            End-to-end tooling for benchmark dataset management, submission processing, and performance evaluation.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {CAPABILITIES.map((cap, i) => (
            <FeatureCard key={cap.title} {...cap} delay={i * 100} isInView={isInView} />
          ))}
        </div>
      </div>
    </section>
  );
}
