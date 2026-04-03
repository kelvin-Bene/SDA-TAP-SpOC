import { type LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  accentColor: string;
  delay: number;
  isInView: boolean;
}

const boxMap: Record<string, string> = {
  cyan: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20 group-hover:shadow-glow-cyan',
  blue: 'text-blue-400 bg-blue-400/10 border-blue-400/20 group-hover:shadow-glow-blue',
  purple: 'text-purple-400 bg-purple-400/10 border-purple-400/20 group-hover:shadow-glow-purple',
  green: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  amber: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
};

const iconMap: Record<string, string> = {
  cyan: 'text-cyan-400',
  blue: 'text-blue-400',
  purple: 'text-purple-400',
  green: 'text-emerald-400',
  amber: 'text-amber-400',
};

export function FeatureCard({ icon: Icon, title, description, accentColor, delay, isInView }: FeatureCardProps) {
  const boxColors = boxMap[accentColor] || boxMap.cyan;
  const iconColor = iconMap[accentColor] || iconMap.cyan;

  return (
    <Card
      className={cn(
        'group glass border-white/10 card-hover transition-all duration-700',
        isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      )}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <CardContent className="p-6 flex flex-col gap-4">
        <div className={cn('w-12 h-12 rounded-lg border flex items-center justify-center transition-shadow', boxColors)}>
          <Icon className={cn('h-6 w-6', iconColor)} />
        </div>
        <div>
          <h3 className="font-display font-semibold text-lg mb-1">{title}</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
        </div>
      </CardContent>
    </Card>
  );
}
