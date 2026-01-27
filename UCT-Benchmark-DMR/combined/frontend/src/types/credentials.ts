/** Credential management types. */

export interface CredentialServiceInfo {
  service_name: string;
  credential_type: 'bearer_token' | 'jwt' | 'username_password' | 'path';
  label: string | null;
  description: string | null;
  is_configured: boolean;
  last_validated: string | null;
  validation_status: 'untested' | 'valid' | 'invalid' | 'error' | 'not_configured';
  source: 'database' | 'environment' | 'none';
  has_env_fallback: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface CredentialSaveRequest {
  primary: string;
  secondary?: string;
}

export interface CredentialSaveResponse {
  service_name: string;
  is_configured: boolean;
  message: string;
}

export interface CredentialTestResponse {
  service_name: string;
  status: string;
  message: string;
  response_time_ms: number | null;
}

export interface ServiceFormConfig {
  service_name: string;
  label: string;
  primaryLabel: string;
  primaryPlaceholder: string;
  secondaryLabel?: string;
  secondaryPlaceholder?: string;
  helpUrl?: string;
  helpText?: string;
}
