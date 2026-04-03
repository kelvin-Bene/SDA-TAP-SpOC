import { useState, useRef, useEffect, useCallback } from 'react';
import { MessageSquare, Bug, Lightbulb, HelpCircle, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { toJpeg } from 'html-to-image';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { toast } from '@/hooks/use-toast';
import { useFeedback } from './FeedbackProvider';
import type { FeedbackSeverity } from '@/types/feedback';

const MAX_DESCRIPTION_LENGTH = 5000;

const SEVERITY_OPTIONS: { value: FeedbackSeverity; label: string; icon: typeof Bug }[] = [
  { value: 'bug', label: 'Bug', icon: Bug },
  { value: 'suggestion', label: 'Suggestion', icon: Lightbulb },
  { value: 'question', label: 'Question', icon: HelpCircle },
];

export function FeedbackWidget() {
  const feedbackEnabled = import.meta.env.VITE_FEEDBACK_ENABLED;
  if (feedbackEnabled === 'false' || feedbackEnabled === '0') {
    return null;
  }

  return <FeedbackWidgetInner />;
}

function FeedbackWidgetInner() {
  const { submitFeedback } = useFeedback();

  const [open, setOpen] = useState(false);
  const [severity, setSeverity] = useState<FeedbackSeverity>('bug');
  const [description, setDescription] = useState('');
  const [screenshotBase64, setScreenshotBase64] = useState<string | undefined>(undefined);
  const [capturingScreenshot, setCapturingScreenshot] = useState(false);
  const [contextExpanded, setContextExpanded] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Capture screenshot when dialog opens
  const captureScreenshot = useCallback(async () => {
    setCapturingScreenshot(true);
    try {
      const dataUrl = await toJpeg(document.body, {
        quality: 0.3,
        pixelRatio: 0.5,
        backgroundColor: '#ffffff',
        // Exclude the dialog overlay from the screenshot
        filter: (node: HTMLElement) => {
          if (node.getAttribute?.('role') === 'dialog') return false;
          if (node.getAttribute?.('data-radix-portal') !== null && node.getAttribute?.('data-radix-portal') !== undefined) return false;
          return true;
        },
      });
      // Strip the data:image/jpeg;base64, prefix
      const base64 = dataUrl.replace(/^data:image\/jpeg;base64,/, '');
      setScreenshotBase64(base64);
    } catch {
      // Screenshot capture is best-effort; don't block the user
      setScreenshotBase64(undefined);
    } finally {
      setCapturingScreenshot(false);
    }
  }, []);

  const handleOpen = useCallback(() => {
    setOpen(true);
    setError(null);
    captureScreenshot();
  }, [captureScreenshot]);

  const handleClose = useCallback(() => {
    setOpen(false);
    setSeverity('bug');
    setDescription('');
    setScreenshotBase64(undefined);
    setContextExpanded(false);
    setError(null);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!description.trim()) {
      setError('Description is required.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const response = await submitFeedback({
        description: description.trim(),
        severity,
        // Screenshot is shown in the dialog for user context but not sent
        // to the API — the base64 payload causes 504 timeouts on Railway's proxy
      });

      if (response.success) {
        toast({
          title: 'Feedback submitted',
          description: response.message || 'Thank you for your feedback!',
          variant: 'success',
        });
        handleClose();
      } else {
        setError(response.message || 'Failed to submit feedback.');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred.';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }, [description, severity, screenshotBase64, submitFeedback, handleClose]);

  // Keyboard shortcuts: Cmd/Ctrl+Enter to submit, Escape to close
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleSubmit();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, handleSubmit]);

  // Focus textarea when dialog opens
  useEffect(() => {
    if (open && textareaRef.current) {
      // Small delay to let the dialog animation finish
      const timer = setTimeout(() => textareaRef.current?.focus(), 100);
      return () => clearTimeout(timer);
    }
  }, [open]);

  return (
    <>
      {/* Floating trigger button */}
      <Button
        onClick={handleOpen}
        size="icon"
        className={cn(
          'fixed bottom-6 left-6 z-40 h-12 w-12 rounded-full shadow-lg',
          'bg-primary text-primary-foreground hover:bg-primary/90',
          'transition-transform hover:scale-105'
        )}
        aria-label="Send feedback"
      >
        <MessageSquare className="h-5 w-5" />
      </Button>

      {/* Feedback dialog */}
      <Dialog open={open} onOpenChange={(v) => (v ? handleOpen() : handleClose())}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Send Feedback</DialogTitle>
            <DialogDescription>
              Help us improve by reporting bugs, suggesting features, or asking questions.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Severity selector */}
            <div className="space-y-2">
              <Label>Type</Label>
              <RadioGroup
                value={severity}
                onValueChange={(v) => setSeverity(v as FeedbackSeverity)}
                className="flex gap-4"
              >
                {SEVERITY_OPTIONS.map((opt) => {
                  const Icon = opt.icon;
                  return (
                    <div key={opt.value} className="flex items-center space-x-2">
                      <RadioGroupItem value={opt.value} id={`severity-${opt.value}`} />
                      <Label
                        htmlFor={`severity-${opt.value}`}
                        className="flex items-center gap-1.5 cursor-pointer font-normal"
                      >
                        <Icon className="h-4 w-4" />
                        {opt.label}
                      </Label>
                    </div>
                  );
                })}
              </RadioGroup>
            </div>

            {/* Description textarea */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="feedback-description">Description</Label>
                <span
                  className={cn(
                    'text-xs',
                    description.length > MAX_DESCRIPTION_LENGTH
                      ? 'text-destructive'
                      : 'text-muted-foreground'
                  )}
                >
                  {description.length}/{MAX_DESCRIPTION_LENGTH}
                </span>
              </div>
              <Textarea
                ref={textareaRef}
                id="feedback-description"
                placeholder="Describe what happened or what you'd like to see..."
                value={description}
                onChange={(e) => setDescription(e.target.value.slice(0, MAX_DESCRIPTION_LENGTH))}
                maxLength={MAX_DESCRIPTION_LENGTH}
                className="min-h-[120px] resize-y"
              />
            </div>

            {/* Screenshot preview */}
            {capturingScreenshot && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Capturing screenshot...
              </div>
            )}
            {screenshotBase64 && !capturingScreenshot && (
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Screenshot (auto-captured)</Label>
                <img
                  src={`data:image/jpeg;base64,${screenshotBase64}`}
                  alt="Auto-captured screenshot"
                  className="w-full rounded border border-input"
                />
              </div>
            )}

            {/* Collapsible context section */}
            <div className="border rounded-md">
              <button
                type="button"
                onClick={() => setContextExpanded(!contextExpanded)}
                className="flex w-full items-center justify-between px-3 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <span>Context (auto-collected)</span>
                {contextExpanded ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </button>
              {contextExpanded && <ContextDetails />}
            </div>

            {/* Error display */}
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleClose} disabled={submitting}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={submitting || !description.trim()}
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>Submit <span className="ml-1 text-xs opacity-70">{navigator.platform.includes('Mac') ? 'Cmd' : 'Ctrl'}+Enter</span></>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** Shows auto-collected context: URL, browser, viewport, recent actions, console errors */
function ContextDetails() {
  // Access the action logger data via the feedback context's internal state
  // We read directly from the provider since the hook exposes the same ref data
  const url = window.location.href;
  const userAgent = navigator.userAgent;
  const viewport = `${window.innerWidth}x${window.innerHeight}`;

  return (
    <div className="space-y-2 px-3 pb-3 text-xs font-mono">
      <div>
        <span className="text-muted-foreground">URL:</span>{' '}
        <span className="break-all">{url}</span>
      </div>
      <div>
        <span className="text-muted-foreground">Browser:</span>{' '}
        <span className="break-all">{userAgent}</span>
      </div>
      <div>
        <span className="text-muted-foreground">Viewport:</span> {viewport}
      </div>
      <div className="text-muted-foreground">
        Recent actions and console errors are included automatically when you submit.
      </div>
    </div>
  );
}
