import { useState, useMemo, useRef, useEffect } from 'react';
import { debounce } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { X, Search, ArrowUpDown } from 'lucide-react';
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
  const [localSearch, setLocalSearch] = useState(filters.search || '');
  const filtersRef = useRef(filters);
  filtersRef.current = filters;

  const debouncedSearchChange = useMemo(
    () => debounce((value: string) => {
      onFiltersChange({ ...filtersRef.current, search: value });
    }, 300),
    [onFiltersChange]
  );

  // Sync local search when filters change externally (e.g., clear button)
  useEffect(() => {
    setLocalSearch(filters.search || '');
  }, [filters.search]);

  const hasFilters =
    filters.regime !== 'all' ||
    filters.tier !== 'all' ||
    filters.sensor !== 'all' ||
    (filters.objectCountRange && (filters.objectCountRange.min > 0 || filters.objectCountRange.max < 200)) ||
    filters.search ||
    filters.sortBy;

  return (
    <Card>
      <CardContent className="pt-6 space-y-4">
        {/* Search and Sort Row */}
        <div className="flex flex-col sm:flex-row sm:flex-wrap items-end gap-4">
          <div className="w-full sm:w-auto space-y-2 flex-1 min-w-[200px] max-w-[400px]">
            <Label htmlFor="search-filter">Search</Label>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                id="search-filter"
                placeholder="Search by dataset name..."
                value={localSearch}
                onChange={(e) => {
                  setLocalSearch(e.target.value);
                  debouncedSearchChange(e.target.value);
                }}
                className="pl-9"
              />
            </div>
          </div>
          <div className="w-full sm:w-auto space-y-2 min-w-[180px]">
            <Label htmlFor="sort-filter">Sort By</Label>
            <Select
              value={filters.sortBy || 'created_at'}
              onValueChange={(value) =>
                onFiltersChange({ ...filters, sortBy: value as FilterType['sortBy'] })
              }
            >
              <SelectTrigger id="sort-filter">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="created_at">Date Created</SelectItem>
                <SelectItem value="name">Name</SelectItem>
                <SelectItem value="satellite_count">Object Count</SelectItem>
                <SelectItem value="observation_count">Observations</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={() =>
              onFiltersChange({
                ...filters,
                sortOrder: filters.sortOrder === 'asc' ? 'desc' : 'asc',
              })
            }
            title={filters.sortOrder === 'asc' ? 'Ascending' : 'Descending'}
          >
            <ArrowUpDown className="h-4 w-4" />
          </Button>
        </div>

        {/* Filter Dropdowns Row */}
        <div className="flex flex-col sm:flex-row sm:flex-wrap items-end gap-4">
          {/* Regime Filter */}
          <div className="w-full sm:w-auto space-y-2 min-w-[180px]">
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
          <div className="w-full sm:w-auto space-y-2 min-w-[180px]">
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
          <div className="w-full sm:w-auto space-y-2 min-w-[180px]">
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
          <div className="w-full sm:w-auto space-y-2 min-w-[200px] flex-1 max-w-[300px]">
            <Label>Object Count: {filters.objectCountRange?.min ?? 0} - {filters.objectCountRange?.max ?? 200}</Label>
            <Slider
              value={[filters.objectCountRange?.min ?? 0, filters.objectCountRange?.max ?? 200]}
              min={0}
              max={200}
              step={5}
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
            <Button
              variant="ghost"
              size="sm"
              onClick={onClear}
              className="w-full sm:w-auto gap-1 justify-center"
            >
              <X className="h-4 w-4" />
              Clear Filters
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
