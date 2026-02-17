import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, ExternalLink } from 'lucide-react';
import type { CredentialServiceInfo, ServiceFormConfig } from '@/types/credentials';

const SERVICE_FORM_CONFIGS: Record<string, ServiceFormConfig> = {
  udl: {
    service_name: 'udl',
    label: 'Unified Data Library',
    primaryLabel: 'API Token',
    primaryPlaceholder: 'Base64-encoded UDL credentials',
    helpUrl: 'https://unifieddatalibrary.com',
    helpText: 'Obtain your token from the UDL portal.',
  },
  esa: {
    service_name: 'esa',
    label: 'ESA Discosweb',
    primaryLabel: 'Bearer Token',
    primaryPlaceholder: 'ESA API bearer token',
    helpUrl: 'https://discosweb.esoc.esa.int',
    helpText: 'Register for an API token at ESA Discosweb.',
  },
  nasa_earthdata: {
    service_name: 'nasa_earthdata',
    label: 'NASA Earthdata',
    primaryLabel: 'JWT Token',
    primaryPlaceholder: 'NASA Earthdata JWT token',
    helpUrl: 'https://urs.earthdata.nasa.gov',
    helpText: 'Create an Earthdata Login account to obtain a token.',
  },
  spacetrack: {
    service_name: 'spacetrack',
    label: 'Space-Track.org',
    primaryLabel: 'Username',
    primaryPlaceholder: 'Space-Track.org username',
    secondaryLabel: 'Password',
    secondaryPlaceholder: 'Space-Track.org password',
    helpUrl: 'https://www.space-track.org/auth/createAccount',
    helpText: 'Create a free account at Space-Track.org.',
  },
  orekit: {
    service_name: 'orekit',
    label: 'Orekit Data Path',
    primaryLabel: 'Data Directory Path',
    primaryPlaceholder: '/path/to/orekit-data',
    helpUrl: 'https://gitlab.orekit.org/orekit/orekit-data',
    helpText: 'Download the Orekit data folder and enter its path.',
  },
};

interface CredentialFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  service: CredentialServiceInfo | null;
  onSave: (serviceName: string, primary: string, secondary?: string) => void;
  onTest: (serviceName: string) => void;
  isSaving: boolean;
  isTesting: boolean;
}

export function CredentialFormDialog({
  open,
  onOpenChange,
  service,
  onSave,
  onTest,
  isSaving,
  isTesting,
}: CredentialFormDialogProps) {
  const [primary, setPrimary] = useState('');
  const [secondary, setSecondary] = useState('');

  if (!service) return null;

  const config = SERVICE_FORM_CONFIGS[service.service_name] || {
    service_name: service.service_name,
    label: service.label || service.service_name,
    primaryLabel: 'Credential',
    primaryPlaceholder: 'Enter credential value',
  };

  const isUsernamePassword = service.credential_type === 'username_password';
  const isPath = service.credential_type === 'path';

  const handleSave = () => {
    if (!primary.trim()) return;
    onSave(service.service_name, primary.trim(), isUsernamePassword ? secondary.trim() : undefined);
    setPrimary('');
    setSecondary('');
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setPrimary('');
      setSecondary('');
    }
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md glass border-white/10">
        <DialogHeader>
          <DialogTitle>Configure {config.label}</DialogTitle>
          <DialogDescription>
            {config.helpText || service.description}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="primary">{config.primaryLabel}</Label>
            <Input
              id="primary"
              type={isPath ? 'text' : 'password'}
              placeholder={config.primaryPlaceholder}
              value={primary}
              onChange={(e) => setPrimary(e.target.value)}
              autoComplete="off"
            />
          </div>

          {isUsernamePassword && config.secondaryLabel && (
            <div className="space-y-2">
              <Label htmlFor="secondary">{config.secondaryLabel}</Label>
              <Input
                id="secondary"
                type="password"
                placeholder={config.secondaryPlaceholder}
                value={secondary}
                onChange={(e) => setSecondary(e.target.value)}
                autoComplete="off"
              />
            </div>
          )}

          {config.helpUrl && (
            <a
              href={config.helpUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-cosmic-cyan hover:underline"
            >
              <ExternalLink className="h-3 w-3" />
              Get credentials
            </a>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => onTest(service.service_name)}
            disabled={isTesting}
            className="mr-auto"
          >
            {isTesting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing...
              </>
            ) : (
              'Test Current'
            )}
          </Button>
          <Button
            onClick={handleSave}
            disabled={!primary.trim() || isSaving}
          >
            {isSaving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              'Save'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
