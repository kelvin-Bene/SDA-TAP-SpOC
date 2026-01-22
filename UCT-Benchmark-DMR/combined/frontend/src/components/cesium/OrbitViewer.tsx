import { useRef, useState } from 'react';
import { Viewer, Entity, CameraFlyTo, Clock } from 'resium';
import {
  Ion,
  Cartesian3,
  Color,
  JulianDate,
  ClockRange,
  ClockStep,
  SampledPositionProperty,
  PathGraphics,
  PointGraphics,
  LabelGraphics,
  Cartesian2,
  VerticalOrigin,
  HorizontalOrigin,
  NearFarScalar,
} from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Play, Pause, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';

// Set Cesium Ion default access token from environment variable
Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN || '';

interface Satellite {
  id: string;
  name: string;
  regime: 'LEO' | 'MEO' | 'GEO' | 'HEO';
  positions: { time: Date; x: number; y: number; z: number }[];
  color?: string;
}

interface OrbitViewerProps {
  satellites?: Satellite[];
  startTime?: Date;
  endTime?: Date;
  showGroundTracks?: boolean;
  className?: string;
}

// Mock satellite data for demonstration
const generateMockSatellites = (): Satellite[] => {
  const now = new Date();
  const satellites: Satellite[] = [];

  // Generate a few LEO satellites
  for (let i = 0; i < 3; i++) {
    const positions = [];
    const semiMajorAxis = 6800 + i * 100; // km
    const inclination = (45 + i * 15) * (Math.PI / 180);
    const period = 2 * Math.PI * Math.sqrt(Math.pow(semiMajorAxis, 3) / 398600.4418); // seconds

    for (let t = 0; t < period * 2; t += 60) {
      const meanAnomaly = (2 * Math.PI * t) / period;
      const x = semiMajorAxis * Math.cos(meanAnomaly);
      const y = semiMajorAxis * Math.sin(meanAnomaly) * Math.cos(inclination);
      const z = semiMajorAxis * Math.sin(meanAnomaly) * Math.sin(inclination);

      positions.push({
        time: new Date(now.getTime() + t * 1000),
        x,
        y,
        z,
      });
    }

    satellites.push({
      id: `leo-${i + 1}`,
      name: `LEO-SAT-${i + 1}`,
      regime: 'LEO',
      positions,
      color: ['#3B82F6', '#60A5FA', '#93C5FD'][i],
    });
  }

  // Add a GEO satellite
  const geoRadius = 42164; // km
  const geoPositions = [];
  for (let t = 0; t < 86400 * 2; t += 300) {
    const angle = (2 * Math.PI * t) / 86400;
    geoPositions.push({
      time: new Date(now.getTime() + t * 1000),
      x: geoRadius * Math.cos(angle),
      y: geoRadius * Math.sin(angle),
      z: 0,
    });
  }
  satellites.push({
    id: 'geo-1',
    name: 'GEO-SAT-1',
    regime: 'GEO',
    positions: geoPositions,
    color: '#F59E0B',
  });

  return satellites;
};

export function OrbitViewer({
  satellites = generateMockSatellites(),
  startTime = new Date(),
  endTime = new Date(Date.now() + 2 * 60 * 60 * 1000),
  showGroundTracks = true,
  className,
}: OrbitViewerProps) {
  const viewerRef = useRef<any>(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [multiplier, setMultiplier] = useState(100);

  // Convert satellite positions to Cesium SampledPositionProperty
  const createPositionProperty = (positions: Satellite['positions']) => {
    const property = new SampledPositionProperty();
    positions.forEach((pos) => {
      const time = JulianDate.fromDate(pos.time);
      const position = Cartesian3.fromElements(pos.x * 1000, pos.y * 1000, pos.z * 1000);
      property.addSample(time, position);
    });
    return property;
  };

  const handlePlayPause = () => {
    if (viewerRef.current?.cesiumElement) {
      const clock = viewerRef.current.cesiumElement.clock;
      clock.shouldAnimate = !clock.shouldAnimate;
      setIsPlaying(!isPlaying);
    }
  };

  const handleReset = () => {
    if (viewerRef.current?.cesiumElement) {
      const clock = viewerRef.current.cesiumElement.clock;
      clock.currentTime = JulianDate.fromDate(startTime);
    }
  };

  const handleMultiplierChange = (value: number[]) => {
    setMultiplier(value[0]);
    if (viewerRef.current?.cesiumElement) {
      viewerRef.current.cesiumElement.clock.multiplier = value[0];
    }
  };

  const handleZoomIn = () => {
    if (viewerRef.current?.cesiumElement) {
      viewerRef.current.cesiumElement.camera.zoomIn(1000000);
    }
  };

  const handleZoomOut = () => {
    if (viewerRef.current?.cesiumElement) {
      viewerRef.current.cesiumElement.camera.zoomOut(1000000);
    }
  };

  const getRegimeColor = (regime: string) => {
    switch (regime) {
      case 'LEO':
        return Color.fromCssColorString('#3B82F6');
      case 'MEO':
        return Color.fromCssColorString('#10B981');
      case 'GEO':
        return Color.fromCssColorString('#F59E0B');
      case 'HEO':
        return Color.fromCssColorString('#EF4444');
      default:
        return Color.WHITE;
    }
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
          <div className="flex items-center gap-2">
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
          <div className="flex items-center gap-2 flex-1 min-w-[200px] max-w-[300px]">
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

        {/* Cesium Viewer */}
        <div className="h-[400px] rounded-lg overflow-hidden border">
          <Viewer
            ref={viewerRef}
            full={false}
            style={{ height: '100%', width: '100%' }}
            timeline={false}
            animation={false}
            baseLayerPicker={false}
            geocoder={false}
            homeButton={false}
            sceneModePicker={false}
            selectionIndicator={false}
            navigationHelpButton={false}
            fullscreenButton={false}
            creditContainer={undefined}
          >
            <Clock
              startTime={JulianDate.fromDate(startTime)}
              stopTime={JulianDate.fromDate(endTime)}
              currentTime={JulianDate.fromDate(startTime)}
              clockRange={ClockRange.LOOP_STOP}
              clockStep={ClockStep.SYSTEM_CLOCK_MULTIPLIER}
              multiplier={multiplier}
              shouldAnimate={isPlaying}
            />

            <CameraFlyTo
              destination={Cartesian3.fromDegrees(0, 0, 50000000)}
              duration={0}
            />

            {satellites.map((satellite) => {
              const positionProperty = createPositionProperty(satellite.positions);
              const color = satellite.color
                ? Color.fromCssColorString(satellite.color)
                : getRegimeColor(satellite.regime);

              return (
                <Entity
                  key={satellite.id}
                  name={satellite.name}
                  position={positionProperty}
                  point={
                    new PointGraphics({
                      pixelSize: 8,
                      color: color,
                      outlineColor: Color.WHITE,
                      outlineWidth: 1,
                      scaleByDistance: new NearFarScalar(1e7, 1.5, 1e9, 0.5),
                    })
                  }
                  path={
                    showGroundTracks
                      ? new PathGraphics({
                          resolution: 120,
                          material: color.withAlpha(0.5),
                          width: 2,
                          leadTime: 3600,
                          trailTime: 3600,
                        })
                      : undefined
                  }
                  label={
                    new LabelGraphics({
                      text: satellite.name,
                      font: '12px sans-serif',
                      fillColor: Color.WHITE,
                      outlineColor: Color.BLACK,
                      outlineWidth: 2,
                      style: 2, // FILL_AND_OUTLINE
                      verticalOrigin: VerticalOrigin.BOTTOM,
                      horizontalOrigin: HorizontalOrigin.CENTER,
                      pixelOffset: new Cartesian2(0, -12),
                      scaleByDistance: new NearFarScalar(1e7, 1, 1e9, 0.3),
                    })
                  }
                />
              );
            })}
          </Viewer>
        </div>

        {/* Legend */}
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>Showing {satellites.length} satellites</span>
          <span>Click and drag to rotate • Scroll to zoom</span>
        </div>
      </CardContent>
    </Card>
  );
}
