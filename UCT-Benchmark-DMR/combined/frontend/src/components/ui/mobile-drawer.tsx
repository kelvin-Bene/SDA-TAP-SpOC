import * as React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Bottom-sheet drawer built on @radix-ui/react-dialog (already installed).
 *
 * Use for mobile-only overlays where a centered dialog feels wrong:
 *   - Filter panels (Leaderboard, DatasetBrowser)
 *   - Long pickers / option lists
 *   - Any mobile action that benefits from thumb-reach anchoring to the bottom
 *
 * On desktop (md:+) most callers will keep the existing inline UI and only
 * mount this drawer on mobile via a `useBreakpoint` check.
 *
 * @example
 * <MobileDrawer open={open} onOpenChange={setOpen} title="Filters">
 *   {filters}
 * </MobileDrawer>
 */

const MobileDrawer = DialogPrimitive.Root;
const MobileDrawerTrigger = DialogPrimitive.Trigger;
const MobileDrawerClose = DialogPrimitive.Close;

const MobileDrawerOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      'fixed inset-0 z-50 bg-black/70 backdrop-blur-sm',
      'data-[state=open]:animate-in data-[state=closed]:animate-out',
      'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
      className,
    )}
    {...props}
  />
));
MobileDrawerOverlay.displayName = 'MobileDrawerOverlay';

export interface MobileDrawerContentProps
  extends Omit<
    React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>,
    'title'
  > {
  /** Optional visible title rendered in the drawer header. */
  title?: React.ReactNode;
  /** Optional description rendered under the title. */
  description?: React.ReactNode;
  /** Hide the built-in close button (consumer provides their own). */
  hideCloseButton?: boolean;
}

const MobileDrawerContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  MobileDrawerContentProps
>(
  (
    { className, children, title, description, hideCloseButton, ...props },
    ref,
  ) => (
    <DialogPrimitive.Portal>
      <MobileDrawerOverlay />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(
          'fixed inset-x-0 bottom-0 z-50 flex max-h-[90dvh] flex-col',
          'rounded-t-2xl border-t border-white/10 bg-background shadow-2xl',
          'pb-safe',
          'data-[state=open]:animate-in data-[state=closed]:animate-out',
          'data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom',
          'duration-200',
          className,
        )}
        {...props}
      >
        {/* Grabber */}
        <div className="flex items-center justify-center pt-2 pb-1">
          <div className="h-1.5 w-10 rounded-full bg-white/20" aria-hidden="true" />
        </div>

        {(title || description || !hideCloseButton) && (
          <div className="relative flex items-start justify-between gap-4 px-4 pt-2 pb-4 border-b border-white/5">
            <div className="min-w-0 flex-1">
              {title && (
                <DialogPrimitive.Title className="text-lg font-semibold leading-tight">
                  {title}
                </DialogPrimitive.Title>
              )}
              {description && (
                <DialogPrimitive.Description className="mt-1 text-sm text-muted-foreground">
                  {description}
                </DialogPrimitive.Description>
              )}
            </div>
            {!hideCloseButton && (
              <DialogPrimitive.Close
                className="shrink-0 rounded-md p-2 text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </DialogPrimitive.Close>
            )}
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-4 py-4">{children}</div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  ),
);
MobileDrawerContent.displayName = 'MobileDrawerContent';

export {
  MobileDrawer,
  MobileDrawerTrigger,
  MobileDrawerClose,
  MobileDrawerContent,
  MobileDrawerOverlay,
};
