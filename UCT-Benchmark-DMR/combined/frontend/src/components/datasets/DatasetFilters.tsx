import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { InfoPopover } from '@/components/ui/info-popover';
import { X, Filter, Orbit, Layers, Radio } from 'lucide-react';
import type { DatasetFilters as FilterType, OrbitalRegime, DataTier, SensorType } from '@/types';
import { cn } from '@/lib/utils';

interface DatasetFiltersProps {
  filters: FilterType;
  onFiltersChange: (filters: FilterType) => void;
  onClear: () => void;
}

const regimeOptions: { value: OrbitalRegime | 'all'; label: string }[] = [
  { value: 'all', label: 'All Regimes' },
  { value: 'LEO', label: 'LEO (Low Earth Orbit)' },
  { value: 'MEO', label: 'MEO (Medium Earth Orbit)' },
  { value: 'GEO', label: 'GEO (Geostationary)' },
  { value: 'HEO', label: 'HEO (Highly Elliptical)' },
];

const tierOptions: { value: DataTier | 'all'; label: string }[] = [
  { value: 'all', label: 'All Tiers' },
  { value: 'T1', label: 'T1 - Pristine' },
  { value: 'T2', label: 'T2 - Downsampled' },
  { value: 'T3', label: 'T3 - Simulated Obs' },
  { value: 'T4', label: 'T4 - Synthetic' },
];

const sensorOptions: { value: SensorType | 'all'; label: string }[] = [
  { value: 'all', label: 'All Sensors' },
  { value: 'optical', label: 'Optical' },
  { value: 'radar', label: 'Radar' },
  { value: 'rf', label: 'RF' },
];

export function DatasetFilters({ filters, onFiltersChange, onClear }: DatasetFiltersProps) {
  const hasFilters =
    filters.regime !== 'all' ||
    filters.tier !== 'all' ||
    filters.sensor !== 'all' ||
    filters.objectCountRange;

  return (
    <Card className="border-white/10 bg-white/[0.02]">
      <CardContent className="pt-5 pb-5">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="h-4 w-4 text-cosmic-cyan" />
          <span className="text-sm font-medium">Filters</span>
          {hasFilters && (
            <span className="ml-auto">
              <Button variant="ghost" size="sm" onClick={onClear} className="gap-1.5 h-7 text-xs text-muted-foreground hover:text-foreground">
                <X className="h-3 w-3" />
                Clear All
              </Button>
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-end gap-4">
          {/* Regime Filter */}
          <div className="space-y-2 min-w-[180px]">
            <div className="flex items-center gap-1.5">
              <Orbit className="h-3 w-3 text-muted-foreground" />
              <Label htmlFor="regime-filter" className="text-xs text-muted-foreground">Orbital Regime</Label>
              <InfoPopover
                title="Orbital Regime"
                description="Filter datasets by the altitude band of their objects."
                details={[
                  'LEO: Fast-moving objects at 200-2,000 km',
                  'MEO: Navigation satellites at 2,000-35,786 km',
                  'GEO: Stationary comms satellites at ~35,786 km',
                  'HEO: Highly elliptical orbits with variable altitude',
                ]}
                variant="info"
              />
            </div>
            <Select
              value={filters.regime || 'all'}
              onValueChange={(value) =>
                onFiltersChange({ ...filters, regime: value as OrbitalRegime | 'all' })
              }
            >
              <SelectTrigger
                id="regime-filter"
                className={cn(
                  'border-white/10 bg-white/5',
                  filters.regime !== 'all' && 'border-cosmic-cyan/30 bg-cosmic-cyan/5',
                )}
              >
                <SelectValue placeholder="Select regime" />
              </SelectTrigger>
              <SelectContent>
                {regimeOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Tier Filter */}
          <div className="space-y-2 min-w-[180px]">
            <div className="flex items-center gap-1.5">
              <Layers className="h-3 w-3 text-muted-foreground" />
              <Label htmlFor="tier-filter" className="text-xs text-muted-foreground">Data Tier</Label>
              <InfoPopover
                title="Data Tier"
                description="Filter by data quality and origin."
                details={[
                  'T1: Full-quality real observations',
                  'T2: Downsampled real observations',
                  'T3: Gap-filled with simulated data',
                  'T4: Fully synthetic scenario',
                ]}
                variant="info"
              />
            </div>
            <Select
              value={filters.tier || 'all'}
              onValueChange={(value) =>
                onFiltersChange({ ...filters, tier: value as DataTier | 'all' })
              }
            >
              <SelectTrigger
                id="tier-filter"
                className={cn(
                  'border-white/10 bg-white/5',
                  filters.tier !== 'all' && 'border-stellar-purple/30 bg-stellar-purple/5',
                )}
              >
                <SelectValue placeholder="Select tier" />
              </SelectTrigger>
              <SelectContent>
                {tierOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Sensor Filter */}
          <div className="space-y-2 min-w-[180px]">
            <div className="flex items-center gap-1.5">
              <Radio className="h-3 w-3 text-muted-foreground" />
              <Label htmlFor="sensor-filter" className="text-xs text-muted-foreground">Sensor Type</Label>
              <InfoPopover
                title="Sensor Type"
                description="Filter by the type of sensor observations in the dataset."
                details={[
                  'Optical: Measures angles (RA, Dec) against the star background',
                  'Radar: Provides range and range-rate in addition to angles',
                  'RF: Radio-frequency observations (signal, Doppler) from SatNOGS',
                ]}
                variant="info"
              />
            </div>
            <Select
              value={filters.sensor || 'all'}
              onValueChange={(value) =>
                onFiltersChange({ ...filters, sensor: value as SensorType | 'all' })
              }
            >
              <SelectTrigger
                id="sensor-filter"
                className={cn(
                  'border-white/10 bg-white/5',
                  filters.sensor !== 'all' && 'border-aurora-green/30 bg-aurora-green/5',
                )}
              >
                <SelectValue placeholder="Select sensor" />
              </SelectTrigger>
              <SelectContent>
                {sensorOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Object Count Range */}
          <div className="space-y-2 min-w-[200px] flex-1 max-w-[300px]">
            <Label className="text-xs text-muted-foreground">
              Object Count: <span className="font-mono text-foreground">{filters.objectCountRange?.min || 10}</span> - <span className="font-mono text-foreground">{filters.objectCountRange?.max || 100}</span>
            </Label>
            <Slider
              defaultValue={[filters.objectCountRange?.min || 10, filters.objectCountRange?.max || 100]}
              min={10}
              max={200}
              step={10}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  objectCountRange: { min: value[0], max: value[1] },
                })
              }
              className="mt-2"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
