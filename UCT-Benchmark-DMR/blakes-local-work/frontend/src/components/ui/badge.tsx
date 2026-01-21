import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
        secondary: 'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
        destructive: 'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80',
        outline: 'text-foreground',
        success: 'border-transparent bg-green-500 text-white hover:bg-green-500/80',
        warning: 'border-transparent bg-yellow-500 text-white hover:bg-yellow-500/80',
        processing: 'border-transparent bg-blue-500 text-white hover:bg-blue-500/80',
        // Orbital regime badges
        leo: 'border-transparent bg-orbital-leo text-white',
        meo: 'border-transparent bg-orbital-meo text-white',
        geo: 'border-transparent bg-orbital-geo text-white',
        heo: 'border-transparent bg-orbital-heo text-white',
        // Tier badges
        tier1: 'border-transparent bg-tier-1 text-white',
        tier2: 'border-transparent bg-tier-2 text-white',
        tier3: 'border-transparent bg-tier-3 text-white',
        tier4: 'border-transparent bg-tier-4 text-white',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
