import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Globe,
  Satellite,
  Shield,
  Radio,
  Star,
  FolderOpen,
  TestTube,
  Trash2,
  Settings2,
  Loader2,
} from 'lucide-react';
import type { CredentialServiceInfo } from '@/types/credentials';

const SERVICE_ICONS: Record<string, React.ElementType> = {
  udl: Globe,
  esa: Satellite,
  spacetrack: Shield,
  satnogs: Radio,
  celestrak: Star,
  orekit: FolderOpen,
};

interface ServiceCredentialCardProps {
  service: CredentialServiceInfo;
  onConfigure: (serviceName: string) => void;
  onTest: (serviceName: string) => void;
  onDelete: (serviceName: string) => void;
  isTesting: boolean;
  isDeleting: boolean;
}

function getStatusBadge(service: CredentialServiceInfo) {
  if (service.source === 'db') {
    return <Badge variant="success" className="text-xs">Configured (DB)</Badge>;
  }
  if (service.source === 'env') {
    return <Badge className="text-xs bg-blue-500/20 text-blue-400 border-blue-500/30">Configured (Env)</Badge>;
  }
  return <Badge variant="outline" className="text-xs text-muted-foreground">Not Configured</Badge>;
}

function getValidationBadge(service: CredentialServiceInfo) {
  if (!service.is_configured) return null;

  switch (service.validation_status) {
    case 'valid':
      return <Badge variant="success" className="text-xs">Valid</Badge>;
    case 'invalid':
      return <Badge variant="destructive" className="text-xs">Invalid</Badge>;
    case 'error':
      return <Badge variant="destructive" className="text-xs">Error</Badge>;
    case 'untested':
    default:
      return <Badge variant="outline" className="text-xs text-muted-foreground">Untested</Badge>;
  }
}

export function ServiceCredentialCard({
  service,
  onConfigure,
  onTest,
  onDelete,
  isTesting,
  isDeleting,
}: ServiceCredentialCardProps) {
  const Icon = SERVICE_ICONS[service.service_name] || Globe;

  return (
    <Card className="bg-card/50 border-white/10 hover:border-white/20 transition-colors">
      <CardContent className="p-4 sm:p-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-start gap-4 min-w-0">
            {/* Icon */}
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cosmic-cyan/20 to-cosmic-blue/20 flex items-center justify-center shrink-0">
              <Icon className="h-5 w-5 text-cosmic-cyan" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-medium text-sm">{service.label || service.service_name}</h3>
                {getStatusBadge(service)}
                {getValidationBadge(service)}
              </div>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2 sm:line-clamp-1">
                {service.description}
              </p>
              {service.last_validated && (
                <p className="text-xs text-muted-foreground mt-1">
                  Last tested: {new Date(service.last_validated).toLocaleString()}
                </p>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-auto">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 hover:bg-white/5"
              onClick={() => onConfigure(service.service_name)}
              title="Configure"
            >
              <Settings2 className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 hover:bg-white/5"
              onClick={() => onTest(service.service_name)}
              disabled={isTesting}
              title="Test Connection"
            >
              {isTesting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <TestTube className="h-4 w-4" />
              )}
            </Button>
            {service.source === 'db' && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 hover:bg-red-500/10 text-muted-foreground hover:text-red-400"
                onClick={() => onDelete(service.service_name)}
                disabled={isDeleting}
                title="Clear Credentials"
              >
                {isDeleting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
