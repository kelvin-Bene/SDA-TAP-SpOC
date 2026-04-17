import { useEffect, useRef, useState } from 'react';
import {
  Ion,
  Viewer as CesiumViewer,
  Cartesian3,
  Color,
  JulianDate,
  ClockRange,
  ClockStep,
  SampledPositionProperty,
  Cartesian2,
  VerticalOrigin,
  HorizontalOrigin,
  NearFarScalar,
  LabelStyle,
} from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Play, Pause, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';

// Set Cesium Ion default access token from environment variable
Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN || '';

type Regime = 'LEO' | 'MEO' | 'GEO' | 'HEO';
type RegimeOrMixed = Regime | 'mixed';

interface Satellite {
  id: string;
  name: string;
  regime: Regime;
  positions: { time: Date; x: number; y: number; z: number }[];
  color?: string;
}

interface OrbitViewerProps {
  satellites?: Satellite[];
  regime?: RegimeOrMixed;
  objectCount?: number;
  startTime?: Date;
  endTime?: Date;
  showGroundTracks?: boolean;
  className?: string;
}

// Mu for Earth (km^3/s^2)
const MU_EARTH = 398600.4418;

// Solve Kepler's equation M = E - e·sin(E) for the eccentric anomaly E
// using Newton-Raphson iteration. Converges in a handful of iterations.
function solveKepler(meanAnomaly: number, eccentricity: number): number {
  // Normalize M to [-π, π] for better initial guess
  const M = ((meanAnomaly + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
  let E = eccentricity < 0.8 ? M : Math.PI;
  for (let i = 0; i < 10; i++) {
    const f = E - eccentricity * Math.sin(E) - M;
    const fp = 1 - eccentricity * Math.cos(E);
    const dE = f / fp;
    E -= dE;
    if (Math.abs(dE) < 1e-8) break;
  }
  return E;
}

// Build an orbit track over `duration` seconds for a circular or elliptical
// Keplerian orbit. Uses proper Kepler's equation solving so eccentric orbits
// (HEO e≈0.72) render as real ellipses instead of limaçon-shaped approximations.
function buildOrbit(
  baseTime: Date,
  semiMajorAxisKm: number,
  inclinationRad: number,
  raanRad: number,
  eccentricity: number,
  phaseRad: number,
  duration: number,
  step: number,
): Satellite['positions'] {
  const period = 2 * Math.PI * Math.sqrt(Math.pow(semiMajorAxisKm, 3) / MU_EARTH);
  const positions: Satellite['positions'] = [];
  const a = semiMajorAxisKm;
  const sqrt1me2 = Math.sqrt(Math.max(0, 1 - eccentricity * eccentricity));

  const cosI = Math.cos(inclinationRad);
  const sinI = Math.sin(inclinationRad);
  const cosR = Math.cos(raanRad);
  const sinR = Math.sin(raanRad);

  for (let t = 0; t <= duration; t += step) {
    const M = (2 * Math.PI * t) / period + phaseRad;
    const E = solveKepler(M, eccentricity);
    // Orbital-plane position with focus at origin (x toward periapsis)
    const xop = a * (Math.cos(E) - eccentricity);
    const yop = a * sqrt1me2 * Math.sin(E);
    // Rotate by inclination (around x-axis) then by RAAN (around z-axis)
    const xi = xop;
    const yi = yop * cosI;
    const zi = yop * sinI;
    const x = xi * cosR - yi * sinR;
    const y = xi * sinR + yi * cosR;
    const z = zi;
    positions.push({
      time: new Date(baseTime.getTime() + t * 1000),
      x,
      y,
      z,
    });
  }
  return positions;
}

// Default satellite counts per regime when objectCount isn't specified.
const DEFAULT_COUNTS: Record<Regime, number> = { LEO: 4, MEO: 3, GEO: 3, HEO: 2 };

const REGIME_COLOR: Record<Regime, string> = {
  LEO: '#3B82F6', // cosmic blue
  MEO: '#10B981', // green
  GEO: '#F59E0B', // amber
  HEO: '#EF4444', // red
};

function generateSatellitesForRegime(
  regime: Regime,
  count: number,
  baseTime: Date,
): Satellite[] {
  const out: Satellite[] = [];
  const color = REGIME_COLOR[regime];
  for (let i = 0; i < count; i++) {
    let a: number;
    let inc: number;
    let ecc = 0;
    let duration = 0;
    let step = 60;
    // Spread satellites evenly in RAAN + phase so they don't overlap
    const raan = (2 * Math.PI * i) / Math.max(count, 1);
    const phase = (2 * Math.PI * i) / Math.max(count, 1);

    switch (regime) {
      case 'LEO':
        // 400-1000 km altitude, varied inclinations (polar, sun-synch, ISS-like)
        a = 6800 + (i % 4) * 100;
        inc = (45 + (i * 15) % 45) * (Math.PI / 180);
        duration = 2.5 * 60 * 60; // 2.5h, ~1.5 revolutions
        step = 30;
        break;
      case 'MEO':
        // Navigation-altitude (GPS ~20200 km, GLONASS ~19100 km)
        a = 26600 + (i % 3) * 200;
        inc = 55 * (Math.PI / 180);
        duration = 12 * 60 * 60; // 12h
        step = 120;
        break;
      case 'GEO':
        // Geostationary belt
        a = 42164;
        inc = 0;
        duration = 24 * 60 * 60; // 24h, full revolution
        step = 300;
        break;
      case 'HEO':
        // Molniya-like: highly elliptical with critical inclination
        a = 26600;
        inc = 63.4 * (Math.PI / 180);
        ecc = 0.72;
        duration = 12 * 60 * 60;
        step = 120;
        break;
    }

    out.push({
      id: `${regime.toLowerCase()}-${i + 1}`,
      name: `${regime}-SAT-${i + 1}`,
      regime,
      positions: buildOrbit(baseTime, a, inc, raan, ecc, phase, duration, step),
      color,
    });
  }
  return out;
}

// Generate a set of mock satellites. When regime is set, returns `count` (or
// regime default) satellites of that regime. When regime is 'mixed', returns
// a visually diverse platform showcase across all four regimes.
const generateMockSatellites = (
  regime: RegimeOrMixed = 'mixed',
  count?: number,
): Satellite[] => {
  const now = new Date();
  if (regime === 'mixed') {
    return [
      ...generateSatellitesForRegime('LEO', 3, now),
      ...generateSatellitesForRegime('MEO', 1, now),
      ...generateSatellitesForRegime('GEO', 2, now),
      ...generateSatellitesForRegime('HEO', 1, now),
    ];
  }
  const n = Math.max(1, count ?? DEFAULT_COUNTS[regime]);
  return generateSatellitesForRegime(regime, n, now);
};

function getCesiumRegimeColor(regime: string) {
  switch (regime) {
    case 'LEO': return Color.fromCssColorString('#3B82F6');
    case 'MEO': return Color.fromCssColorString('#10B981');
    case 'GEO': return Color.fromCssColorString('#F59E0B');
    case 'HEO': return Color.fromCssColorString('#EF4444');
    default: return Color.WHITE;
  }
}

export function OrbitViewer({
  satellites,
  regime = 'mixed',
  objectCount,
  startTime = new Date(),
  endTime = new Date(Date.now() + 12 * 60 * 60 * 1000),
  showGroundTracks = true,
  className,
}: OrbitViewerProps) {
  const resolvedSatellites = satellites ?? generateMockSatellites(regime, objectCount);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<CesiumViewer | null>(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [multiplier, setMultiplier] = useState(100);

  // Initialize Cesium viewer on mount; destroy on unmount.
  useEffect(() => {
    if (!containerRef.current) return;
    const viewer = new CesiumViewer(containerRef.current, {
      timeline: false,
      animation: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      selectionIndicator: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      // infoBox uses knockout.js which does `new Function(...)` (requires
      // 'unsafe-eval' in CSP). We don't need click-to-show entity info for
      // the mock demo, so disable it.
      infoBox: false,
    });
    viewerRef.current = viewer;

    // Clock
    viewer.clock.startTime = JulianDate.fromDate(startTime);
    viewer.clock.stopTime = JulianDate.fromDate(endTime);
    viewer.clock.currentTime = JulianDate.fromDate(startTime);
    viewer.clock.clockRange = ClockRange.LOOP_STOP;
    viewer.clock.clockStep = ClockStep.SYSTEM_CLOCK_MULTIPLIER;
    viewer.clock.multiplier = 100;
    viewer.clock.shouldAnimate = true;

    // Camera: off-axis 3/4 view so equatorial orbits (GEO) and the inclined HEO
    // plane are seen at an angle rather than edge-on. A lon=0, lat=30° vantage
    // at ~120 Mm altitude keeps the whole GEO ring (42 Mm radius) in frame.
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(30, 25, 120_000_000),
      duration: 0,
    });

    // Compute the longest satellite duration so the clock covers at least one full
    // orbital period of every sat. Without this, GEO (24h period) would loop every
    // 12h, making half the orbit invisible.
    const maxDurationSec = resolvedSatellites.reduce((max, sat) => {
      const first = sat.positions[0]?.time.getTime() ?? 0;
      const last = sat.positions[sat.positions.length - 1]?.time.getTime() ?? 0;
      return Math.max(max, (last - first) / 1000);
    }, 0);

    if (maxDurationSec > 0) {
      viewer.clock.stopTime = JulianDate.addSeconds(
        JulianDate.fromDate(startTime),
        maxDurationSec,
        new JulianDate(),
      );
    }

    // Add each satellite as an entity
    resolvedSatellites.forEach((sat) => {
      const property = new SampledPositionProperty();
      sat.positions.forEach((pos) => {
        property.addSample(
          JulianDate.fromDate(pos.time),
          Cartesian3.fromElements(pos.x * 1000, pos.y * 1000, pos.z * 1000),
        );
      });
      const color = sat.color
        ? Color.fromCssColorString(sat.color)
        : getCesiumRegimeColor(sat.regime);

      // Draw the full orbit path at all times. Previously the path was a 2-hour
      // trailing window, which showed only ~30° of a GEO orbit (appearing as a
      // straight line). Setting lead+trail to the sat's full sample duration
      // makes the complete ellipse visible regardless of clock position.
      const first = sat.positions[0]?.time.getTime() ?? 0;
      const last = sat.positions[sat.positions.length - 1]?.time.getTime() ?? 0;
      const satDurationSec = Math.max(1, (last - first) / 1000);

      viewer.entities.add({
        id: sat.id,
        name: sat.name,
        position: property,
        point: {
          pixelSize: 8,
          color,
          outlineColor: Color.WHITE,
          outlineWidth: 1,
          scaleByDistance: new NearFarScalar(1e7, 1.5, 1e9, 0.5),
        },
        path: showGroundTracks
          ? {
              resolution: 120,
              material: color.withAlpha(0.5),
              width: 2,
              leadTime: satDurationSec,
              trailTime: satDurationSec,
            }
          : undefined,
        label: {
          text: sat.name,
          font: '12px sans-serif',
          fillColor: Color.WHITE,
          outlineColor: Color.BLACK,
          outlineWidth: 2,
          style: LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: VerticalOrigin.BOTTOM,
          horizontalOrigin: HorizontalOrigin.CENTER,
          pixelOffset: new Cartesian2(0, -12),
          scaleByDistance: new NearFarScalar(1e7, 1, 1e9, 0.3),
        },
      });
    });

    return () => {
      if (!viewer.isDestroyed()) viewer.destroy();
      viewerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handlePlayPause = () => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    viewer.clock.shouldAnimate = !viewer.clock.shouldAnimate;
    setIsPlaying(viewer.clock.shouldAnimate);
  };

  const handleReset = () => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    viewer.clock.currentTime = JulianDate.fromDate(startTime);
  };

  const handleMultiplierChange = (value: number[]) => {
    setMultiplier(value[0]);
    const viewer = viewerRef.current;
    if (viewer) viewer.clock.multiplier = value[0];
  };

  const handleZoomIn = () => {
    viewerRef.current?.camera.zoomIn(1_000_000);
  };

  const handleZoomOut = () => {
    viewerRef.current?.camera.zoomOut(1_000_000);
  };

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">3D Orbit Visualization</CardTitle>
          <div className="flex items-center gap-2">
            {['LEO', 'MEO', 'GEO', 'HEO'].map((regime) => (
              <Badge
                key={regime}
                variant={
                  regime === 'LEO' ? 'leo' : regime === 'MEO' ? 'meo' : regime === 'GEO' ? 'geo' : 'heo'
                }
                className="text-xs"
              >
                {regime}
              </Badge>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Controls */}
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <Button variant="outline" size="icon" onClick={handlePlayPause}>
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
            <Button variant="outline" size="icon" onClick={handleReset}>
              <RotateCcw className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={handleZoomIn}>
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={handleZoomOut}>
              <ZoomOut className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex items-center gap-2 flex-1 w-full sm:min-w-[200px] sm:max-w-[300px] sm:w-auto">
            <span className="text-sm text-muted-foreground whitespace-nowrap">Speed:</span>
            <Slider
              value={[multiplier]}
              onValueChange={handleMultiplierChange}
              min={1}
              max={1000}
              step={10}
              className="flex-1"
            />
            <span className="text-sm font-mono w-12">{multiplier}x</span>
          </div>
        </div>

        {/* Cesium Viewer — vanilla Cesium mounted via useEffect (no resium) */}
        <div
          ref={containerRef}
          className="h-[60vh] sm:h-[400px] rounded-lg overflow-hidden border"
          style={{ touchAction: 'none' }}
        />

        {/* Legend */}
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>Showing {resolvedSatellites.length} satellites</span>
          <span>Click and drag to rotate • Scroll to zoom</span>
        </div>
      </CardContent>
    </Card>
  );
}
