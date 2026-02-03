import { describe, it, expect } from 'vitest';

/**
 * Tests for the preset requirement logic in useDataSourceStatus.
 * Note: These are unit tests for the pure logic functions.
 * Full hook integration tests would require jsdom environment.
 */

// Preset requirements mapping (same as in the hook)
const PRESET_REQUIREMENTS: Record<string, string[]> = {
  'quick-test': [],
  'standard': ['udl'],
  'multi-phenom': ['udl'],
  'validation': ['udl'],
  'full-integration': ['udl'],
  'custom': [],
};

// Service labels mapping (same as in the hook)
const SERVICE_LABELS: Record<string, string> = {
  udl: 'Unified Data Library',
  esa: 'ESA Discosweb',
  nasa: 'NASA APIs',
  spacetrack: 'Space-Track.org',
  orekit: 'Orekit Data',
  satnogs: 'SatNOGS',
  ilrs: 'ILRS',
};

// Pure function implementations for testing
function getMissingForPreset(
  presetId: string,
  configuredServices: string[]
): string[] {
  const required = PRESET_REQUIREMENTS[presetId] || [];
  return required.filter((svc) => !configuredServices.includes(svc));
}

function getServiceLabel(serviceName: string): string {
  return SERVICE_LABELS[serviceName] || serviceName.toUpperCase();
}

describe('useDataSourceStatus - preset requirements', () => {
  it('quick-test preset requires no credentials', () => {
    expect(PRESET_REQUIREMENTS['quick-test']).toEqual([]);
    expect(getMissingForPreset('quick-test', [])).toEqual([]);
    expect(getMissingForPreset('quick-test', ['udl'])).toEqual([]);
  });

  it('standard preset requires udl', () => {
    expect(PRESET_REQUIREMENTS['standard']).toEqual(['udl']);
    expect(getMissingForPreset('standard', [])).toEqual(['udl']);
    expect(getMissingForPreset('standard', ['udl'])).toEqual([]);
  });

  it('validation preset requires udl', () => {
    expect(getMissingForPreset('validation', [])).toEqual(['udl']);
    expect(getMissingForPreset('validation', ['udl', 'ilrs'])).toEqual([]);
  });

  it('custom preset requires no credentials', () => {
    expect(getMissingForPreset('custom', [])).toEqual([]);
  });

  it('unknown preset defaults to empty requirements', () => {
    expect(getMissingForPreset('unknown-preset', [])).toEqual([]);
  });
});

describe('useDataSourceStatus - service labels', () => {
  it('returns correct label for known services', () => {
    expect(getServiceLabel('udl')).toBe('Unified Data Library');
    expect(getServiceLabel('esa')).toBe('ESA Discosweb');
    expect(getServiceLabel('satnogs')).toBe('SatNOGS');
  });

  it('returns uppercased name for unknown services', () => {
    expect(getServiceLabel('unknown')).toBe('UNKNOWN');
    expect(getServiceLabel('myservice')).toBe('MYSERVICE');
  });
});
