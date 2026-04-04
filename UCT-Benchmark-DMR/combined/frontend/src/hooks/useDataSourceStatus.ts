import { useCredentials } from './useCredentials';
import type { CredentialServiceInfo } from '@/types/credentials';

export interface DataSourceStatus {
  serviceName: string;
  label: string;
  isConfigured: boolean;
  validationStatus: 'untested' | 'valid' | 'invalid' | 'error' | 'not_configured';
}

/**
 * Maps preset IDs to their required credential services.
 * Services listed here must be configured for the preset to work.
 */
const PRESET_REQUIREMENTS: Record<string, string[]> = {
  'quick-test': [],              // Can work with mock data or minimal UDL
  'standard': ['udl'],           // UDL required, ESA optional (public)
  'multi-phenom': ['udl'],       // UDL + SatNOGS (SatNOGS is public API)
  'validation': ['udl'],         // UDL + ILRS (ILRS has public endpoints)
  'full-integration': ['udl'],   // UDL required, others optional
  'custom': [],                  // User configures manually
};

/**
 * Maps service names to human-readable labels for display.
 */
const SERVICE_LABELS: Record<string, string> = {
  udl: 'Unified Data Library',
  esa: 'ESA Discosweb',
  nasa: 'NASA APIs',
  spacetrack: 'Space-Track.org',
  orekit: 'Orekit Data',
  satnogs: 'SatNOGS',
  ilrs: 'ILRS',
};

/**
 * Hook that provides data source status information for the dataset generator.
 * Wraps useCredentials and adds preset-specific requirement checking.
 */
export function useDataSourceStatus() {
  const { data: credentials, isLoading, error } = useCredentials();

  /**
   * Get list of missing required credentials for a preset.
   */
  const getMissingForPreset = (presetId: string): string[] => {
    if (!credentials) return [];

    const required = PRESET_REQUIREMENTS[presetId] || [];
    return required.filter((svc) => {
      const cred = credentials.find((c) => c.service_name === svc);
      return !cred?.is_configured;
    });
  };

  /**
   * Check if all required credentials are configured for a preset.
   */
  const isPresetReady = (presetId: string): boolean => {
    return getMissingForPreset(presetId).length === 0;
  };

  /**
   * Get human-readable label for a service.
   */
  const getServiceLabel = (serviceName: string): string => {
    return SERVICE_LABELS[serviceName] || serviceName.toUpperCase();
  };

  /**
   * Transform credentials into DataSourceStatus array.
   */
  const sources: DataSourceStatus[] = (credentials || []).map((cred: CredentialServiceInfo) => ({
    serviceName: cred.service_name,
    label: cred.label || getServiceLabel(cred.service_name),
    isConfigured: cred.is_configured,
    validationStatus: cred.validation_status,
  }));

  /**
   * Count of configured vs total sources.
   */
  const configuredCount = sources.filter((s) => s.isConfigured).length;
  const totalCount = sources.length;

  /**
   * Check if UDL is configured (most common requirement).
   */
  const isUdlConfigured = credentials?.find((c) => c.service_name === 'udl')?.is_configured ?? false;

  return {
    sources,
    credentials,
    isLoading,
    error,
    getMissingForPreset,
    isPresetReady,
    getServiceLabel,
    configuredCount,
    totalCount,
    isUdlConfigured,
  };
}
