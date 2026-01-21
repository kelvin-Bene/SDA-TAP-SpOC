import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
  className?: string;
}

export function StatCard({
  title,
  value,
  subtitle,
  change,
  changeLabel,
  icon,
  className,
}: StatCardProps) {
  const getChangeColor = () => {
    if (!change) return 'text-muted-foreground';
    return change > 0 ? 'text-green-500' : change < 0 ? 'text-red-500' : 'text-muted-foreground';
  };

  const getChangeIcon = () => {
    if (!change) return <Minus className="h-3 w-3" />;
    return change > 0 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />;
  };

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              {title}
            </p>
            <p className="text-3xl font-bold tracking-tight">{value}</p>
            {(change !== undefined || subtitle) && (
              <div className="flex items-center gap-2 text-sm">
                {change !== undefined && (
                  <span className={cn('flex items-center gap-1', getChangeColor())}>
                    {getChangeIcon()}
                    {Math.abs(change)}
                    {changeLabel && <span className="text-muted-foreground ml-1">{changeLabel}</span>}
                  </span>
                )}
                {subtitle && !change && (
                  <span className="text-muted-foreground">{subtitle}</span>
                )}
              </div>
            )}
          </div>
          {icon && (
            <div className="rounded-full bg-primary/10 p-3 text-primary">
              {icon}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
