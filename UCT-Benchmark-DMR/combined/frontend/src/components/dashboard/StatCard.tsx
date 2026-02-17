import { cn } from '@/lib/utils';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
  className?: string;
  accentColor?: 'cyan' | 'blue' | 'purple' | 'green' | 'orange';
}

const accentStyles = {
  cyan: {
    gradient: 'from-cosmic-cyan/20 to-cosmic-blue/10',
    iconBg: 'from-cosmic-cyan/20 to-cosmic-blue/20',
    iconColor: 'text-cosmic-cyan',
    borderHover: 'hover:border-cosmic-cyan/30',
    glow: 'hover:shadow-glow-cyan',
    topLine: 'from-cosmic-cyan',
  },
  blue: {
    gradient: 'from-cosmic-blue/20 to-stellar-purple/10',
    iconBg: 'from-cosmic-blue/20 to-stellar-purple/20',
    iconColor: 'text-cosmic-blue',
    borderHover: 'hover:border-cosmic-blue/30',
    glow: 'hover:shadow-glow-blue',
    topLine: 'from-cosmic-blue',
  },
  purple: {
    gradient: 'from-stellar-purple/20 to-cosmic-blue/10',
    iconBg: 'from-stellar-purple/20 to-cosmic-blue/20',
    iconColor: 'text-stellar-purple',
    borderHover: 'hover:border-stellar-purple/30',
    glow: 'hover:shadow-glow-purple',
    topLine: 'from-stellar-purple',
  },
  green: {
    gradient: 'from-aurora-green/20 to-cosmic-cyan/10',
    iconBg: 'from-aurora-green/20 to-cosmic-cyan/20',
    iconColor: 'text-aurora-green',
    borderHover: 'hover:border-aurora-green/30',
    glow: 'hover:shadow-[0_0_20px_-5px_hsl(142_76%_45%_/_0.5)]',
    topLine: 'from-aurora-green',
  },
  orange: {
    gradient: 'from-nova-orange/20 to-cosmic-cyan/10',
    iconBg: 'from-nova-orange/20 to-cosmic-cyan/20',
    iconColor: 'text-nova-orange',
    borderHover: 'hover:border-nova-orange/30',
    glow: 'hover:shadow-[0_0_20px_-5px_hsl(25_95%_53%_/_0.5)]',
    topLine: 'from-nova-orange',
  },
};

export function StatCard({
  title,
  value,
  subtitle,
  change,
  changeLabel,
  icon,
  className,
  accentColor = 'cyan',
}: StatCardProps) {
  const styles = accentStyles[accentColor];

  const getChangeColor = () => {
    if (!change) return 'text-muted-foreground';
    return change > 0 ? 'text-aurora-green' : change < 0 ? 'text-red-400' : 'text-muted-foreground';
  };

  const getChangeIcon = () => {
    if (!change) return <Minus className="h-3 w-3" />;
    return change > 0 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />;
  };

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl border border-white/10 bg-card p-6 transition-all duration-300',
        styles.borderHover,
        styles.glow,
        'group',
        className
      )}
    >
      {/* Top accent line */}
      <div
        className={cn(
          'absolute top-0 left-0 right-0 h-px bg-gradient-to-r opacity-0 group-hover:opacity-100 transition-opacity',
          styles.topLine,
          'to-transparent'
        )}
      />

      {/* Background gradient */}
      <div
        className={cn(
          'absolute top-0 right-0 w-32 h-32 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity -translate-y-1/2 translate-x-1/2 bg-gradient-to-br',
          styles.gradient
        )}
      />

      <div className="relative z-10 flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            {title}
          </p>
          <p className="text-3xl font-display font-bold tracking-tight">{value}</p>
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
          <div
            className={cn(
              'rounded-xl p-3 bg-gradient-to-br transition-all duration-300 group-hover:scale-110',
              styles.iconBg,
              styles.iconColor
            )}
          >
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
