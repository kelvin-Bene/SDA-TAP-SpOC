import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface TierCardProps {
  tier: string;
  title: string;
  description: string;
  color: string;
  delay: number;
  isInView: boolean;
}

const colorMap: Record<string, { badge: string; border: string; glow: string }> = {
  green: {
    badge: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    border: 'border-emerald-500/20',
    glow: 'hover:border-emerald-500/40',
  },
  blue: {
    badge: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    border: 'border-blue-500/20',
    glow: 'hover:border-blue-500/40',
  },
  amber: {
    badge: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    border: 'border-amber-500/20',
    glow: 'hover:border-amber-500/40',
  },
  red: {
    badge: 'bg-red-500/20 text-red-400 border-red-500/30',
    border: 'border-red-500/20',
    glow: 'hover:border-red-500/40',
  },
  purple: {
    badge: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    border: 'border-purple-500/20',
    glow: 'hover:border-purple-500/40',
  },
};

export function TierCard({ tier, title, description, color, delay, isInView }: TierCardProps) {
  const colors = colorMap[color] || colorMap.green;

  return (
    <Card
      className={cn(
        'glass border-white/10 transition-all duration-700 card-hover',
        colors.glow,
        isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      )}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <CardContent className="p-5 flex flex-col gap-3">
        <Badge variant="outline" className={cn('w-fit text-xs font-mono', colors.badge)}>
          {tier}
        </Badge>
        <h3 className="font-display font-semibold text-base">{title}</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
      </CardContent>
    </Card>
  );
}
