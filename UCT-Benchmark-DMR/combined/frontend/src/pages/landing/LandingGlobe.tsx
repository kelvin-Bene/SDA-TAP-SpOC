import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { CesiumGlobe } from '@/components/cesium/CesiumGlobe';
import { useInView } from '@/hooks/useInView';
import type { OrbitSatellite } from '@/hooks/useDatasetReferenceOrbits';

interface RawPosition { time: string; x: number; y: number; z: number }
interface RawSatellite {
  id: string;
  name: string;
  regime: OrbitSatellite['regime'];
  positions: RawPosition[];
  color?: string;
}
interface RawDemoScene {
  start_time: string;
  end_time: string;
  satellites: RawSatellite[];
}

interface LandingGlobeProps {
  fallback: ReactNode;
}

/**
 * LandingPage hero 3D globe.
 *
 * Uses `useInView` to defer the Cesium + scene fetch until the hero is near
 * the viewport — unauthenticated landing visitors on slow connections don't
 * pay the 1.4MB cost until they see the feature. Falls back to the existing
 * `OrbitalGraphic` SVG when the globe is unavailable (mobile, reduced motion,
 * no WebGL, feature flag off).
 */
export function LandingGlobe({ fallback }: LandingGlobeProps) {
  const { ref, isInView } = useInView({ threshold: 0.05 });
  const [scene, setScene] = useState<RawDemoScene | null>(null);
  const [fetchFailed, setFetchFailed] = useState(false);

  useEffect(() => {
    if (!isInView || scene || fetchFailed) return;
    let cancelled = false;
    fetch('/demo-orbits.json')
      .then((r) => {
        if (!r.ok) throw new Error(`Demo orbits fetch failed: ${r.status}`);
        return r.json();
      })
      .then((data: RawDemoScene) => {
        if (!cancelled) setScene(data);
      })
      .catch(() => {
        if (!cancelled) setFetchFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [isInView, scene, fetchFailed]);

  const satellites: OrbitSatellite[] = scene
    ? scene.satellites.map((s) => ({
        id: s.id,
        name: s.name,
        regime: s.regime,
        color: s.color,
        positions: s.positions.map((p) => ({
          time: new Date(p.time),
          x: p.x,
          y: p.y,
          z: p.z,
        })),
      }))
    : [];

  return (
    <div ref={ref} className="max-w-[560px] aspect-square">
      {scene && !fetchFailed ? (
        <CesiumGlobe
          satellites={satellites}
          startTime={new Date(scene.start_time)}
          endTime={new Date(scene.end_time)}
          ariaLabel="Orbit demo: real LEO, MEO, GEO, and HEO satellites"
          fallback={fallback}
        />
      ) : (
        fallback
      )}
    </div>
  );
}
