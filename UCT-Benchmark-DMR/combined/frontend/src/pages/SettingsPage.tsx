import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Loader2, KeyRound, Monitor } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useAuthStore } from '@/stores/authStore';
import {
  useCredentials,
  useSaveCredential,
  useDeleteCredential,
  useTestCredential,
} from '@/hooks/useCredentials';
import { ServiceCredentialCard } from '@/components/settings/ServiceCredentialCard';
import { CredentialFormDialog } from '@/components/settings/CredentialFormDialog';
import type { CredentialServiceInfo } from '@/types/credentials';

export function SettingsPage() {
  const { toast } = useToast();
  const { isAuthenticated } = useAuthStore();
  const { data: services, isLoading } = useCredentials();
  const saveMutation = useSaveCredential();
  const deleteMutation = useDeleteCredential();
  const testMutation = useTestCredential();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedService, setSelectedService] = useState<CredentialServiceInfo | null>(null);
  const [testingService, setTestingService] = useState<string | null>(null);
  const [deletingService, setDeletingService] = useState<string | null>(null);

  const handleConfigure = (serviceName: string) => {
    const svc = services?.find((s) => s.service_name === serviceName) ?? null;
    setSelectedService(svc);
    setDialogOpen(true);
  };

  const handleSave = (serviceName: string, primary: string, secondary?: string) => {
    saveMutation.mutate(
      { serviceName, primary, secondary },
      {
        onSuccess: (data) => {
          toast({ title: 'Credentials Saved', description: data.message });
          setDialogOpen(false);
        },
        onError: (err: Error) => {
          toast({ title: 'Save Failed', description: err.message, variant: 'destructive' });
        },
      },
    );
  };

  const handleTest = (serviceName: string) => {
    setTestingService(serviceName);
    testMutation.mutate(serviceName, {
      onSuccess: (data) => {
        const isOk = data.status === 'success' || data.status === 'connected' || data.status === 'configured';
        toast({
          title: isOk ? 'Connection Successful' : 'Connection Issue',
          description: data.message,
          variant: isOk ? 'default' : 'destructive',
        });
        setTestingService(null);
      },
      onError: (err: Error) => {
        toast({ title: 'Test Failed', description: err.message, variant: 'destructive' });
        setTestingService(null);
      },
    });
  };

  const handleDelete = (serviceName: string) => {
    setDeletingService(serviceName);
    deleteMutation.mutate(serviceName, {
      onSuccess: (data) => {
        toast({ title: 'Credentials Cleared', description: data.message });
        setDeletingService(null);
      },
      onError: (err: Error) => {
        toast({ title: 'Delete Failed', description: err.message, variant: 'destructive' });
        setDeletingService(null);
      },
    });
  };

  // Summary stats
  const configuredCount = services?.filter(
    (s) => s.source === 'db' || s.source === 'env',
  ).length ?? 0;
  const totalCount = services?.length ?? 0;

  // App config from environment
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'Not configured';

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl xs:text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Manage credentials, connections, and application configuration
        </p>
      </div>

      <Tabs defaultValue="credentials" className="space-y-4">
        <TabsList className="grid grid-cols-2 w-full sm:w-auto sm:inline-grid">
          <TabsTrigger value="credentials" className="gap-2">
            <KeyRound className="h-4 w-4" />
            <span className="truncate">Service Credentials</span>
          </TabsTrigger>
          <TabsTrigger value="application" className="gap-2">
            <Monitor className="h-4 w-4" />
            Application
          </TabsTrigger>
        </TabsList>

        {/* Service Credentials Tab */}
        <TabsContent value="credentials">
          <div className="space-y-4">
            {/* Summary header */}
            <Card className="bg-card/50 border-white/10">
              <CardHeader className="pb-3">
                <div className="flex flex-col xs:flex-row xs:items-center xs:justify-between gap-3">
                  <div>
                    <CardTitle className="text-lg">External Service Credentials</CardTitle>
                    <CardDescription>
                      Configure API keys and tokens for data sources.
                      Credentials are encrypted at rest.
                    </CardDescription>
                  </div>
                  <Badge
                    variant={configuredCount === totalCount && totalCount > 0 ? 'success' : 'outline'}
                    className="w-fit text-sm"
                  >
                    {configuredCount}/{totalCount} configured
                  </Badge>
                </div>
              </CardHeader>
            </Card>

            {/* Service cards */}
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <div className="space-y-2">
                {services?.map((service) => (
                  <ServiceCredentialCard
                    key={service.service_name}
                    service={service}
                    onConfigure={handleConfigure}
                    onTest={handleTest}
                    onDelete={handleDelete}
                    isTesting={testingService === service.service_name}
                    isDeleting={deletingService === service.service_name}
                  />
                ))}
                {services?.length === 0 && (
                  <Card className="bg-card/50 border-white/10">
                    <CardContent className="py-8 text-center text-muted-foreground">
                      No services configured on the backend.
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </div>
        </TabsContent>

        {/* Application Tab */}
        <TabsContent value="application">
          <Card className="bg-card/50 border-white/10">
            <CardHeader>
              <CardTitle>Application Configuration</CardTitle>
              <CardDescription>
                System settings and runtime configuration (read-only)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-lg border border-white/10 p-4">
                  <p className="text-sm text-muted-foreground">API Base URL</p>
                  <p className="font-medium mt-1 text-sm break-all">{apiBaseUrl}</p>
                </div>
                <div className="rounded-lg border border-white/10 p-4">
                  <p className="text-sm text-muted-foreground">Auth Status</p>
                  <p className="font-medium mt-1 text-sm">
                    {isAuthenticated ? (
                      <span className="text-green-400">Authenticated</span>
                    ) : (
                      <span className="text-muted-foreground">Not authenticated</span>
                    )}
                  </p>
                </div>
                <div className="rounded-lg border border-white/10 p-4">
                  <p className="text-sm text-muted-foreground">Auth Provider</p>
                  <p className="font-medium mt-1 text-sm break-all">
                    {supabaseUrl !== 'Not configured' ? 'Supabase' : 'Not configured'}
                  </p>
                </div>
                <div className="rounded-lg border border-white/10 p-4">
                  <p className="text-sm text-muted-foreground">Database Backend</p>
                  <p className="font-medium mt-1 text-sm">Supabase (PostgreSQL)</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Credential form dialog */}
      <CredentialFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        service={selectedService}
        onSave={handleSave}
        onTest={handleTest}
        isSaving={saveMutation.isPending}
        isTesting={testMutation.isPending}
      />
    </div>
  );
}
