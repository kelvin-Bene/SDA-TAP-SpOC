import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { User, Building2, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useLeaderboardStatistics } from '@/hooks/useLeaderboard';
import { useSubmissions } from '@/hooks/useSubmissions';
import { useAuthStore } from '@/stores/authStore';
import { api } from '@/api/client';

export function ProfilePage() {
  const { toast } = useToast();
  const { user } = useAuthStore();
  const [isSaving, setIsSaving] = useState(false);

  // Editable fields initialized from auth user data
  const [displayName, setDisplayName] = useState(user?.username ?? '');
  const [organization, setOrganization] = useState(user?.organization ?? '');

  // Fetch real stats from API
  const { data: stats } = useLeaderboardStatistics();
  const { data: submissions = [] } = useSubmissions();

  // Calculate user stats from real data
  const totalSubmissions = submissions.length;

  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      const payload: Record<string, string> = {
        display_name: displayName,
        organization,
      };

      await api.updateProfile(payload);

      toast({
        title: 'Profile Updated',
        description: 'Your profile information has been saved.',
      });
    } catch (error: unknown) {
      console.error('Failed to update profile:', error);
      const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      toast({
        title: 'Update Failed',
        description: String(detail || 'Failed to save profile changes. Please try again.'),
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Format member since date from user data
  const memberSince = user?.createdAt
    ? new Date(user.createdAt).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    : '--';

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl sm:text-3xl font-bold tracking-tight">Profile</h1>
        <p className="text-muted-foreground mt-1">
          Manage your profile information
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
          <CardDescription>
            Update your personal information and organization details
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <form onSubmit={(e) => { e.preventDefault(); handleSaveProfile(); }}>
            <div className="space-y-6">
              {/* Avatar */}
              <div className="flex flex-col sm:flex-row sm:items-start gap-4">
                <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                  <User className="h-10 w-10 text-primary" />
                </div>
                <div>
                  <Button variant="outline" size="sm" disabled title="Avatar uploads coming soon">Change Avatar</Button>
                  <p className="text-xs text-muted-foreground mt-1">JPG, PNG or GIF. 1MB max.</p>
                </div>
              </div>

              <Separator />

              {/* Form Fields */}
              <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="username">Display Name</Label>
                  <Input
                    id="username"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    autoComplete="name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={user?.email ?? ''}
                    disabled
                    className="opacity-60"
                    autoComplete="email"
                    inputMode="email"
                  />
                  <p className="text-xs text-muted-foreground">
                    Email is managed by your authentication provider.
                  </p>
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="organization">Organization</Label>
                  <div className="flex gap-2">
                    <Building2 className="h-10 w-10 text-muted-foreground p-2 border rounded-md shrink-0" />
                    <Input
                      id="organization"
                      value={organization}
                      onChange={(e) => setOrganization(e.target.value)}
                      className="flex-1"
                      autoComplete="organization"
                    />
                  </div>
                </div>
              </div>

              {/* Stats */}
              <div className="grid gap-4 grid-cols-1 xs:grid-cols-3 pt-4 border-t">
                <div>
                  <p className="text-sm text-muted-foreground">Member Since</p>
                  <p className="font-medium">{memberSince}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Submissions</p>
                  <p className="font-medium">{totalSubmissions}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Best Score</p>
                  <p className="font-medium">{stats?.bestScore ? stats.bestScore.toFixed(4) : '--'}</p>
                </div>
              </div>

              <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
                <Button type="submit" disabled={isSaving} className="w-full sm:w-auto">
                  {isSaving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save Changes'
                  )}
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
