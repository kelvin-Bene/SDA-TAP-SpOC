import * as React from 'react';
import { useState } from 'react';
import {
  Info,
  HelpCircle,
  BookOpen,
  ChevronDown,
  ExternalLink,
  Lightbulb,
  AlertTriangle,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/* ------------------------------------------------------------------ */
/*  InfoPopover  --  Educational tooltip / popover for complex topics   */
/* ------------------------------------------------------------------ */

export interface InfoPopoverProps {
  /** Short title shown in the popover header */
  title: string;
  /** Main explanation paragraph */
  description: string;
  /** Optional bullet-point details */
  details?: string[];
  /** Optional "Learn More" expandable section */
  learnMore?: string;
  /** Optional link to documentation */
  docsLink?: string;
  /** Optional link label */
  docsLabel?: string;
  /** Visual variant */
  variant?: 'info' | 'tip' | 'warning' | 'concept';
  /** Size of the trigger icon */
  size?: 'sm' | 'md';
  /** Override trigger icon */
  triggerIcon?: React.ReactNode;
  /** Additional className for the trigger */
  className?: string;
  /** Side to show on (for future positioning) */
  side?: 'top' | 'bottom' | 'left' | 'right';
}

const variantConfig = {
  info: {
    icon: Info,
    borderColor: 'border-cosmic-cyan/30',
    bgColor: 'bg-cosmic-cyan/5',
    headerColor: 'text-cosmic-cyan',
    accentBg: 'bg-cosmic-cyan/10',
    triggerColor: 'text-muted-foreground hover:text-cosmic-cyan',
  },
  tip: {
    icon: Lightbulb,
    borderColor: 'border-aurora-green/30',
    bgColor: 'bg-aurora-green/5',
    headerColor: 'text-aurora-green',
    accentBg: 'bg-aurora-green/10',
    triggerColor: 'text-muted-foreground hover:text-aurora-green',
  },
  warning: {
    icon: AlertTriangle,
    borderColor: 'border-nova-orange/30',
    bgColor: 'bg-nova-orange/5',
    headerColor: 'text-nova-orange',
    accentBg: 'bg-nova-orange/10',
    triggerColor: 'text-muted-foreground hover:text-nova-orange',
  },
  concept: {
    icon: BookOpen,
    borderColor: 'border-stellar-purple/30',
    bgColor: 'bg-stellar-purple/5',
    headerColor: 'text-stellar-purple',
    accentBg: 'bg-stellar-purple/10',
    triggerColor: 'text-muted-foreground hover:text-stellar-purple',
  },
};

export function InfoPopover({
  title,
  description,
  details,
  learnMore,
  docsLink,
  docsLabel,
  variant = 'info',
  size = 'sm',
  triggerIcon,
  className,
}: InfoPopoverProps) {
  const [open, setOpen] = useState(false);
  const [showLearnMore, setShowLearnMore] = useState(false);
  const cfg = variantConfig[variant];
  const TriggerIcon = cfg.icon;
  const iconSize = size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4';

  return (
    <div className={cn('relative inline-flex', className)}>
      {/* Trigger */}
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        onMouseEnter={() => setOpen(true)}
        className={cn(
          'inline-flex items-center justify-center rounded-full transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50',
          cfg.triggerColor,
          size === 'sm' ? 'p-0.5' : 'p-1',
        )}
        aria-label={`Learn about ${title}`}
      >
        {triggerIcon || <TriggerIcon className={iconSize} />}
      </button>

      {/* Popover */}
      {open && (
        <>
          {/* Backdrop (click to close) */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => { setOpen(false); setShowLearnMore(false); }}
          />

          {/* Popover Card */}
          <div
            className={cn(
              'absolute z-50 w-80 rounded-xl border shadow-xl backdrop-blur-xl',
              'animate-in fade-in-0 zoom-in-95 slide-in-from-top-2',
              'duration-200',
              cfg.borderColor,
              'bg-card/95',
              'left-1/2 -translate-x-1/2 top-full mt-2',
            )}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className={cn('flex items-start justify-between gap-2 px-4 pt-4 pb-2')}>
              <div className="flex items-center gap-2">
                <div className={cn('p-1.5 rounded-lg', cfg.accentBg)}>
                  <TriggerIcon className={cn('h-3.5 w-3.5', cfg.headerColor)} />
                </div>
                <h4 className={cn('text-sm font-semibold', cfg.headerColor)}>{title}</h4>
              </div>
              <button
                onClick={() => { setOpen(false); setShowLearnMore(false); }}
                className="text-muted-foreground hover:text-foreground transition-colors p-0.5 rounded"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Body */}
            <div className="px-4 pb-3">
              <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>

              {/* Bullet details */}
              {details && details.length > 0 && (
                <ul className="mt-2.5 space-y-1.5">
                  {details.map((d, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className={cn('mt-1.5 h-1 w-1 rounded-full flex-shrink-0', cfg.accentBg.replace('/10', ''))} />
                      <span>{d}</span>
                    </li>
                  ))}
                </ul>
              )}

              {/* Learn More expandable */}
              {learnMore && (
                <div className="mt-3">
                  <button
                    onClick={() => setShowLearnMore(!showLearnMore)}
                    className={cn(
                      'flex items-center gap-1.5 text-xs font-medium transition-colors',
                      cfg.headerColor,
                    )}
                  >
                    <ChevronDown
                      className={cn(
                        'h-3 w-3 transition-transform duration-200',
                        showLearnMore && 'rotate-180',
                      )}
                    />
                    {showLearnMore ? 'Show less' : 'Learn more'}
                  </button>
                  {showLearnMore && (
                    <div className={cn(
                      'mt-2 p-3 rounded-lg text-xs leading-relaxed text-muted-foreground',
                      cfg.bgColor,
                    )}>
                      {learnMore}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer link */}
            {docsLink && (
              <div className={cn('border-t px-4 py-2.5', cfg.borderColor)}>
                <a
                  href={docsLink}
                  className={cn(
                    'flex items-center gap-1.5 text-xs font-medium transition-colors',
                    cfg.headerColor,
                  )}
                >
                  <ExternalLink className="h-3 w-3" />
                  {docsLabel || 'View Documentation'}
                </a>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ConceptBadge  --  Inline educational chip                           */
/* ------------------------------------------------------------------ */

export interface ConceptBadgeProps {
  label: string;
  explanation: string;
  variant?: 'info' | 'tip' | 'warning' | 'concept';
  className?: string;
}

export function ConceptBadge({ label, explanation, variant = 'concept', className }: ConceptBadgeProps) {
  const [open, setOpen] = useState(false);
  const cfg = variantConfig[variant];

  return (
    <span className={cn('relative inline-flex', className)}>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        className={cn(
          'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium transition-all duration-200 cursor-help',
          cfg.borderColor,
          cfg.bgColor,
          cfg.headerColor,
          'hover:opacity-80',
        )}
      >
        {label}
        <HelpCircle className="h-2.5 w-2.5 opacity-60" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div
            className={cn(
              'absolute z-50 w-64 rounded-lg border shadow-lg backdrop-blur-xl p-3',
              'animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-200',
              cfg.borderColor,
              'bg-card/95',
              'left-1/2 -translate-x-1/2 top-full mt-1',
            )}
            onClick={(e) => e.stopPropagation()}
          >
            <p className={cn('text-xs font-semibold mb-1', cfg.headerColor)}>{label}</p>
            <p className="text-xs text-muted-foreground leading-relaxed">{explanation}</p>
          </div>
        </>
      )}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  StepExplainer  --  Educational panel for wizard steps               */
/* ------------------------------------------------------------------ */

export interface StepExplainerProps {
  title: string;
  description: string;
  tips?: string[];
  variant?: 'info' | 'tip' | 'warning' | 'concept';
  className?: string;
  collapsible?: boolean;
  defaultOpen?: boolean;
}

export function StepExplainer({
  title,
  description,
  tips,
  variant = 'tip',
  className,
  collapsible = true,
  defaultOpen = true,
}: StepExplainerProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const cfg = variantConfig[variant];
  const Icon = cfg.icon;

  return (
    <div className={cn('rounded-xl border', cfg.borderColor, cfg.bgColor, className)}>
      <button
        type="button"
        onClick={() => collapsible && setIsOpen(!isOpen)}
        className={cn(
          'w-full flex items-center gap-3 px-4 py-3 text-left',
          collapsible && 'cursor-pointer',
        )}
      >
        <div className={cn('p-1.5 rounded-lg', cfg.accentBg)}>
          <Icon className={cn('h-3.5 w-3.5', cfg.headerColor)} />
        </div>
        <span className={cn('text-sm font-medium flex-1', cfg.headerColor)}>{title}</span>
        {collapsible && (
          <ChevronDown
            className={cn(
              'h-4 w-4 transition-transform duration-200',
              cfg.headerColor,
              isOpen && 'rotate-180',
            )}
          />
        )}
      </button>

      {isOpen && (
        <div className="px-4 pb-4 space-y-2">
          <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>
          {tips && tips.length > 0 && (
            <ul className="space-y-1">
              {tips.map((tip, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                  <Lightbulb className={cn('h-3 w-3 mt-0.5 flex-shrink-0', cfg.headerColor)} />
                  <span>{tip}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
