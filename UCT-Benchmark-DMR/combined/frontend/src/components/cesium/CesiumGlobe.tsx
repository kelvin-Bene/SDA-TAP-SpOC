import { Component, lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';

import type { OrbitSatellite } from '@/hooks/useDatasetReferenceOrbits';

// Keep OrbitViewer's heavy Cesium import out of the page chunk. Types come
// through via `import type` which Vite strips at build time — only this
// dynamic import pulls real code.
const OrbitViewer = lazy(() =>
  import('./OrbitViewer').then((m) => ({ default: m.OrbitViewer })),
);

export interface CesiumGlobeProps {
  satellites: OrbitSatellite[];
  startTime?: Date;
  endTime?: Date;
  ariaLabel: string;
  fallback?: ReactNode;
  className?: string;
  showGroundTracks?: boolean;
}

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
}

function hasWebGL2(): boolean {
  if (typeof document === 'undefined') return false;
  try {
    const canvas = document.createElement('canvas');
    return !!(canvas.getContext('webgl2') || canvas.getContext('experimental-webgl'));
  } catch {
    return false;
  }
}

function globeEnabled(): boolean {
  // Opt-in via env; if the variable is missing (dev default) we still render
  // so the UI works locally, but prod deploys must set it explicitly.
  const envValue = (import.meta.env.VITE_ENABLE_GLOBE as string | undefined) ?? '';
  if (envValue === '') return true;
  return envValue.toLowerCase() !== 'false' && envValue !== '0';
}

/**
 * Thin accessibility-aware wrapper around the 3D OrbitViewer.
 *
 * Falls back to `fallback` when:
 *   - VITE_ENABLE_GLOBE is set to false/0
 *   - prefers-reduced-motion is on
 *   - WebGL2 is unavailable
 *   - Cesium chunk fails to load (error boundary)
 */
export function CesiumGlobe({
  satellites,
  startTime,
  endTime,
  ariaLabel,
  fallback = null,
  className,
  showGroundTracks = true,
}: CesiumGlobeProps) {
  const [capable, setCapable] = useState<boolean | null>(null);
  const [hadError, setHadError] = useState(false);
  const errorBoundaryKey = useRef(0);

  useEffect(() => {
    setCapable(globeEnabled() && !prefersReducedMotion() && hasWebGL2());
  }, []);

  const regimeSummary = useMemo(() => {
    const counts = satellites.reduce<Record<string, number>>((acc, s) => {
      acc[s.regime] = (acc[s.regime] ?? 0) + 1;
      return acc;
    }, {});
    return Object.entries(counts)
      .map(([regime, n]) => `${n} ${regime}`)
      .join(', ');
  }, [satellites]);

  if (capable === false || hadError) {
    return <>{fallback}</>;
  }
  if (capable === null) {
    // Capability probe hasn't run yet — avoid flashing fallback.
    return null;
  }

  return (
    <div
      role="img"
      aria-label={`${ariaLabel}${regimeSummary ? `: ${regimeSummary}` : ''}`}
      className={className}
    >
      <ErrorBoundary
        key={errorBoundaryKey.current}
        onError={() => setHadError(true)}
        fallback={fallback}
      >
        <Suspense fallback={fallback}>
          <OrbitViewer
            satellites={satellites}
            startTime={startTime}
            endTime={endTime}
            showGroundTracks={showGroundTracks}
          />
        </Suspense>
      </ErrorBoundary>
    </div>
  );
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback: ReactNode;
  onError?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch() {
    this.props.onError?.();
  }

  render() {
    if (this.state.hasError) return <>{this.props.fallback}</>;
    return this.props.children;
  }
}
