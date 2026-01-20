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
import { X } from 'lucide-react';
import type { DatasetFilters as FilterType, OrbitalRegime, DataTier, SensorType } from '@/types';

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
    <Card>
      <CardContent className="pt-6">
        <div className="flex flex-wrap items-end gap-4">
          {/* Regime Filter */}
          <div className="space-y-2 min-w-[180px]">
            <Label htmlFor="regime-filter">Orbital Regime</Label>
            <Select
              value={filters.regime || 'all'}
              onValueChange={(value) =>
                onFiltersChange({ ...filters, regime: value as OrbitalRegime | 'all' })
              }
            >
              <SelectTrigger id="regime-filter">
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
            <Label htmlFor="tier-filter">Data Tier</Label>
            <Select
              value={filters.tier || 'all'}
              onValueChange={(value) =>
                onFiltersChange({ ...filters, tier: value as DataTier | 'all' })
              }
            >
              <SelectTrigger id="tier-filter">
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
            <Label htmlFor="sensor-filter">Sensor Type</Label>
            <Select
              value={filters.sensor || 'all'}
              onValueChange={(value) =>
                onFiltersChange({ ...filters, sensor: value as SensorType | 'all' })
              }
            >
              <SelectTrigger id="sensor-filter">
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
            <Label>Object Count: {filters.objectCountRange?.min || 10} - {filters.objectCountRange?.max || 100}</Label>
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

          {/* Clear Filters */}
          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={onClear} className="gap-1">
              <X className="h-4 w-4" />
              Clear Filters
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
