import { useRef, useState, useCallback, useEffect } from 'react';
import { cn } from '@/lib/utils';
import {
  Globe, Orbit, Satellite, Radio, Waves, ChevronLeft,
  Database, Eye, EyeOff, Loader2, ChevronDown, ChevronRight,
  Plus, Minus, Crosshair,
} from 'lucide-react';
import { api } from '@/api/client';

// ── Orbital regime definitions ────────────────────────────────────────────────
const REGIMES = [
  {
    id: 'LEO' as const,
    label: 'Low Earth Orbit',
    altitude: '200 - 2,000 km',
    color: '#3B82F6',
    icon: Orbit,
    orbits: [
      { inclination: 51.6, altKm: 420, label: 'ISS Orbit (420 km)' },
      { inclination: 97.5, altKm: 700, label: 'Sun-Sync (700 km)' },
      { inclination: 45, altKm: 1200, label: 'LEO Belt (1,200 km)' },
    ],
    cameraAlt: 8_000_000,
    description: 'Dense debris environment with fast-moving satellites completing orbits in ~90 minutes.',
  },
  {
    id: 'MEO' as const,
    label: 'Medium Earth Orbit',
    altitude: '2,000 - 35,786 km',
    color: '#10B981',
    icon: Satellite,
    orbits: [
      { inclination: 55, altKm: 20200, label: 'GPS Constellation' },
      { inclination: 56, altKm: 23222, label: 'Galileo Orbit' },
    ],
    cameraAlt: 40_000_000,
    description: 'Home to navigation constellations like GPS, GLONASS, and Galileo.',
  },
  {
    id: 'GEO' as const,
    label: 'Geostationary Orbit',
    altitude: '~35,786 km',
    color: '#F59E0B',
    icon: Radio,
    orbits: [
      { inclination: 0, altKm: 35786, label: 'Geostationary Belt' },
    ],
    cameraAlt: 60_000_000,
    description: 'Satellites appear stationary over the equator. Home to communications and weather sats.',
  },
  {
    id: 'HEO' as const,
    label: 'Highly Elliptical Orbit',
    altitude: 'Variable',
    color: '#EF4444',
    icon: Waves,
    orbits: [
      { inclination: 63.4, perigeeKm: 500, apogeeKm: 39873, altKm: 0, label: 'Molniya Orbit' },
    ],
    cameraAlt: 55_000_000,
    description: 'Elongated orbits providing extended coverage over high latitudes.',
  },
];

type RegimeId = 'LEO' | 'MEO' | 'GEO' | 'HEO';
type PanelTab = 'regimes' | 'datasets';

interface DatasetInfo {
  id: string;
  name: string;
  regime: string;
  satelliteCount: number;
  satellites: number[];
  loaded: boolean;
}

interface VisibleSatellite {
  noradId: number;
  datasetId: string;
  regime: string;
}

// ── Helper: compute a satellite position on its regime orbit ──────────────────
function computeSatPosition(
  Cesium: any,
  noradId: number,
  regime: string,
  index: number,
  total: number,
) {
  const cfg = REGIMES.find((r) => r.id === regime) || REGIMES[0];
  const orbit = cfg.orbits[0];
  const altKm = orbit.altKm || 500;
  const inclination = orbit.inclination || 45;

  const baseAngle = (2 * Math.PI * index) / Math.max(total, 1);
  const jitter = ((noradId % 37) / 37) * (Math.PI / 6);
  const angle = baseAngle + jitter;

  const incRad = Cesium.Math.toRadians(inclination);
  const lat = Math.asin(Math.sin(incRad) * Math.sin(angle));
  const lon =
    Math.atan2(Math.cos(incRad) * Math.sin(angle), Math.cos(angle)) +
    ((noradId % 13) / 13) * Math.PI * 0.3;

  const altVar = ((noradId % 23) / 23 - 0.5) * altKm * 0.06;
  return Cesium.Cartesian3.fromRadians(lon, lat, (altKm + altVar) * 1000);
}

// ── Orbit-path generation helpers ─────────────────────────────────────────────
function generateCircularPositions(
  Cesium: any, altKm: number, inclination: number, lonOffset: number,
) {
  const positions: any[] = [];
  const incRad = Cesium.Math.toRadians(inclination);
  const lonOffsetRad = Cesium.Math.toRadians(lonOffset);
  const numPoints = 360;
  for (let i = 0; i <= numPoints; i++) {
    const theta = (2 * Math.PI * i) / numPoints;
    const lat = Math.asin(Math.sin(incRad) * Math.sin(theta));
    const lon =
      Math.atan2(Math.cos(incRad) * Math.sin(theta), Math.cos(theta)) + lonOffsetRad;
    positions.push(Cesium.Cartesian3.fromRadians(lon, lat, altKm * 1000));
  }
  return positions;
}

function generateEllipticalPositions(
  Cesium: any, perigeeKm: number, apogeeKm: number, inclination: number, lonOffset: number,
) {
  const positions: any[] = [];
  const incRad = Cesium.Math.toRadians(inclination);
  const lonOffsetRad = Cesium.Math.toRadians(lonOffset);
  const earthRadius = 6371;
  const rp = earthRadius + perigeeKm;
  const ra = earthRadius + apogeeKm;
  const a = (rp + ra) / 2;
  const e = (ra - rp) / (ra + rp);
  const numPoints = 360;
  for (let i = 0; i <= numPoints; i++) {
    const nu = (2 * Math.PI * i) / numPoints;
    const r = (a * (1 - e * e)) / (1 + e * Math.cos(nu));
    const altKm = r - earthRadius;
    const lat = Math.asin(Math.sin(incRad) * Math.sin(nu));
    const lon =
      Math.atan2(Math.cos(incRad) * Math.sin(nu), Math.cos(nu)) + lonOffsetRad;
    positions.push(Cesium.Cartesian3.fromRadians(lon, lat, altKm * 1000));
  }
  return positions;
}

// ══════════════════════════════════════════════════════════════════════════════
// Component
// ══════════════════════════════════════════════════════════════════════════════
export function OrbitMapPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerInstanceRef = useRef<any>(null);
  const satelliteEntitiesRef = useRef<Map<string, any>>(new Map());

  // Viewer state
  const [viewerReady, setViewerReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Panel state
  const [panelCollapsed, setPanelCollapsed] = useState(false);
  const [panelTab, setPanelTab] = useState<PanelTab>('regimes');

  // Regime state
  const [selectedRegime, setSelectedRegime] = useState<RegimeId | null>(null);
  const [hoveredRegime, setHoveredRegime] = useState<RegimeId | null>(null);

  // Dataset state
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const [expandedDataset, setExpandedDataset] = useState<string | null>(null);
  const [datasetDetailLoading, setDatasetDetailLoading] = useState<string | null>(null);
  const [visibleSatellites, setVisibleSatellites] = useState<Map<string, VisibleSatellite>>(
    () => new Map(),
  );
  const [selectedSatKey, setSelectedSatKey] = useState<string | null>(null);

  // ── Initialize Cesium ─────────────────────────────────────────────────────
  useEffect(() => {
    let viewer: any = null;
    let destroyed = false;

    async function initCesium() {
      try {
        const Cesium = await import('cesium');
        await import('cesium/Build/Cesium/Widgets/widgets.css');
        if (destroyed || !containerRef.current) return;

        const token = import.meta.env.VITE_CESIUM_ION_TOKEN;
        if (token) Cesium.Ion.defaultAccessToken = token;

        const creditDiv = document.createElement('div');
        creditDiv.style.display = 'none';
        containerRef.current.appendChild(creditDiv);

        viewer = new Cesium.Viewer(containerRef.current, {
          timeline: false,
          animation: false,
          baseLayerPicker: false,
          geocoder: false,
          homeButton: false,
          sceneModePicker: false,
          selectionIndicator: false,
          navigationHelpButton: false,
          fullscreenButton: false,
          infoBox: false,
          creditContainer: creditDiv,
          scene3DOnly: true,
          ...(token
            ? {}
            : {
                imageryProvider: new (Cesium.TileMapServiceImageryProvider as any)({
                  url: Cesium.buildModuleUrl('Assets/Textures/NaturalEarthII'),
                }),
                terrainProvider: undefined,
              }),
        });

        viewer.scene.backgroundColor = Cesium.Color.BLACK;
        viewer.scene.globe.enableLighting = true;
        viewer.scene.globe.atmosphereLightIntensity = 3.0;
        viewer.scene.skyBox = new Cesium.SkyBox({
          sources: {
            positiveX: Cesium.buildModuleUrl('Assets/Textures/SkyBox/tycho2t3_80_px.jpg'),
            negativeX: Cesium.buildModuleUrl('Assets/Textures/SkyBox/tycho2t3_80_mx.jpg'),
            positiveY: Cesium.buildModuleUrl('Assets/Textures/SkyBox/tycho2t3_80_py.jpg'),
            negativeY: Cesium.buildModuleUrl('Assets/Textures/SkyBox/tycho2t3_80_my.jpg'),
            positiveZ: Cesium.buildModuleUrl('Assets/Textures/SkyBox/tycho2t3_80_pz.jpg'),
            negativeZ: Cesium.buildModuleUrl('Assets/Textures/SkyBox/tycho2t3_80_mz.jpg'),
          },
        });

        viewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(0, 20, 45_000_000),
        });

        // Add static orbit paths
        addOrbits(viewer, Cesium);

        viewerInstanceRef.current = { viewer, Cesium };
        if (!destroyed) setViewerReady(true);
      } catch (err: any) {
        console.error('Cesium init error:', err);
        if (!destroyed) setError(err.message || 'Failed to initialize 3D viewer');
      }
    }

    initCesium();
    return () => {
      destroyed = true;
      if (viewer && !viewer.isDestroyed()) viewer.destroy();
      viewerInstanceRef.current = null;
    };
  }, []);

  function addOrbits(viewer: any, Cesium: any) {
    REGIMES.forEach((regime) => {
      regime.orbits.forEach((orbit, idx) => {
        const lonOffset = idx * 60;
        let positions: any[];
        if ('perigeeKm' in orbit && orbit.perigeeKm && 'apogeeKm' in orbit && orbit.apogeeKm) {
          positions = generateEllipticalPositions(Cesium, orbit.perigeeKm as number, orbit.apogeeKm as number, orbit.inclination, lonOffset);
        } else {
          positions = generateCircularPositions(Cesium, orbit.altKm, orbit.inclination, lonOffset);
        }
        const color = Cesium.Color.fromCssColorString(regime.color);
        viewer.entities.add({
          name: orbit.label,
          polyline: {
            positions,
            width: 3,
            material: new Cesium.ColorMaterialProperty(color.withAlpha(0.85)),
            clampToGround: false,
          },
          properties: { regimeId: regime.id, type: 'orbit' },
        });
      });
    });
  }

  // ── Camera helpers ────────────────────────────────────────────────────────
  const flyTo = useCallback((altMeters: number, lat = 20, lon = 0, duration = 1.5) => {
    const inst = viewerInstanceRef.current;
    if (!inst) return;
    inst.viewer.camera.flyTo({
      destination: inst.Cesium.Cartesian3.fromDegrees(lon, lat, altMeters),
      duration,
    });
  }, []);

  // ── Regime selection & orbit visibility ───────────────────────────────────
  useEffect(() => {
    const inst = viewerInstanceRef.current;
    if (!inst || !viewerReady) return;
    const { viewer, Cesium } = inst;

    const entities = viewer.entities.values;
    for (let i = 0; i < entities.length; i++) {
      const entity = entities[i];
      const entType = entity.properties?.type?.getValue();
      if (entType !== 'orbit') continue;

      const regimeId = entity.properties?.regimeId?.getValue();
      if (!regimeId) continue;

      const isSelected = selectedRegime === regimeId;
      const isOther = selectedRegime !== null && !isSelected;
      const regime = REGIMES.find((r) => r.id === regimeId);
      if (!regime) continue;

      const color = Cesium.Color.fromCssColorString(regime.color);
      entity.polyline.width = isSelected ? 5 : 3;
      entity.polyline.material = new Cesium.ColorMaterialProperty(
        color.withAlpha(isOther ? 0.15 : isSelected ? 1.0 : 0.85),
      );
    }
  }, [selectedRegime, viewerReady]);

  const handleRegimeClick = useCallback(
    (regime: (typeof REGIMES)[number]) => {
      if (selectedRegime === regime.id) {
        setSelectedRegime(null);
        flyTo(45_000_000, 20, 0, 1.5);
      } else {
        setSelectedRegime(regime.id as RegimeId);
        flyTo(regime.cameraAlt, 25, 0, 1.5);
      }
    },
    [selectedRegime, flyTo],
  );

  // ── Click handler for entities on the globe ───────────────────────────────
  useEffect(() => {
    const inst = viewerInstanceRef.current;
    if (!inst || !viewerReady) return;
    const { viewer, Cesium } = inst;

    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((movement: any) => {
      const picked = viewer.scene.pick(movement.position);
      if (!Cesium.defined(picked) || !picked.id) return;

      const entType = picked.id.properties?.type?.getValue();

      if (entType === 'satellite') {
        const satKey = picked.id.properties?.satKey?.getValue();
        if (satKey) {
          setSelectedSatKey(satKey);
          setPanelTab('datasets');
          viewer.flyTo(picked.id, {
            offset: new Cesium.HeadingPitchRange(0, -Cesium.Math.PI_OVER_FOUR, 2_000_000),
            duration: 1.5,
          });
        }
        return;
      }

      // Orbit click (existing behavior)
      if (picked.id?.name) {
        const regime = REGIMES.find((r) => r.orbits.some((o) => o.label === picked.id.name));
        if (regime) {
          setSelectedRegime(regime.id as RegimeId);
          flyTo(regime.cameraAlt, 25, 0, 1.5);
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    return () => handler.destroy();
  }, [viewerReady, flyTo]);

  // ── Fetch datasets on mount ───────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function fetch() {
      setDatasetsLoading(true);
      try {
        const response = await api.getDatasets();
        if (cancelled) return;
        const data = response.data as any[];
        setDatasets(
          data.map((d: any) => ({
            id: String(d.id),
            name: d.name || `Dataset ${d.id}`,
            regime: d.regime || 'LEO',
            satelliteCount: d.satellite_count || 0,
            satellites: [],
            loaded: false,
          })),
        );
      } catch (err) {
        console.error('Failed to fetch datasets:', err);
      } finally {
        if (!cancelled) setDatasetsLoading(false);
      }
    }
    fetch();
    return () => { cancelled = true; };
  }, []);

  // ── Load satellites when a dataset is expanded ────────────────────────────
  const expandDataset = useCallback(
    async (datasetId: string) => {
      if (expandedDataset === datasetId) {
        setExpandedDataset(null);
        return;
      }
      setExpandedDataset(datasetId);

      const ds = datasets.find((d) => d.id === datasetId);
      if (!ds || ds.loaded) return;

      setDatasetDetailLoading(datasetId);
      try {
        const response = await api.getDataset(datasetId);
        const detail = response.data as any;
        const sats: number[] = detail.satellites || [];
        setDatasets((prev) =>
          prev.map((d) => (d.id === datasetId ? { ...d, satellites: sats, loaded: true } : d)),
        );
      } catch (err) {
        console.error('Failed to load dataset satellites:', err);
      } finally {
        setDatasetDetailLoading(null);
      }
    },
    [expandedDataset, datasets],
  );

  // ── Satellite visibility management ───────────────────────────────────────
  const toggleSatellite = useCallback(
    (datasetId: string, noradId: number, regime: string) => {
      const key = `${datasetId}-${noradId}`;
      setVisibleSatellites((prev) => {
        const next = new Map(prev);
        if (next.has(key)) {
          next.delete(key);
          if (selectedSatKey === key) setSelectedSatKey(null);
        } else {
          next.set(key, { noradId, datasetId, regime });
        }
        return next;
      });
    },
    [selectedSatKey],
  );

  const addAllSatellites = useCallback((ds: DatasetInfo) => {
    setVisibleSatellites((prev) => {
      const next = new Map(prev);
      ds.satellites.forEach((noradId) => {
        const key = `${ds.id}-${noradId}`;
        if (!next.has(key)) next.set(key, { noradId, datasetId: ds.id, regime: ds.regime });
      });
      return next;
    });
  }, []);

  const removeAllSatellites = useCallback(
    (datasetId: string) => {
      setVisibleSatellites((prev) => {
        const next = new Map(prev);
        for (const key of [...next.keys()]) {
          if (key.startsWith(`${datasetId}-`)) next.delete(key);
        }
        return next;
      });
      if (selectedSatKey?.startsWith(`${datasetId}-`)) setSelectedSatKey(null);
    },
    [selectedSatKey],
  );

  // ── Sync visible satellites → Cesium entities ─────────────────────────────
  useEffect(() => {
    const inst = viewerInstanceRef.current;
    if (!inst || !viewerReady) return;
    const { viewer, Cesium } = inst;
    const current = satelliteEntitiesRef.current;
    const visibleKeys = new Set(visibleSatellites.keys());

    // Remove stale entities
    for (const [key, entity] of [...current.entries()]) {
      if (!visibleKeys.has(key)) {
        viewer.entities.remove(entity);
        current.delete(key);
      }
    }

    // Collect per-dataset totals for positioning
    const datasetTotals = new Map<string, number>();
    const datasetIndexes = new Map<string, number>();
    for (const sat of visibleSatellites.values()) {
      datasetTotals.set(sat.datasetId, (datasetTotals.get(sat.datasetId) || 0) + 1);
    }

    // Add new entities
    for (const [key, sat] of visibleSatellites) {
      if (current.has(key)) continue;

      const dsIdx = datasetIndexes.get(sat.datasetId) || 0;
      datasetIndexes.set(sat.datasetId, dsIdx + 1);
      const total = datasetTotals.get(sat.datasetId) || 1;

      const position = computeSatPosition(Cesium, sat.noradId, sat.regime, dsIdx, total);
      const regimeCfg = REGIMES.find((r) => r.id === sat.regime);
      const color = Cesium.Color.fromCssColorString(regimeCfg?.color || '#FFFFFF');

      const entity = viewer.entities.add({
        name: `SAT-${sat.noradId}`,
        position,
        point: {
          pixelSize: 10,
          color,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
          scaleByDistance: new Cesium.NearFarScalar(1.5e6, 1.5, 1.5e8, 0.5),
        },
        label: {
          text: String(sat.noradId),
          font: '12px monospace',
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -16),
          scaleByDistance: new Cesium.NearFarScalar(1.5e6, 1.0, 1.5e8, 0.3),
          showBackground: true,
          backgroundColor: Cesium.Color.BLACK.withAlpha(0.6),
          backgroundPadding: new Cesium.Cartesian2(6, 3),
        },
        properties: {
          type: 'satellite',
          noradId: sat.noradId,
          datasetId: sat.datasetId,
          regime: sat.regime,
          satKey: key,
        },
      });
      current.set(key, entity);
    }
  }, [visibleSatellites, viewerReady]);

  // ── Zoom to a satellite ───────────────────────────────────────────────────
  const zoomToSatellite = useCallback(
    (datasetId: string, noradId: number, regime: string) => {
      const inst = viewerInstanceRef.current;
      if (!inst) return;
      const { viewer, Cesium } = inst;

      const key = `${datasetId}-${noradId}`;
      setSelectedSatKey(key);

      // Ensure satellite is visible on map
      if (!visibleSatellites.has(key)) {
        toggleSatellite(datasetId, noradId, regime);
      }

      // Try flying to existing entity
      const entity = satelliteEntitiesRef.current.get(key);
      if (entity) {
        const regimeCfg = REGIMES.find((r) => r.id === regime);
        const offset = (regimeCfg?.cameraAlt || 8_000_000) * 0.25;
        viewer.flyTo(entity, {
          offset: new Cesium.HeadingPitchRange(0, -Cesium.Math.PI_OVER_FOUR, offset),
          duration: 1.5,
        });
      }
    },
    [visibleSatellites, toggleSatellite],
  );

  // ── Count visible sats per dataset ────────────────────────────────────────
  const visibleCountForDataset = useCallback(
    (datasetId: string) => {
      let count = 0;
      for (const key of visibleSatellites.keys()) {
        if (key.startsWith(`${datasetId}-`)) count++;
      }
      return count;
    },
    [visibleSatellites],
  );

  // ══════════════════════════════════════════════════════════════════════════
  // Render
  // ══════════════════════════════════════════════════════════════════════════
  return (
    <div className="relative h-[calc(100vh-8rem)] -mx-4 -my-8 lg:-mx-8">
      {/* Cesium container */}
      <div ref={containerRef} className="absolute inset-0" style={{ background: '#000' }} />

      {/* Loading state */}
      {!viewerReady && !error && (
        <div className="absolute inset-0 flex items-center justify-center z-10 bg-black">
          <div className="flex flex-col items-center gap-4">
            <div className="w-10 h-10 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            <span className="text-sm text-muted-foreground">Loading 3D Globe...</span>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center z-10 bg-black">
          <div className="text-center space-y-3 max-w-md px-8">
            <Globe className="h-12 w-12 text-muted-foreground mx-auto" />
            <p className="text-foreground font-semibold">Failed to load 3D viewer</p>
            <p className="text-sm text-muted-foreground">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-lg bg-primary/20 text-primary text-sm hover:bg-primary/30 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* ── Overlay control panel ─────────────────────────────────────────── */}
      {viewerReady && (
        <div
          className={cn(
            'absolute top-4 left-4 z-10 transition-all duration-300',
            panelCollapsed ? 'w-12' : 'w-80',
          )}
        >
          {panelCollapsed ? (
            <button
              onClick={() => setPanelCollapsed(false)}
              className="w-12 h-12 rounded-xl bg-black/70 backdrop-blur-xl border border-white/10 flex items-center justify-center hover:bg-white/10 transition-colors"
            >
              <Globe className="h-5 w-5 text-primary" />
            </button>
          ) : (
            <div className="rounded-xl bg-black/70 backdrop-blur-xl border border-white/10 overflow-hidden flex flex-col max-h-[calc(100vh-12rem)]">
              {/* Panel header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <Globe className="h-4 w-4 text-primary" />
                  <span className="font-display font-semibold text-sm text-white">
                    Orbit Map
                  </span>
                </div>
                <button
                  onClick={() => setPanelCollapsed(true)}
                  className="p-1 rounded hover:bg-white/10 transition-colors"
                >
                  <ChevronLeft className="h-4 w-4 text-white/50" />
                </button>
              </div>

              {/* Tab switcher */}
              <div className="flex border-b border-white/10 flex-shrink-0">
                <button
                  onClick={() => setPanelTab('regimes')}
                  className={cn(
                    'flex-1 px-3 py-2 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5',
                    panelTab === 'regimes'
                      ? 'text-white border-b-2 border-primary bg-white/5'
                      : 'text-white/40 hover:text-white/60',
                  )}
                >
                  <Orbit className="h-3.5 w-3.5" />
                  Regimes
                </button>
                <button
                  onClick={() => setPanelTab('datasets')}
                  className={cn(
                    'flex-1 px-3 py-2 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5',
                    panelTab === 'datasets'
                      ? 'text-white border-b-2 border-primary bg-white/5'
                      : 'text-white/40 hover:text-white/60',
                  )}
                >
                  <Database className="h-3.5 w-3.5" />
                  Datasets
                  {visibleSatellites.size > 0 && (
                    <span className="ml-1 px-1.5 py-0.5 rounded-full bg-primary/30 text-[10px] text-primary">
                      {visibleSatellites.size}
                    </span>
                  )}
                </button>
              </div>

              {/* Scrollable content area */}
              <div className="overflow-y-auto flex-1 min-h-0">
                {/* ── Regimes Tab ────────────────────────────────────────── */}
                {panelTab === 'regimes' && (
                  <>
                    <div className="p-3 space-y-2">
                      {REGIMES.map((regime) => {
                        const Icon = regime.icon;
                        const isSelected = selectedRegime === regime.id;
                        return (
                          <button
                            key={regime.id}
                            onClick={() => handleRegimeClick(regime)}
                            onMouseEnter={() => setHoveredRegime(regime.id as RegimeId)}
                            onMouseLeave={() => setHoveredRegime(null)}
                            className={cn(
                              'w-full flex items-start gap-3 rounded-lg p-3 text-left transition-all duration-200 border',
                              isSelected
                                ? 'bg-white/10 border-white/20'
                                : 'border-transparent hover:bg-white/5',
                            )}
                            style={{
                              borderColor: isSelected ? regime.color + '60' : undefined,
                              boxShadow:
                                isSelected
                                  ? `0 0 20px -4px ${regime.color}50, inset 0 0 20px -10px ${regime.color}20`
                                  : hoveredRegime === regime.id
                                    ? `0 0 16px -4px ${regime.color}40`
                                    : 'none',
                            }}
                          >
                            <div
                              className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                              style={{ backgroundColor: regime.color + '25' }}
                            >
                              <Icon className="h-4 w-4" style={{ color: regime.color }} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <div
                                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                                  style={{ backgroundColor: regime.color }}
                                />
                                <span className="font-semibold text-sm text-white">
                                  {regime.id}
                                </span>
                                <span className="text-xs text-white/50 truncate">
                                  {regime.altitude}
                                </span>
                              </div>
                              <p className="text-xs text-white/40 mt-1 leading-relaxed">
                                {regime.description}
                              </p>
                            </div>
                          </button>
                        );
                      })}
                    </div>

                    {selectedRegime && (
                      <div className="px-3 pb-3">
                        <button
                          onClick={() => {
                            setSelectedRegime(null);
                            flyTo(45_000_000, 20, 0, 1.5);
                          }}
                          className="w-full rounded-lg px-3 py-2 text-xs text-white/50 hover:text-white bg-white/5 hover:bg-white/10 transition-colors text-center"
                        >
                          Reset View (Show All)
                        </button>
                      </div>
                    )}
                  </>
                )}

                {/* ── Datasets Tab ───────────────────────────────────────── */}
                {panelTab === 'datasets' && (
                  <div className="p-3 space-y-2">
                    {datasetsLoading ? (
                      <div className="flex items-center justify-center py-8 gap-2 text-white/40">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span className="text-xs">Loading datasets...</span>
                      </div>
                    ) : datasets.length === 0 ? (
                      <div className="text-center py-8">
                        <Database className="h-8 w-8 text-white/20 mx-auto mb-2" />
                        <p className="text-xs text-white/40">No datasets found</p>
                        <p className="text-[11px] text-white/25 mt-1">
                          Generate a dataset first
                        </p>
                      </div>
                    ) : (
                      datasets.map((ds) => {
                        const isExpanded = expandedDataset === ds.id;
                        const regimeCfg = REGIMES.find((r) => r.id === ds.regime);
                        const regimeColor = regimeCfg?.color || '#888';
                        const visCount = visibleCountForDataset(ds.id);
                        const allVisible = ds.loaded && ds.satellites.length > 0 && visCount === ds.satellites.length;

                        return (
                          <div
                            key={ds.id}
                            className={cn(
                              'rounded-lg border transition-all duration-200',
                              isExpanded
                                ? 'bg-white/5 border-white/15'
                                : 'border-transparent hover:bg-white/[0.03]',
                            )}
                          >
                            {/* Dataset header */}
                            <button
                              onClick={() => expandDataset(ds.id)}
                              className="w-full flex items-center gap-3 p-3 text-left"
                            >
                              <div
                                className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                                style={{ backgroundColor: regimeColor + '20' }}
                              >
                                <Database className="h-3.5 w-3.5" style={{ color: regimeColor }} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="font-semibold text-xs text-white truncate">
                                    {ds.name}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2 mt-0.5">
                                  <span
                                    className="text-[10px] font-medium px-1.5 py-0.5 rounded"
                                    style={{
                                      backgroundColor: regimeColor + '20',
                                      color: regimeColor,
                                    }}
                                  >
                                    {ds.regime}
                                  </span>
                                  <span className="text-[10px] text-white/30">
                                    {ds.satelliteCount} sat{ds.satelliteCount !== 1 ? 's' : ''}
                                  </span>
                                  {visCount > 0 && (
                                    <span className="text-[10px] text-primary">
                                      {visCount} shown
                                    </span>
                                  )}
                                </div>
                              </div>
                              {isExpanded ? (
                                <ChevronDown className="h-4 w-4 text-white/30 flex-shrink-0" />
                              ) : (
                                <ChevronRight className="h-4 w-4 text-white/30 flex-shrink-0" />
                              )}
                            </button>

                            {/* Expanded: satellite list */}
                            {isExpanded && (
                              <div className="px-3 pb-3 space-y-2">
                                {/* Add/Remove all controls */}
                                {ds.loaded && ds.satellites.length > 0 && (
                                  <div className="flex gap-2">
                                    <button
                                      onClick={() => addAllSatellites(ds)}
                                      disabled={allVisible}
                                      className={cn(
                                        'flex-1 flex items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-[11px] font-medium transition-colors',
                                        allVisible
                                          ? 'bg-white/5 text-white/20 cursor-not-allowed'
                                          : 'bg-primary/15 text-primary hover:bg-primary/25',
                                      )}
                                    >
                                      <Plus className="h-3 w-3" />
                                      Add All
                                    </button>
                                    <button
                                      onClick={() => removeAllSatellites(ds.id)}
                                      disabled={visCount === 0}
                                      className={cn(
                                        'flex-1 flex items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-[11px] font-medium transition-colors',
                                        visCount === 0
                                          ? 'bg-white/5 text-white/20 cursor-not-allowed'
                                          : 'bg-red-500/15 text-red-400 hover:bg-red-500/25',
                                      )}
                                    >
                                      <Minus className="h-3 w-3" />
                                      Remove All
                                    </button>
                                  </div>
                                )}

                                {/* Satellite list */}
                                {datasetDetailLoading === ds.id ? (
                                  <div className="flex items-center justify-center py-4 gap-2 text-white/30">
                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                    <span className="text-[11px]">Loading satellites...</span>
                                  </div>
                                ) : ds.satellites.length === 0 ? (
                                  <p className="text-[11px] text-white/30 text-center py-3">
                                    No satellite data available
                                  </p>
                                ) : (
                                  <div className="space-y-0.5 max-h-52 overflow-y-auto">
                                    {ds.satellites.map((noradId) => {
                                      const key = `${ds.id}-${noradId}`;
                                      const isVisible = visibleSatellites.has(key);
                                      const isSel = selectedSatKey === key;

                                      return (
                                        <div
                                          key={noradId}
                                          className={cn(
                                            'flex items-center gap-2 rounded-md px-2 py-1.5 group transition-colors',
                                            isSel
                                              ? 'bg-primary/15 border border-primary/30'
                                              : 'hover:bg-white/5 border border-transparent',
                                          )}
                                        >
                                          {/* Toggle visibility */}
                                          <button
                                            onClick={() =>
                                              toggleSatellite(ds.id, noradId, ds.regime)
                                            }
                                            className="flex-shrink-0 p-0.5 rounded transition-colors hover:bg-white/10"
                                            title={isVisible ? 'Hide from map' : 'Show on map'}
                                          >
                                            {isVisible ? (
                                              <Eye className="h-3.5 w-3.5 text-primary" />
                                            ) : (
                                              <EyeOff className="h-3.5 w-3.5 text-white/20 group-hover:text-white/40" />
                                            )}
                                          </button>

                                          {/* NORAD ID + color dot */}
                                          <div
                                            className="w-2 h-2 rounded-full flex-shrink-0"
                                            style={{
                                              backgroundColor: isVisible ? regimeColor : regimeColor + '40',
                                            }}
                                          />
                                          <span
                                            className={cn(
                                              'text-[11px] font-mono flex-1',
                                              isVisible ? 'text-white' : 'text-white/40',
                                            )}
                                          >
                                            {noradId}
                                          </span>

                                          {/* Zoom-to button */}
                                          <button
                                            onClick={() =>
                                              zoomToSatellite(ds.id, noradId, ds.regime)
                                            }
                                            className="flex-shrink-0 p-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white/10"
                                            title="Zoom to satellite"
                                          >
                                            <Crosshair className="h-3.5 w-3.5 text-white/50" />
                                          </button>
                                        </div>
                                      );
                                    })}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </div>

              {/* Footer hint */}
              <div className="px-4 py-2 border-t border-white/10 text-[11px] text-white/30 flex-shrink-0">
                Click &amp; drag to rotate | Scroll to zoom | Click orbit to select
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Selected regime info overlay ───────────────────────────────────── */}
      {selectedRegime && viewerReady && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10">
          <div
            className="rounded-xl bg-black/70 backdrop-blur-xl border border-white/10 px-6 py-3 flex items-center gap-4"
            style={{
              boxShadow: `0 0 30px -8px ${REGIMES.find((r) => r.id === selectedRegime)?.color}40`,
            }}
          >
            <div
              className="w-3 h-3 rounded-full animate-pulse"
              style={{ backgroundColor: REGIMES.find((r) => r.id === selectedRegime)?.color }}
            />
            <span className="font-display font-semibold text-sm text-white">
              {REGIMES.find((r) => r.id === selectedRegime)?.label}
            </span>
            <span className="text-xs text-white/50">
              {REGIMES.find((r) => r.id === selectedRegime)?.altitude}
            </span>
          </div>
        </div>
      )}

      {/* ── Selected satellite info overlay ────────────────────────────────── */}
      {selectedSatKey && !selectedRegime && viewerReady && (() => {
        const sat = visibleSatellites.get(selectedSatKey);
        if (!sat) return null;
        const regimeCfg = REGIMES.find((r) => r.id === sat.regime);
        const ds = datasets.find((d) => d.id === sat.datasetId);
        return (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10">
            <div
              className="rounded-xl bg-black/70 backdrop-blur-xl border border-white/10 px-6 py-3 flex items-center gap-4"
              style={{ boxShadow: `0 0 30px -8px ${regimeCfg?.color}40` }}
            >
              <div
                className="w-3 h-3 rounded-full animate-pulse"
                style={{ backgroundColor: regimeCfg?.color }}
              />
              <span className="font-display font-semibold text-sm text-white">
                NORAD {sat.noradId}
              </span>
              <span className="text-xs text-white/50">
                {ds?.name || `Dataset ${sat.datasetId}`}
              </span>
              <span
                className="text-[10px] font-medium px-1.5 py-0.5 rounded"
                style={{ backgroundColor: (regimeCfg?.color || '#888') + '25', color: regimeCfg?.color }}
              >
                {sat.regime}
              </span>
              <button
                onClick={() => setSelectedSatKey(null)}
                className="text-xs text-white/30 hover:text-white/60 transition-colors ml-2"
              >
                Dismiss
              </button>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
